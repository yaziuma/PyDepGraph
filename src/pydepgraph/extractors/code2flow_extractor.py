# pydepgraph/extractors/code2flow_extractor.py

import subprocess
import json
import ast
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

from .base import ExtractorBase, RawExtractionResult
from ..exceptions import PrologExecutionError
from ..utils.metadata_collector import MetadataCollector
from ..utils.definition_indexer import DefinitionIndexer

logger = logging.getLogger(__name__)


# +++ NEW VISITOR CLASSES FOR CROSS-FILE RESOLUTION +++

class _ImportVisitor(ast.NodeVisitor):
    def __init__(self, module_fqn: str):
        self.module_fqn = module_fqn
        self.imports: Dict[str, str] = {}

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imports[alias.asname or alias.name] = alias.name
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        module = node.module or ""
        if node.level > 0:
            base = self.module_fqn.split('.')
            module_base = ".".join(base[:-node.level]) if len(base) > node.level else ""
            module = f"{module_base}.{module}" if module else module_base
            if module.startswith('.'):
                module = module[1:]

        for alias in node.names:
            full_name = f"{module}.{alias.name}"
            self.imports[alias.asname or alias.name] = full_name
        self.generic_visit(node)


class _CallResolverVisitor(ast.NodeVisitor):
    def __init__(self, module_fqn: str, definition_index: Dict, import_map: Dict):
        self.module_fqn = module_fqn
        self.definition_index = definition_index
        self.import_map = import_map
        self.scope_stack: List[str] = [module_fqn]
        self.calls: List[Dict[str, Any]] = []
        self.variable_types: Dict[str, str] = {}

    def _get_current_fqn_from_scope(self) -> str:
        return ".".join(self.scope_stack)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.scope_stack.append(node.name)
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.visit_FunctionDef(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        self.scope_stack.append(node.name)
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_Assign(self, node: ast.Assign):
        if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name):
            class_name = node.value.func.id
            class_fqn = None
            if class_name in self.import_map:
                class_fqn = self.import_map[class_name]
            else:
                local_class_fqn = f"{self.module_fqn}.{class_name}"
                if local_class_fqn in self.definition_index and self.definition_index[local_class_fqn]['node_type'] == 'class':
                    class_fqn = local_class_fqn

            if class_fqn and class_fqn in self.definition_index and self.definition_index[class_fqn]['node_type'] == 'class':
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        self.variable_types[target.id] = class_fqn
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        target_fqn = self._resolve_call_target(node.func)

        if target_fqn and target_fqn in self.definition_index:
            if self.definition_index[target_fqn]['node_type'] in ('function', 'method'):
                source_fqn = self._get_current_fqn_from_scope()
                if source_fqn != target_fqn:
                    self.calls.append({
                        "type": "FunctionCall",
                        "data": { "source_function": source_fqn, "target_function": target_fqn, "call_type": "direct", "line_number": node.lineno, "extractor": "code2flow_ast_cross_file" }
                    })
        self.generic_visit(node)

    def _resolve_call_target(self, node: ast.expr) -> Optional[str]:
        if isinstance(node, ast.Name):
            if node.id in self.import_map:
                return self.import_map[node.id]
            local_fqn = f"{self.module_fqn}.{node.id}"
            if local_fqn in self.definition_index:
                return local_fqn
        elif isinstance(node, ast.Attribute):
            value_node = node.value
            attr_name = node.attr
            base_fqn = None
            if isinstance(value_node, ast.Name):
                base_name = value_node.id
                if base_name == 'self':
                    if len(self.scope_stack) > 1:
                        class_name = self.scope_stack[1]
                        return f"{self.module_fqn}.{class_name}.{attr_name}"
                elif base_name in self.import_map:
                    base_fqn = self.import_map[base_name]
                elif base_name in self.variable_types:
                    base_fqn = self.variable_types[base_name]
                else:
                    local_class_fqn = f"{self.module_fqn}.{base_name}"
                    if local_class_fqn in self.definition_index:
                        base_fqn = local_class_fqn
            elif isinstance(value_node, ast.Attribute):
                base_fqn = self._resolve_call_target(value_node)
            if base_fqn:
                return f"{base_fqn}.{attr_name}"
        return None


class Code2FlowExtractor(ExtractorBase):
    def __init__(self, ast_mode: bool = False):
        self.function_id_counter = 0
        self.class_id_counter = 0
        self.metadata_collector = MetadataCollector()
        self.ast_mode = ast_mode

    def extract(self, project_path: str) -> RawExtractionResult:
        if not self.validate_project_path(project_path):
            raise ValueError(f"Invalid project path: {project_path}")
        if self.ast_mode:
            logger.info("Running in forced AST mode for cross-file analysis.")
            return self._extract_with_cross_file_resolver(project_path)
        try:
            return self._run_code2flow(project_path)
        except Exception as e:
            logger.warning(f"Code2Flow execution failed: {e}")
            logger.info("Falling back to AST analysis for function-level dependencies")
            return self._ast_analysis(project_path)

    def _extract_with_cross_file_resolver(self, project_path: str) -> RawExtractionResult:
        logger.info(f"Cross-file resolver running on {project_path}")
        indexer = DefinitionIndexer(project_path)
        definition_index = indexer.index_project()
        all_relationships = []
        project_root = Path(project_path)
        for py_file in project_root.rglob("*.py"):
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    source_code = f.read()
                tree = ast.parse(source_code, filename=str(py_file))
                module_fqn = indexer._get_module_fqn(py_file)
                import_visitor = _ImportVisitor(module_fqn)
                import_visitor.visit(tree)
                call_visitor = _CallResolverVisitor(module_fqn, definition_index, import_visitor.imports)
                call_visitor.visit(tree)
                all_relationships.extend(call_visitor.calls)
            except Exception as e:
                logger.warning(f"Failed to analyze {py_file} for cross-file calls: {e}", exc_info=True)
        functions = [v for v in definition_index.values() if v['node_type'] in ('function', 'method')]
        classes = [v for v in definition_index.values() if v['node_type'] == 'class']
        return RawExtractionResult(
            modules=[], functions=functions, classes=classes, relationships=all_relationships,
            metadata={'extractor': 'code2flow_ast_cross_file'}
        )

    # --- Restored Original Methods ---
    def _run_code2flow(self, project_path: str) -> RawExtractionResult:
        try:
            cmd = ["code2flow", "--language", "py", "--output", "/tmp/code2flow_output.json", project_path]
            logger.info(f"Running Code2Flow: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd=project_path)
            if result.returncode != 0:
                raise PrologExecutionError(f"Code2Flow failed with return code {result.returncode}: {result.stderr}")
            output_file = "/tmp/code2flow_output.json"
            if not Path(output_file).exists():
                raise PrologExecutionError("Code2Flow output file not found")
            with open(output_file, 'r', encoding='utf-8') as f:
                output_content = f.read()
            if not output_content.strip():
                raise PrologExecutionError("Code2Flow produced no output")
            logger.info("Code2Flow execution successful, parsing output...")
            return self._parse_code2flow_output(output_content, project_path)
        except subprocess.TimeoutExpired:
            raise PrologExecutionError("Code2Flow execution timed out")
        except FileNotFoundError:
            raise PrologExecutionError("Code2Flow not found. Please install code2flow: pip install code2flow")
        except Exception as e:
            raise PrologExecutionError(f"Code2Flow execution failed: {e}")

    def _parse_code2flow_output(self, output: str, project_path: str) -> RawExtractionResult:
        functions, classes, relationships = [], [], []
        try:
            data = json.loads(output)
            function_name_to_info = {}
            graph = data.get('graph', {})
            nodes = graph.get('nodes', {})
            edges = graph.get('edges', {})
            for node_id, node_data in nodes.items():
                self.function_id_counter += 1
                label = node_data.get('label', '')
                name = node_data.get('name', '')
                if ':' in label:
                    line_str, func_name = label.split(':', 1)
                    line_number = int(line_str.strip()) if line_str.strip().isdigit() else 0
                    func_name = func_name.strip()
                else:
                    line_number, func_name = 0, label.strip()
                if '::' in name:
                    parts = name.split('::')
                    if len(parts) >= 2:
                        module_name, function_full_name = parts[0], parts[1]
                        if '.' in function_full_name:
                            class_name, method_name = function_full_name.rsplit('.', 1)
                            is_method, qualified_name = True, f"{module_name}::{class_name}.{method_name}"
                        else:
                            is_method, qualified_name = False, f"{module_name}::{function_full_name}"
                    else:
                        is_method, qualified_name = False, name
                else:
                    is_method, qualified_name = False, name
                file_path_for_metadata = name.split('::')[0] if '::' in name else 'unknown'
                possible_paths = [Path(project_path)/f"{file_path_for_metadata}.py", Path(project_path)/f"{file_path_for_metadata}/__init__.py", Path(project_path)/file_path_for_metadata]
                enhanced_metadata = {}
                for actual_file_path in possible_paths:
                    if actual_file_path.exists() and actual_file_path.is_file():
                        file_metadata = self.metadata_collector.collect_file_metadata(str(actual_file_path))
                        if file_metadata:
                            for func_meta in file_metadata.functions:
                                if func_meta['name'] == func_name:
                                    enhanced_metadata = func_meta
                                    break
                            if enhanced_metadata: break
                function_info = {'id':f"func_{self.function_id_counter:06d}",'name':func_name,'qualified_name':qualified_name,'file_path':file_path_for_metadata,'line_number':line_number,'cyclomatic_complexity':enhanced_metadata.get('cyclomatic_complexity',1),'parameter_count':enhanced_metadata.get('parameter_count',0),'is_method':enhanced_metadata.get('is_method',is_method),'is_static':enhanced_metadata.get('is_static',False),'is_class_method':enhanced_metadata.get('is_class_method',False),'extractor':'code2flow'}
                functions.append(function_info)
                function_name_to_info[node_id] = function_info
            for edge_data in edges:
                source_id, target_id = edge_data.get('source',''), edge_data.get('target','')
                source_info, target_info = function_name_to_info.get(source_id), function_name_to_info.get(target_id)
                if source_info and target_info:
                    relationships.append({'relationship_type':'FunctionCalls','source_function':source_info['qualified_name'],'target_function':target_info['qualified_name'],'source_function_id':source_info['id'],'target_function_id':target_info['id'],'file_path':source_info['file_path'],'line_number':0,'call_type':'direct','extractor':'code2flow'})
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parsing failed: {e}, trying DOT format")
            return self._parse_dot_format(output, project_path)
        logger.info(f"Code2Flow parsing completed: {len(functions)} functions, {len(relationships)} relationships")
        return RawExtractionResult(modules=[], functions=functions, classes=classes, relationships=relationships, metadata={'extractor':'code2flow','total_functions':len(functions),'total_classes':len(classes),'total_relationships':len(relationships),'project_path':project_path})

    def _parse_dot_format(self, output: str, project_path: str) -> RawExtractionResult:
        functions, classes, relationships, function_name_to_info = [], [], [], {}
        for line in output.split('\n'):
            line = line.strip()
            if '[label=' in line and 'shape=' not in line:
                parts = line.split('[label=')
                if len(parts) >= 2:
                    node_id, label_part = parts[0].strip().strip('"'), parts[1].split(']')[0].strip('"')
                    self.function_id_counter += 1
                    function_info = {'id':f"func_{self.function_id_counter:06d}",'name':label_part,'qualified_name':f"{project_path}::{label_part}",'file_path':project_path,'line_number':0,'cyclomatic_complexity':1,'parameter_count':0,'is_method':False,'is_static':False,'is_class_method':False,'extractor':'code2flow'}
                    functions.append(function_info)
                    function_name_to_info[node_id] = function_info
            elif '->' in line and not line.startswith('//'):
                parts = line.split('->')
                if len(parts) >= 2:
                    source, target = parts[0].strip().strip('"').strip(), parts[1].split('[')[0].strip().strip('"').strip()
                    source_info, target_info = function_name_to_info.get(source), function_name_to_info.get(target)
                    if source_info and target_info:
                        relationships.append({'relationship_type':'FunctionCalls','source_function':source_info['qualified_name'],'target_function':target_info['qualified_name'],'source_function_id':source_info['id'],'target_function_id':target_info['id'],'file_path':project_path,'line_number':0,'call_type':'direct','extractor':'code2flow'})
        return RawExtractionResult(modules=[], functions=functions, classes=classes, relationships=relationships, metadata={'extractor':'code2flow','total_functions':len(functions),'total_classes':len(classes),'total_relationships':len(relationships),'project_path':project_path})

    def _ast_analysis(self, project_path: str) -> RawExtractionResult:
        functions, classes, relationships = [], [], []
        project_root = Path(project_path)
        for py_file in list(project_root.rglob("*.py")):
            try:
                file_metadata = self.metadata_collector.collect_file_metadata(str(py_file))
                if file_metadata:
                    for func_data in file_metadata.functions:
                        self.function_id_counter += 1
                        functions.append({'id':f"func_{self.function_id_counter:06d}",'name':func_data['name'],'qualified_name':func_data['qualified_name'],'file_path':str(py_file.relative_to(project_root)),'line_number':func_data['line_number'],'cyclomatic_complexity':func_data['cyclomatic_complexity'],'parameter_count':func_data['parameter_count'],'is_method':func_data['is_method'],'is_static':func_data['is_static'],'is_class_method':func_data['is_class_method'],'extractor':'code2flow_ast'})
                    for class_data in file_metadata.classes:
                        self.class_id_counter += 1
                        classes.append({'id':f"class_{self.class_id_counter:06d}",'name':class_data['name'],'qualified_name':class_data['qualified_name'],'file_path':str(py_file.relative_to(project_root)),'line_number':class_data['line_number'],'method_count':class_data['method_count'],'inheritance_depth':class_data['inheritance_depth'],'is_abstract':class_data['is_abstract'],'extractor':'code2flow_ast'})
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                tree = ast.parse(content)
                _, _, file_relationships = self._analyze_ast(tree, str(py_file.relative_to(project_root)))
                relationships.extend(file_relationships)
            except Exception as e:
                logger.warning(f"Failed to analyze {py_file}: {e}")
        logger.info(f"AST analysis completed: {len(functions)} functions, {len(classes)} classes, {len(relationships)} relationships")
        return RawExtractionResult(modules=[], functions=functions, classes=classes, relationships=relationships, metadata={'extractor':'code2flow_ast','total_functions':len(functions),'total_classes':len(classes),'total_relationships':len(relationships),'project_path':project_path})

    def _analyze_ast(self, tree: ast.AST, file_path: str) -> tuple:
        functions, classes, relationships, function_names, class_names = [], [], [], set(), set()
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef): function_names.add(node.name)
            elif isinstance(node, ast.ClassDef): class_names.add(node.name)
        visitor = self.FunctionVisitor(self, function_names, class_names, file_path, relationships, functions, classes)
        visitor.visit(tree)
        return functions, classes, relationships

    class FunctionVisitor(ast.NodeVisitor):
        def __init__(self, extractor, function_names, class_names, file_path, relationships, functions, classes):
            self.extractor, self.function_names, self.class_names, self.file_path, self.relationships, self.functions, self.classes = extractor, function_names, class_names, file_path, relationships, functions, classes
            self.current_class = None
        def visit_ClassDef(self, node):
            class_id = f"class_{self.extractor.class_id_counter:06d}"; self.extractor.class_id_counter += 1
            base_classes = [self._get_name(base) for base in node.bases]
            class_info = {'id':class_id,'name':node.name,'qualified_name':f"{self.file_path}::{node.name}",'file_path':self.file_path,'line_number':node.lineno,'method_count':len([n for n in node.body if isinstance(n,ast.FunctionDef)]),'inheritance_depth':1 if base_classes else 0,'base_classes':base_classes,'is_abstract':self._is_abstract_class(node)}
            self.classes.append(class_info)
            for base_class in base_classes:
                if base_class != 'object' and base_class in self.class_names:
                    self.relationships.append({'relationship_type':'Inheritance','child_class':f"{self.file_path}::{node.name}",'parent_class':f"{self.file_path}::{base_class}",'source_class_id':class_id,'target_class_id':f"unknown_{base_class}",'file_path':self.file_path,'line_number':node.lineno})
            old_class, self.current_class = self.current_class, class_info
            self.generic_visit(node)
            self.current_class = old_class
        def visit_FunctionDef(self, node):
            function_id = f"func_{self.extractor.function_id_counter:06d}"; self.extractor.function_id_counter += 1
            qualified_name = f"{self.current_class['name']}.{node.name}" if self.current_class else node.name
            qualified_name = f"{self.file_path}::{qualified_name}"
            function_info = {'id':function_id,'name':node.name,'qualified_name':qualified_name,'file_path':self.file_path,'line_number':node.lineno,'cyclomatic_complexity':self._calculate_complexity(node),'parameter_count':len(node.args.args),'is_method':self.current_class is not None,'is_static':any(isinstance(d,ast.Name)and d.id=='staticmethod'for d in node.decorator_list),'is_class_method':any(isinstance(d,ast.Name)and d.id=='classmethod'for d in node.decorator_list),'class_id':self.current_class['id']if self.current_class else None}
            self.functions.append(function_info)
            if self.current_class:
                self.relationships.append({'relationship_type':'Contains','source_class':self.current_class['name'],'target_function':node.name,'source_class_id':self.current_class['id'],'target_function_id':function_id,'file_path':self.file_path,'line_number':node.lineno})
            self._extract_function_calls(node, function_info, self.relationships)
            self.generic_visit(node)
        def _get_name(self, node):
            if isinstance(node, ast.Name): return node.id
            if isinstance(node, ast.Attribute): return f"{self._get_name(node.value)}.{node.attr}"
            return str(node)
        def _is_abstract_class(self, node):
            for child in ast.walk(node):
                if isinstance(child, ast.Name) and child.id == 'abstractmethod': return True
            return False
        def _calculate_complexity(self, node):
            complexity = 1
            for child in ast.walk(node):
                if isinstance(child,(ast.If,ast.While,ast.For,ast.ExceptHandler)): complexity += 1
                elif isinstance(child, ast.BoolOp): complexity += len(child.values) - 1
            return complexity
        def _extract_function_calls(self, func_node, func_info, relationships):
            for node in ast.walk(func_node):
                if isinstance(node, ast.Call):
                    called_func = self._get_call_name(node.func)
                    if called_func and called_func in self.function_names:
                        relationships.append({'relationship_type':'FunctionCalls','source_function':func_info['qualified_name'],'target_function':f"{self.file_path}::{called_func}",'source_function_id':func_info['id'],'target_function_id':f"unknown_{called_func}",'file_path':self.file_path,'line_number':getattr(node,'lineno',0),'call_type':'direct'})
        def _get_call_name(self, node):
            if isinstance(node, ast.Name): return node.id
            if isinstance(node, ast.Attribute): return node.attr
            return None

    def get_supported_file_types(self) -> List[str]:
        """サポートするファイル拡張子を返す"""
        return ['.py']
