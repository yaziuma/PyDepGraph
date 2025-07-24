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

logger = logging.getLogger(__name__)


class Code2FlowExtractor(ExtractorBase):
    """Code2Flowを使用した関数レベル依存関係抽出器"""

    def __init__(self):
        self.function_id_counter = 0
        self.class_id_counter = 0
        self.metadata_collector = MetadataCollector()

    def extract(self, project_path: str) -> RawExtractionResult:
        """Code2Flowコマンドを実行して関数レベル依存関係を抽出"""
        
        if not self.validate_project_path(project_path):
            raise ValueError(f"Invalid project path: {project_path}")

        # まず実Code2Flowコマンドの実行を試行
        try:
            return self._run_code2flow(project_path)
        except Exception as e:
            logger.warning(f"Code2Flow execution failed: {e}")
            logger.info("Falling back to AST analysis for function-level dependencies")
            return self._ast_analysis(project_path)

    def _run_code2flow(self, project_path: str) -> RawExtractionResult:
        """実際のCode2Flowコマンドを実行"""
        try:
            # Code2Flowコマンドの実行（JSON形式で出力）
            cmd = ["code2flow", "--language", "py", "--output", "/tmp/code2flow_output.json", project_path]
            logger.info(f"Running Code2Flow: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5分のタイムアウト
                cwd=project_path
            )
            
            if result.returncode != 0:
                raise PrologExecutionError(f"Code2Flow failed with return code {result.returncode}: {result.stderr}")
            
            # 出力ファイルの読み取り
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
        """Code2Flowの出力（JSON形式）を解析してPyDepGraph形式に変換"""
        functions = []
        classes = []
        relationships = []
        
        try:
            # JSON形式の解析
            data = json.loads(output)
            current_function_id = 0
            function_name_to_info = {}
            
            # Code2FlowのJSON構造に合わせて解析
            graph = data.get('graph', {})
            nodes = graph.get('nodes', {})
            edges = graph.get('edges', {})
            
            # ノード情報の抽出
            for node_id, node_data in nodes.items():
                current_function_id += 1
                label = node_data.get('label', '')
                name = node_data.get('name', '')
                
                # ラベルから行番号を抽出（例："12: __init__()" -> "__init__()"）
                if ':' in label:
                    line_str, func_name = label.split(':', 1)
                    line_number = int(line_str.strip()) if line_str.strip().isdigit() else 0
                    func_name = func_name.strip()
                else:
                    line_number = 0
                    func_name = label.strip()
                
                # nameから実際のファイルパスとクラス情報を抽出
                # 例："binding_environment::BindingEnvironment.__init__"
                if '::' in name:
                    parts = name.split('::')
                    if len(parts) >= 2:
                        module_name = parts[0]
                        function_full_name = parts[1]
                        
                        # クラスメソッドかどうかを判定
                        if '.' in function_full_name:
                            class_name, method_name = function_full_name.rsplit('.', 1)
                            is_method = True
                            qualified_name = f"{module_name}::{class_name}.{method_name}"
                        else:
                            is_method = False
                            qualified_name = f"{module_name}::{function_full_name}"
                    else:
                        qualified_name = name
                        is_method = False
                else:
                    qualified_name = name
                    is_method = False
                
                # Try to get more accurate metadata for this function
                file_path_for_metadata = name.split('::')[0] if '::' in name else 'unknown'
                
                # Try different possible file paths
                possible_paths = [
                    Path(project_path) / f"{file_path_for_metadata}.py",
                    Path(project_path) / f"{file_path_for_metadata}/__init__.py",
                    Path(project_path) / file_path_for_metadata
                ]
                
                # Get enhanced metadata if file exists
                enhanced_metadata = {}
                for actual_file_path in possible_paths:
                    if actual_file_path.exists() and actual_file_path.is_file():
                        file_metadata = self.metadata_collector.collect_file_metadata(str(actual_file_path))
                        if file_metadata:
                            # Find matching function in metadata
                            for func_meta in file_metadata.functions:
                                if func_meta['name'] == func_name:
                                    enhanced_metadata = func_meta
                                    break
                            if enhanced_metadata:
                                break
                
                function_info = {
                    'id': f"func_{current_function_id:06d}",
                    'name': func_name,
                    'qualified_name': qualified_name,
                    'file_path': file_path_for_metadata,
                    'line_number': line_number,
                    'cyclomatic_complexity': enhanced_metadata.get('cyclomatic_complexity', 1),
                    'parameter_count': enhanced_metadata.get('parameter_count', 0),
                    'is_method': enhanced_metadata.get('is_method', is_method),
                    'is_static': enhanced_metadata.get('is_static', False),
                    'is_class_method': enhanced_metadata.get('is_class_method', False),
                    'extractor': 'code2flow'
                }
                functions.append(function_info)
                function_name_to_info[node_id] = function_info
            
            # エッジ情報の抽出（edgesはリスト形式）
            for edge_data in edges:
                source_id = edge_data.get('source', '')
                target_id = edge_data.get('target', '')
                
                source_info = function_name_to_info.get(source_id)
                target_info = function_name_to_info.get(target_id)
                
                if source_info and target_info:
                    relationships.append({
                        'relationship_type': 'FunctionCalls',
                        'source_function': source_info['qualified_name'],
                        'target_function': target_info['qualified_name'],
                        'source_function_id': source_info['id'],
                        'target_function_id': target_info['id'],
                        'file_path': source_info['file_path'],
                        'line_number': 0,
                        'call_type': 'direct',
                        'extractor': 'code2flow'
                    })
            
        except json.JSONDecodeError as e:
            # JSON解析失敗時はDOT形式として処理
            logger.warning(f"JSON parsing failed: {e}, trying DOT format")
            return self._parse_dot_format(output, project_path)
        
        logger.info(f"Code2Flow parsing completed: {len(functions)} functions, {len(relationships)} relationships")
        
        return RawExtractionResult(
            modules=[],
            functions=functions,
            classes=classes,
            relationships=relationships,
            metadata={
                'extractor': 'code2flow',
                'total_functions': len(functions),
                'total_classes': len(classes),
                'total_relationships': len(relationships),
                'project_path': project_path,
            }
        )

    def _parse_dot_format(self, output: str, project_path: str) -> RawExtractionResult:
        """DOT形式の出力を解析（フォールバック）"""
        functions = []
        classes = []
        relationships = []
        
        lines = output.split('\n')
        current_function_id = 0
        function_name_to_info = {}
        
        for line in lines:
            line = line.strip()
            
            # ノード定義の解析 (例: "func1" [label="function_name"])
            if '[label=' in line and 'shape=' not in line:
                parts = line.split('[label=')
                if len(parts) >= 2:
                    node_id = parts[0].strip().strip('"')
                    label_part = parts[1].split(']')[0].strip('"')
                    
                    current_function_id += 1
                    function_info = {
                        'id': f"func_{current_function_id:06d}",
                        'name': label_part,
                        'qualified_name': f"{project_path}::{label_part}",
                        'file_path': project_path,
                        'line_number': 0,
                        'cyclomatic_complexity': 1,
                        'parameter_count': 0,
                        'is_method': False,
                        'is_static': False,
                        'is_class_method': False,
                        'extractor': 'code2flow'
                    }
                    functions.append(function_info)
                    function_name_to_info[node_id] = function_info
            
            # エッジ定義の解析 (例: "func1" -> "func2")
            elif '->' in line and not line.startswith('//'):
                parts = line.split('->')
                if len(parts) >= 2:
                    source = parts[0].strip().strip('"').strip()
                    target = parts[1].split('[')[0].strip().strip('"').strip()
                    
                    source_info = function_name_to_info.get(source)
                    target_info = function_name_to_info.get(target)
                    
                    if source_info and target_info:
                        relationships.append({
                            'relationship_type': 'FunctionCalls',
                            'source_function': source_info['qualified_name'],
                            'target_function': target_info['qualified_name'],
                            'source_function_id': source_info['id'],
                            'target_function_id': target_info['id'],
                            'file_path': project_path,
                            'line_number': 0,
                            'call_type': 'direct',
                            'extractor': 'code2flow'
                        })
        
        return RawExtractionResult(
            modules=[],
            functions=functions,
            classes=classes,
            relationships=relationships,
            metadata={
                'extractor': 'code2flow',
                'total_functions': len(functions),
                'total_classes': len(classes),
                'total_relationships': len(relationships),
                'project_path': project_path,
            }
        )

    def _ast_analysis(self, project_path: str) -> RawExtractionResult:
        """ASTを使用した関数・クラス依存関係の抽出"""
        
        functions = []
        classes = []
        relationships = []
        
        project_root = Path(project_path)
        python_files = list(project_root.rglob("*.py"))
        
        for py_file in python_files:
            try:
                # Use MetadataCollector for comprehensive analysis
                file_metadata = self.metadata_collector.collect_file_metadata(str(py_file))
                if file_metadata:
                    # Extract functions with accurate metadata
                    for func_data in file_metadata.functions:
                        self.function_id_counter += 1
                        function_info = {
                            'id': f"func_{self.function_id_counter:06d}",
                            'name': func_data['name'],
                            'qualified_name': func_data['qualified_name'],
                            'file_path': str(py_file.relative_to(project_root)),
                            'line_number': func_data['line_number'],
                            'cyclomatic_complexity': func_data['cyclomatic_complexity'],
                            'parameter_count': func_data['parameter_count'],
                            'is_method': func_data['is_method'],
                            'is_static': func_data['is_static'],
                            'is_class_method': func_data['is_class_method'],
                            'extractor': 'code2flow_ast'
                        }
                        functions.append(function_info)
                    
                    # Extract classes with accurate metadata
                    for class_data in file_metadata.classes:
                        self.class_id_counter += 1
                        class_info = {
                            'id': f"class_{self.class_id_counter:06d}",
                            'name': class_data['name'],
                            'qualified_name': class_data['qualified_name'],
                            'file_path': str(py_file.relative_to(project_root)),
                            'line_number': class_data['line_number'],
                            'method_count': class_data['method_count'],
                            'inheritance_depth': class_data['inheritance_depth'],
                            'is_abstract': class_data['is_abstract'],
                            'extractor': 'code2flow_ast'
                        }
                        classes.append(class_info)
                
                # Still use AST for relationship analysis
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                tree = ast.parse(content)
                _, _, file_relationships = self._analyze_ast(
                    tree, str(py_file.relative_to(project_root))
                )
                relationships.extend(file_relationships)
                
            except Exception as e:
                logger.warning(f"Failed to analyze {py_file}: {e}")
                continue

        logger.info(f"AST analysis completed: {len(functions)} functions, {len(classes)} classes, {len(relationships)} relationships")

        return RawExtractionResult(
            modules=[],
            functions=functions,
            classes=classes,
            relationships=relationships,
            metadata={
                'extractor': 'code2flow_ast',
                'total_functions': len(functions),
                'total_classes': len(classes),
                'total_relationships': len(relationships),
                'project_path': project_path,
            }
        )

    def _analyze_ast(self, tree: ast.AST, file_path: str) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """AST解析によるファイル内の関数・クラス・依存関係抽出"""
        functions = []
        classes = []
        relationships = []
        function_names = set()  # ファイル内の関数名を記録
        class_names = set()  # ファイル内のクラス名を記録
        
        class FunctionVisitor(ast.NodeVisitor):
            def __init__(self, extractor, function_names, class_names):
                self.extractor = extractor
                self.current_class = None
                self.function_names = function_names
                self.class_names = class_names
                
            def visit_ClassDef(self, node: ast.ClassDef):
                class_id = f"class_{self.extractor.class_id_counter:06d}"
                self.extractor.class_id_counter += 1
                
                # 基底クラス情報
                base_classes = [self._get_name(base) for base in node.bases]
                
                class_info = {
                    'id': class_id,
                    'name': node.name,
                    'qualified_name': f"{file_path}::{node.name}",
                    'file_path': file_path,
                    'line_number': node.lineno,
                    'method_count': len([n for n in node.body if isinstance(n, ast.FunctionDef)]),
                    'inheritance_depth': 1 if base_classes else 0,
                    'base_classes': base_classes,
                    'is_abstract': self._is_abstract_class(node),
                }
                classes.append(class_info)
                
                # 継承関係を追加
                for base_class in base_classes:
                    if base_class != 'object' and base_class in self.class_names:
                        # 同一ファイル内のクラス継承のみを記録
                        relationships.append({
                            'relationship_type': 'Inheritance',
                            'child_class': f"{file_path}::{node.name}",
                            'parent_class': f"{file_path}::{base_class}",
                            'source_class_id': class_id,
                            'target_class_id': f"unknown_{base_class}",
                            'file_path': file_path,
                            'line_number': node.lineno,
                        })
                        logger.debug(f"Added inheritance: {node.name} -> {base_class}")
                    else:
                        logger.debug(f"Skipped inheritance: {node.name} -> {base_class} (not in class_names: {self.class_names})")
                
                # クラス内のメソッドを解析
                old_class = self.current_class
                self.current_class = class_info
                self.generic_visit(node)
                self.current_class = old_class
                
            def visit_FunctionDef(self, node: ast.FunctionDef):
                function_id = f"func_{self.extractor.function_id_counter:06d}"
                self.extractor.function_id_counter += 1
                
                # 関数の複雑度計算（簡易版）
                complexity = self._calculate_complexity(node)
                
                qualified_name = node.name
                if self.current_class:
                    qualified_name = f"{self.current_class['name']}.{node.name}"
                    qualified_name = f"{file_path}::{qualified_name}"
                else:
                    qualified_name = f"{file_path}::{node.name}"
                
                function_info = {
                    'id': function_id,
                    'name': node.name,
                    'qualified_name': qualified_name,
                    'file_path': file_path,
                    'line_number': node.lineno,
                    'cyclomatic_complexity': complexity,
                    'parameter_count': len(node.args.args),
                    'is_method': self.current_class is not None,
                    'is_static': any(isinstance(d, ast.Name) and d.id == 'staticmethod' for d in node.decorator_list),
                    'is_class_method': any(isinstance(d, ast.Name) and d.id == 'classmethod' for d in node.decorator_list),
                    'class_id': self.current_class['id'] if self.current_class else None,
                }
                functions.append(function_info)
                
                # Contains関係を追加
                if self.current_class:
                    relationships.append({
                        'relationship_type': 'Contains',
                        'source_class': self.current_class['name'],
                        'target_function': node.name,
                        'source_class_id': self.current_class['id'],
                        'target_function_id': function_id,
                        'file_path': file_path,
                        'line_number': node.lineno,
                    })
                
                # 関数内の関数呼び出しを解析
                self._extract_function_calls(node, function_info, relationships)
                
                self.generic_visit(node)
                
            def _get_name(self, node):
                """ノードから名前を取得"""
                if isinstance(node, ast.Name):
                    return node.id
                elif isinstance(node, ast.Attribute):
                    return f"{self._get_name(node.value)}.{node.attr}"
                else:
                    return str(node)
                    
            def _is_abstract_class(self, node: ast.ClassDef) -> bool:
                """抽象クラスかどうかを判定"""
                for child in ast.walk(node):
                    if isinstance(child, ast.Name) and child.id == 'abstractmethod':
                        return True
                return False
                
            def _calculate_complexity(self, node: ast.FunctionDef) -> int:
                """関数の循環複雑度を計算（簡易版）"""
                complexity = 1  # 基本値
                
                for child in ast.walk(node):
                    if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                        complexity += 1
                    elif isinstance(child, ast.BoolOp):
                        complexity += len(child.values) - 1
                        
                return complexity
                
            def _extract_function_calls(self, func_node: ast.FunctionDef, func_info: Dict[str, Any], relationships: List[Dict[str, Any]]):
                """関数内の関数呼び出しを抽出"""
                for node in ast.walk(func_node):
                    if isinstance(node, ast.Call):
                        called_func = self._get_call_name(node.func)
                        if called_func and called_func in self.function_names:
                            # 同一ファイル内の関数呼び出しのみを記録
                            target_qualified_name = f"{file_path}::{called_func}"
                            relationships.append({
                                'relationship_type': 'FunctionCalls',
                                'source_function': func_info['qualified_name'],
                                'target_function': target_qualified_name,
                                'source_function_id': func_info['id'],
                                'target_function_id': f"unknown_{called_func}",
                                'file_path': file_path,
                                'line_number': getattr(node, 'lineno', 0),
                                'call_type': 'direct',
                            })
                            
            def _get_call_name(self, node) -> Optional[str]:
                """関数呼び出しノードから関数名を取得"""
                if isinstance(node, ast.Name):
                    return node.id
                elif isinstance(node, ast.Attribute):
                    return node.attr
                return None
        
        # 最初にファイル内の全関数名とクラス名を収集
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                function_names.add(node.name)
            elif isinstance(node, ast.ClassDef):
                class_names.add(node.name)
        
        visitor = FunctionVisitor(self, function_names, class_names)
        visitor.visit(tree)
        
        return functions, classes, relationships

    def get_supported_file_types(self) -> List[str]:
        """サポートするファイル拡張子を返す"""
        return ['.py']
