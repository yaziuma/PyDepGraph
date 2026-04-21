# pydepgraph/utils/metadata_collector.py

import ast
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from .file_filter import iter_python_files, DEFAULT_EXCLUDE_PATTERNS

try:
    from radon.complexity import cc_visit
    from radon.raw import analyze
    RADON_AVAILABLE = True
except ImportError:
    RADON_AVAILABLE = False
    cc_visit = None
    analyze = None

logger = logging.getLogger(__name__)


@dataclass
class FileMetadata:
    """File-level metadata container"""
    lines_of_code: int
    total_lines: int
    comment_lines: int
    blank_lines: int
    average_complexity: float
    functions: List[Dict[str, Any]]
    classes: List[Dict[str, Any]]


@dataclass 
class FunctionMetadata:
    """Function-level metadata container"""
    name: str
    qualified_name: str
    line_number: int
    cyclomatic_complexity: int
    parameter_count: int
    lines_of_code: int
    is_method: bool
    is_static: bool
    is_class_method: bool
    docstring: Optional[str] = None


@dataclass
class ClassMetadata:
    """Class-level metadata container"""
    name: str
    qualified_name: str
    line_number: int
    method_count: int
    inheritance_depth: int
    lines_of_code: int
    is_abstract: bool
    docstring: Optional[str] = None


class MetadataCollector:
    """Utility class for collecting comprehensive code metadata using Radon and AST analysis"""
    
    def __init__(self, exclude_patterns: Optional[List[str]] = None):
        self.radon_available = RADON_AVAILABLE
        self.exclude_patterns = exclude_patterns or DEFAULT_EXCLUDE_PATTERNS
        if not self.radon_available:
            logger.warning("Radon not available, falling back to basic AST analysis")
    
    def collect_file_metadata(self, file_path: str) -> Optional[FileMetadata]:
        """
        Collect comprehensive metadata for a single Python file
        
        Args:
            file_path: Path to the Python file
            
        Returns:
            FileMetadata object or None if analysis fails
        """
        try:
            path = Path(file_path)
            if not path.exists() or not path.suffix == '.py':
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse AST
            try:
                tree = ast.parse(content)
            except SyntaxError as e:
                logger.warning(f"Syntax error in {file_path}: {e}")
                return None
            
            # Collect raw metrics using Radon if available
            if self.radon_available:
                raw_metrics = analyze(content)
                lines_of_code = raw_metrics.loc
                total_lines = raw_metrics.lloc
                comment_lines = raw_metrics.comments
                blank_lines = raw_metrics.blank
            else:
                # Fallback to basic line counting
                lines = content.split('\n')
                total_lines = len(lines)
                blank_lines = sum(1 for line in lines if not line.strip())
                comment_lines = sum(1 for line in lines if line.strip().startswith('#'))
                lines_of_code = total_lines - blank_lines - comment_lines
            
            # Collect function and class metadata
            functions = self._collect_functions_metadata(tree, file_path, content)
            classes = self._collect_classes_metadata(tree, file_path, content)
            
            # Calculate average complexity
            complexities = [f['cyclomatic_complexity'] for f in functions if f['cyclomatic_complexity'] > 0]
            average_complexity = sum(complexities) / len(complexities) if complexities else 0.0
            
            return FileMetadata(
                lines_of_code=lines_of_code,
                total_lines=total_lines,
                comment_lines=comment_lines,
                blank_lines=blank_lines,
                average_complexity=average_complexity,
                functions=functions,
                classes=classes
            )
            
        except Exception as e:
            logger.warning(f"Failed to collect metadata for {file_path}: {e}")
            return None
    
    def _collect_functions_metadata(self, tree: ast.AST, file_path: str, content: str) -> List[Dict[str, Any]]:
        """Collect metadata for all functions in the AST"""
        functions = []
        
        # Get Radon complexity data if available
        radon_complexities = {}
        if self.radon_available:
            try:
                complexity_data = cc_visit(content)
                for item in complexity_data:
                    radon_complexities[item.name] = item.complexity
            except Exception as e:
                logger.debug(f"Radon complexity analysis failed for {file_path}: {e}")
        
        class FunctionVisitor(ast.NodeVisitor):
            def __init__(self, collector):
                self.collector = collector
                self.current_class = None
                self.functions = []
            
            def visit_ClassDef(self, node: ast.ClassDef):
                old_class = self.current_class
                self.current_class = node.name
                self.generic_visit(node)
                self.current_class = old_class
            
            def visit_FunctionDef(self, node: ast.FunctionDef):
                # Calculate function lines of code
                func_lines = node.end_lineno - node.lineno + 1 if hasattr(node, 'end_lineno') else 1
                
                # Get parameter count
                param_count = len(node.args.args)
                
                # Get complexity from Radon or calculate basic complexity
                if node.name in radon_complexities:
                    complexity = radon_complexities[node.name]
                else:
                    complexity = self.collector._calculate_basic_complexity(node)
                
                # Determine method characteristics
                is_method = self.current_class is not None
                is_static = any(
                    isinstance(d, ast.Name) and d.id == 'staticmethod' 
                    for d in node.decorator_list
                )
                is_class_method = any(
                    isinstance(d, ast.Name) and d.id == 'classmethod' 
                    for d in node.decorator_list
                )
                
                # Build qualified name
                if self.current_class:
                    qualified_name = f"{Path(file_path).stem}::{self.current_class}.{node.name}"
                else:
                    qualified_name = f"{Path(file_path).stem}::{node.name}"
                
                # Get docstring
                docstring = None
                if (node.body and isinstance(node.body[0], ast.Expr) and 
                    isinstance(node.body[0].value, ast.Constant) and 
                    isinstance(node.body[0].value.value, str)):
                    docstring = node.body[0].value.value
                
                function_data = {
                    'name': node.name,
                    'qualified_name': qualified_name,
                    'line_number': node.lineno,
                    'cyclomatic_complexity': complexity,
                    'parameter_count': param_count,
                    'lines_of_code': func_lines,
                    'is_method': is_method,
                    'is_static': is_static,
                    'is_class_method': is_class_method,
                    'docstring': docstring
                }
                
                self.functions.append(function_data)
                self.generic_visit(node)
        
        visitor = FunctionVisitor(self)
        visitor.visit(tree)
        return visitor.functions
    
    def _collect_classes_metadata(self, tree: ast.AST, file_path: str, content: str) -> List[Dict[str, Any]]:
        """Collect metadata for all classes in the AST"""
        classes = []
        
        class ClassVisitor(ast.NodeVisitor):
            def __init__(self):
                self.classes = []
            
            def visit_ClassDef(self, node: ast.ClassDef):
                # Calculate class lines of code
                class_lines = node.end_lineno - node.lineno + 1 if hasattr(node, 'end_lineno') else 1
                
                # Count methods
                method_count = len([n for n in node.body if isinstance(n, ast.FunctionDef)])
                
                # Calculate inheritance depth (simplified)
                inheritance_depth = len(node.bases) if node.bases else 0
                
                # Check if abstract
                is_abstract = self._is_abstract_class(node)
                
                # Build qualified name
                qualified_name = f"{Path(file_path).stem}::{node.name}"
                
                # Get docstring
                docstring = None
                if (node.body and isinstance(node.body[0], ast.Expr) and 
                    isinstance(node.body[0].value, ast.Constant) and 
                    isinstance(node.body[0].value.value, str)):
                    docstring = node.body[0].value.value
                
                class_data = {
                    'name': node.name,
                    'qualified_name': qualified_name,
                    'line_number': node.lineno,
                    'method_count': method_count,
                    'inheritance_depth': inheritance_depth,
                    'lines_of_code': class_lines,
                    'is_abstract': is_abstract,
                    'docstring': docstring
                }
                
                self.classes.append(class_data)
                self.generic_visit(node)
            
            def _is_abstract_class(self, node: ast.ClassDef) -> bool:
                """Check if class is abstract based on decorators and methods"""
                # Check for ABC inheritance
                for base in node.bases:
                    if isinstance(base, ast.Name) and base.id in ('ABC', 'ABCMeta'):
                        return True
                
                # Check for abstract methods
                for child in ast.walk(node):
                    if isinstance(child, ast.FunctionDef):
                        for decorator in child.decorator_list:
                            if (isinstance(decorator, ast.Name) and 
                                decorator.id == 'abstractmethod'):
                                return True
                return False
        
        visitor = ClassVisitor()
        visitor.visit(tree)
        return visitor.classes
    
    def _calculate_basic_complexity(self, node: ast.FunctionDef) -> int:
        """Calculate basic cyclomatic complexity using AST (fallback when Radon unavailable)"""
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor, 
                                 ast.ExceptHandler, ast.With, ast.AsyncWith)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                # Each additional boolean operator adds complexity
                complexity += len(child.values) - 1
            elif isinstance(child, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
                # Comprehensions add complexity
                complexity += 1
        
        return complexity
    
    def collect_module_metadata(self, module_path: str, project_root: str) -> Dict[str, Any]:
        """
        Collect aggregated metadata for a module (file or directory)
        
        Args:
            module_path: Path to the module
            project_root: Root path of the project
            
        Returns:
            Dict containing aggregated module metadata
        """
        path = Path(module_path)
        
        if path.is_file() and path.suffix == '.py':
            # Single file module
            file_metadata = self.collect_file_metadata(str(path))
            if file_metadata:
                return {
                    'lines_of_code': file_metadata.lines_of_code,
                    'complexity_score': file_metadata.average_complexity,
                    'function_count': len(file_metadata.functions),
                    'class_count': len(file_metadata.classes),
                    'total_lines': file_metadata.total_lines
                }
        
        elif path.is_dir():
            # Directory module - aggregate all Python files
            total_loc = 0
            total_complexity = 0
            total_functions = 0
            total_classes = 0
            total_lines = 0
            complexity_count = 0
            
            for py_file in iter_python_files(path, self.exclude_patterns):
                if py_file.name == '__init__.py':
                    continue  # Skip __init__.py for directory aggregation
                
                file_metadata = self.collect_file_metadata(str(py_file))
                if file_metadata:
                    total_loc += file_metadata.lines_of_code
                    total_lines += file_metadata.total_lines
                    total_functions += len(file_metadata.functions)
                    total_classes += len(file_metadata.classes)
                    
                    if file_metadata.average_complexity > 0:
                        total_complexity += file_metadata.average_complexity
                        complexity_count += 1
            
            avg_complexity = total_complexity / complexity_count if complexity_count > 0 else 0.0
            
            return {
                'lines_of_code': total_loc,
                'complexity_score': avg_complexity,
                'function_count': total_functions,
                'class_count': total_classes,
                'total_lines': total_lines
            }
        
        return {
            'lines_of_code': 0,
            'complexity_score': 0.0,
            'function_count': 0,
            'class_count': 0,
            'total_lines': 0
        }
