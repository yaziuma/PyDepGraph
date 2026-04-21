# src/pydepgraph/utils/definition_indexer.py

import ast
from pathlib import Path
from typing import Dict, Any, List, Optional
from .file_filter import iter_python_files, DEFAULT_EXCLUDE_PATTERNS

class DefinitionIndexer:
    """
    Scans a Python project and builds an index of all class, function,
    and method definitions with their fully qualified names (FQN).
    """

    def __init__(self, project_root: str, exclude_patterns: Optional[List[str]] = None):
        self.project_root = Path(project_root).resolve()
        self.exclude_patterns = exclude_patterns or DEFAULT_EXCLUDE_PATTERNS
        self.index: Dict[str, Dict[str, Any]] = {}

    def index_project(self) -> Dict[str, Dict[str, Any]]:
        """
        Indexes all Python files in the project root.
        """
        for py_file in iter_python_files(self.project_root, self.exclude_patterns):
            self._index_file(py_file)
        return self.index

    def _get_module_fqn(self, file_path: Path) -> str:
        """Converts a file path to a module's fully qualified name."""
        relative_path = file_path.relative_to(self.project_root)
        # Remove .py extension and replace / with .
        return str(relative_path.with_suffix("")).replace('/', '.')

    def _index_file(self, file_path: Path):
        """Indexes a single Python file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source_code = f.read()
            tree = ast.parse(source_code, filename=str(file_path))

            module_fqn = self._get_module_fqn(file_path)

            visitor = _DefinitionVisitor(module_fqn, str(file_path))
            visitor.visit(tree)

            self.index.update(visitor.definitions)
        except Exception:
            # Silently ignore files that can't be parsed.
            # In a real-world scenario, we might want to log this.
            pass

class _DefinitionVisitor(ast.NodeVisitor):
    """
    An AST visitor that collects information about class and function definitions.
    """
    def __init__(self, module_fqn: str, file_path: str):
        self.module_fqn = module_fqn
        self.file_path = file_path
        self.definitions: Dict[str, Dict[str, Any]] = {}
        # Stack stores tuples of (name, type) where type is 'module', 'class', or 'function'
        self.scope_stack: List[tuple[str, str]] = [(module_fqn, "module")]

    def _get_current_fqn(self, name: str) -> str:
        """Constructs the FQN for a definition within the current scope."""
        # Join the names from the scope stack, ignoring the module name at the start
        # if it's the only thing on the stack.
        base_fqn = ".".join(s[0] for s in self.scope_stack)
        return f"{base_fqn}.{name}"

    def _get_end_line(self, node: ast.AST) -> int:
        """
        Get the end line number of a node.
        This is a bit tricky as end_lineno is not always available.
        We traverse the node's children to find the maximum line number.
        """
        if hasattr(node, 'end_lineno') and node.end_lineno is not None:
            return node.end_lineno

        max_line = node.lineno
        for child in ast.walk(node):
            if hasattr(child, 'lineno'):
                max_line = max(max_line, child.lineno)
        return max_line

    def _add_definition(self, node: ast.AST, name: str, node_type: str):
        """Adds a found definition to the index."""
        fqn = self._get_current_fqn(name)

        # Guard against adding the same FQN twice (e.g. from different files, though unlikely)
        if fqn not in self.definitions:
            self.definitions[fqn] = {
                "file_path": self.file_path,
                "start_line": node.lineno,
                "end_line": self._get_end_line(node),
                "node_type": node_type,
            }

    def visit_ClassDef(self, node: ast.ClassDef):
        """Handles class definitions."""
        self._add_definition(node, node.name, "class")

        # Push class name to scope and visit children
        self.scope_stack.append((node.name, "class"))
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Handles function and method definitions."""
        # A function is a method if its parent scope is a class.
        parent_scope_type = self.scope_stack[-1][1]
        node_type = "method" if parent_scope_type == "class" else "function"

        self._add_definition(node, node.name, node_type)

        # Handle nested functions by pushing the function itself onto the scope stack.
        self.scope_stack.append((node.name, "function"))
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Handles async function and method definitions."""
        # Treat async functions the same as regular functions for indexing purposes.
        self.visit_FunctionDef(node)
