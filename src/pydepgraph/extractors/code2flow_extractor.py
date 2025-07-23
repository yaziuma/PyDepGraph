# pydepgraph/extractors/code2flow_extractor.py

import subprocess
import json
import ast
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

from .base import ExtractorBase, RawExtractionResult
from ..exceptions import PrologExecutionError

logger = logging.getLogger(__name__)


class Code2FlowExtractor(ExtractorBase):
    """Code2Flowを使用した関数レベル依存関係抽出器"""

    def __init__(self):
        self.function_id_counter = 0
        self.class_id_counter = 0

    def extract(self, project_path: str) -> RawExtractionResult:
        """Code2Flowコマンドを実行して関数レベル依存関係を抽出"""
        
        if not self.validate_project_path(project_path):
            raise ValueError(f"Invalid project path: {project_path}")

        # Code2Flowが利用できない場合はAST解析を使用
        logger.info("Using AST analysis for function-level dependencies")
        return self._ast_analysis(project_path)

    def _ast_analysis(self, project_path: str) -> RawExtractionResult:
        """ASTを使用した関数・クラス依存関係の抽出"""
        
        functions = []
        classes = []
        relationships = []
        
        project_root = Path(project_path)
        python_files = list(project_root.rglob("*.py"))
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                tree = ast.parse(content)
                file_functions, file_classes, file_relationships = self._analyze_ast(
                    tree, str(py_file.relative_to(project_root))
                )
                
                functions.extend(file_functions)
                classes.extend(file_classes)
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
