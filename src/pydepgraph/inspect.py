# pydepgraph/inspect.py

"""
LLM-friendly AST structure inspector.

Produces a compact JSON summary of a Python file's public interface:
function/method signatures, class definitions, and their relationships --
without implementation details, to minimise token usage for LLM consumers.
"""

import ast
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .exceptions import PyDepGraphError
from .utils.file_filter import iter_python_files

logger = logging.getLogger(__name__)


def inspect_target(target: str) -> Dict[str, Any]:
    """
    Inspect a Python file or directory and return an LLM-friendly AST summary.

    Args:
        target: Path to a .py file, or a directory containing Python files.

    Returns:
        A dict with keys:
          - file_path: the inspected file
          - definitions: list of function/class signature summaries
    """
    path = Path(target)

    if path.is_file() and path.suffix == ".py":
        return _inspect_file(path)
    elif path.is_dir():
        return _inspect_directory(path)
    else:
        # Try treating as a module path (dotted name)
        module_path = target.replace(".", "/")
        candidates = [
            Path(module_path + ".py"),
            Path(module_path) / "__init__.py",
        ]
        for candidate in candidates:
            if candidate.is_file():
                return _inspect_file(candidate)

        raise PyDepGraphError(
            f"Cannot inspect target '{target}': not a valid Python file, "
            f"directory, or module path"
        )


def render_skeleton(target: str, exclude_patterns: Optional[List[str]] = None) -> str:
    """
    Render Python interface skeleton text for a file or directory.

    Function bodies are omitted and replaced by ellipsis-style signatures.
    """
    path = Path(target)
    if path.is_file() and path.suffix == ".py":
        return _render_file_skeleton(path)
    if path.is_dir():
        chunks: List[str] = []
        for py_file in sorted(iter_python_files(path, exclude_patterns)):
            chunks.append(_render_file_skeleton(py_file))
        return "\n\n".join(chunks)
    raise PyDepGraphError(f"Cannot render skeleton for target '{target}'")


def render_target_function(target: str, function_name: str) -> str:
    """Render full source implementation for the first matching function/method."""
    path = Path(target)
    if not path.is_file():
        raise PyDepGraphError(f"Target must be a Python file: '{target}'")
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    lines = source.splitlines()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
            if getattr(node, "end_lineno", None) is None:
                continue
            snippet = "\n".join(lines[node.lineno - 1 : node.end_lineno])
            return f"# {path}\n{snippet}"
    raise PyDepGraphError(f"Function '{function_name}' not found in '{target}'")


def render_context(target: str, depth: int = 1, project_root: Optional[str] = None) -> str:
    """
    Render dependency-aware context for LLM usage.

    Dependencies are rendered as skeletons, while target is rendered in full.
    """
    target_path = Path(target).resolve()
    if not target_path.is_file():
        raise PyDepGraphError(f"Target must be a Python file: '{target}'")

    root = Path(project_root).resolve() if project_root else target_path.parent.resolve()
    module_map = _build_module_map(root)
    dependency_paths = _collect_local_dependency_files(target_path, root, module_map, max(depth, 0))
    dependency_paths = [p for p in dependency_paths if p != target_path]

    sections: List[str] = []
    sections.append("=== Dependencies (Skeleton) ===")
    if dependency_paths:
        for dep_path in sorted(dependency_paths):
            sections.append(_render_file_skeleton(dep_path))
    else:
        sections.append("(none)")

    sections.append("\n=== Target Implementation ===")
    sections.append(f"# {target_path}")
    sections.append(target_path.read_text(encoding="utf-8"))
    return "\n".join(sections)


def _inspect_directory(dir_path: Path, exclude_patterns: Optional[List[str]] = None) -> Dict[str, Any]:
    """Inspect all Python files in a directory."""
    results: List[Dict[str, Any]] = []
    for py_file in sorted(iter_python_files(dir_path, exclude_patterns)):
        try:
            file_result = _inspect_file(py_file)
            if file_result.get("definitions"):
                results.append(file_result)
        except Exception as e:
            logger.debug(f"Failed to inspect {py_file}: {e}")

    return {
        "directory": str(dir_path),
        "file_count": len(results),
        "files": results,
    }


def _inspect_file(file_path: Path) -> Dict[str, Any]:
    """
    Parse a single Python file and extract its public interface.

    Returns a dict containing:
      - file_path: str
      - module_docstring: Optional[str]
      - definitions: list of dicts describing classes, functions, etc.
    """
    try:
        source = file_path.read_text(encoding="utf-8")
    except Exception as e:
        raise PyDepGraphError(f"Cannot read file '{file_path}': {e}")

    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError as e:
        raise PyDepGraphError(f"Syntax error in '{file_path}': {e}")

    module_docstring = ast.get_docstring(tree)
    definitions: List[Dict[str, Any]] = []

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            definitions.append(_extract_class(node, source))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            definitions.append(_extract_function(node, source))
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            const = _extract_module_constant(node, source)
            if const:
                definitions.append(const)

    # Extract imports summary
    imports = _extract_imports(tree)

    result: Dict[str, Any] = {
        "file_path": str(file_path),
        "definitions": definitions,
    }
    if module_docstring:
        result["module_docstring"] = module_docstring
    if imports:
        result["imports"] = imports

    return result


def _render_file_skeleton(file_path: Path) -> str:
    source = file_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(file_path))
    module_docstring = ast.get_docstring(tree)
    lines: List[str] = [f"# {file_path}"]
    if module_docstring:
        lines.append(f'"""{module_docstring}"""')

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            lines.extend(_render_class_skeleton_lines(node))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            lines.append(f"{_build_node_signature(node)}: ...")
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            const = _extract_module_constant(node, source)
            if const:
                annotation = const.get("annotation")
                if annotation:
                    lines.append(f"{const['name']}: {annotation}")
                else:
                    lines.append(const["name"])
    return "\n".join(lines)


def _render_class_skeleton_lines(node: ast.ClassDef) -> List[str]:
    bases = [_get_annotation_str(b) for b in node.bases]
    header = f"class {node.name}"
    if bases:
        header += f"({', '.join(bases)})"
    header += ":"
    lines: List[str] = [header]

    class_doc = ast.get_docstring(node)
    if class_doc:
        lines.append(f'    """{class_doc}"""')

    members = 0
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            lines.append(f"    {_build_node_signature(child)}: ...")
            members += 1
        elif isinstance(child, ast.AnnAssign):
            var = _extract_class_variable(child)
            if var:
                lines.append(f"    {var['name']}: {var['type']}")
                members += 1

    if members == 0:
        lines.append("    ...")
    return lines


def _build_node_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    params = _extract_parameters(node.args)
    return_annotation = _get_annotation_str(node.returns) if node.returns else None
    return _build_signature(node.name, params, return_annotation, isinstance(node, ast.AsyncFunctionDef))


def _build_module_map(root: Path, exclude_patterns: Optional[List[str]] = None) -> Dict[str, Path]:
    module_map: Dict[str, Path] = {}
    for py_file in iter_python_files(root, exclude_patterns):
        rel = py_file.relative_to(root)
        if rel.name == "__init__.py":
            module_name = ".".join(rel.parent.parts) if rel.parent.parts else ""
        else:
            module_name = ".".join(rel.with_suffix("").parts)
        module_map[module_name] = py_file
    return module_map


def _collect_local_dependency_files(
    target_path: Path,
    root: Path,
    module_map: Dict[str, Path],
    depth: int,
) -> List[Path]:
    discovered: List[Path] = []
    visited: set[Path] = set()
    frontier: List[Path] = [target_path]

    for _ in range(depth):
        next_frontier: List[Path] = []
        for file_path in frontier:
            for dep in _resolve_local_import_paths(file_path, root, module_map):
                if dep not in visited and dep.exists():
                    visited.add(dep)
                    discovered.append(dep)
                    next_frontier.append(dep)
        frontier = next_frontier
        if not frontier:
            break
    return discovered


def _resolve_local_import_paths(file_path: Path, root: Path, module_map: Dict[str, Path]) -> List[Path]:
    source = file_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(file_path))
    imports: List[Path] = []
    current_module = _module_name_from_path(file_path, root)
    current_parts = current_module.split(".") if current_module else []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_name = alias.name
                path = module_map.get(module_name)
                if path:
                    imports.append(path)
        elif isinstance(node, ast.ImportFrom):
            base_module = node.module or ""
            if node.level > 0:
                anchor_parts = current_parts[: -node.level] if node.level <= len(current_parts) else []
                if base_module:
                    base_module = ".".join(anchor_parts + base_module.split("."))
                else:
                    base_module = ".".join(anchor_parts)
            for alias in node.names:
                candidates = []
                if base_module:
                    candidates.append(f"{base_module}.{alias.name}")
                    candidates.append(base_module)
                else:
                    candidates.append(alias.name)
                for module_name in candidates:
                    path = module_map.get(module_name)
                    if path:
                        imports.append(path)
                        break
    return imports


def _module_name_from_path(path: Path, root: Path) -> str:
    rel = path.relative_to(root)
    if rel.name == "__init__.py":
        return ".".join(rel.parent.parts)
    return ".".join(rel.with_suffix("").parts)


def _extract_function(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    source: str,
) -> Dict[str, Any]:
    """Extract function/method signature information."""
    is_async = isinstance(node, ast.AsyncFunctionDef)
    params = _extract_parameters(node.args)
    return_annotation = _get_annotation_str(node.returns) if node.returns else None
    decorators = [_get_decorator_str(d) for d in node.decorator_list]
    docstring = ast.get_docstring(node)

    result: Dict[str, Any] = {
        "type": "function",
        "name": node.name,
        "signature": _build_signature(node.name, params, return_annotation, is_async),
        "line": node.lineno,
    }
    if decorators:
        result["decorators"] = decorators
    if docstring:
        result["docstring"] = docstring
    if is_async:
        result["async"] = True

    return result


def _extract_class(node: ast.ClassDef, source: str) -> Dict[str, Any]:
    """Extract class definition with methods."""
    bases = [_get_annotation_str(b) for b in node.bases]
    decorators = [_get_decorator_str(d) for d in node.decorator_list]
    docstring = ast.get_docstring(node)

    methods: List[Dict[str, Any]] = []
    class_variables: List[Dict[str, Any]] = []

    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            methods.append(_extract_function(child, source))
        elif isinstance(child, ast.AnnAssign):
            var = _extract_class_variable(child)
            if var:
                class_variables.append(var)

    result: Dict[str, Any] = {
        "type": "class",
        "name": node.name,
        "line": node.lineno,
    }
    if bases:
        result["bases"] = bases
    if decorators:
        result["decorators"] = decorators
    if docstring:
        result["docstring"] = docstring
    if methods:
        result["methods"] = methods
    if class_variables:
        result["class_variables"] = class_variables

    return result


def _extract_parameters(args: ast.arguments) -> List[Dict[str, Any]]:
    """Extract function parameter information."""
    params: List[Dict[str, Any]] = []

    # Count defaults offset
    num_args = len(args.args)
    num_defaults = len(args.defaults)
    default_offset = num_args - num_defaults

    for i, arg in enumerate(args.args):
        if arg.arg == "self" or arg.arg == "cls":
            continue
        param: Dict[str, Any] = {"name": arg.arg}
        if arg.annotation:
            param["type"] = _get_annotation_str(arg.annotation)
        # Check if this argument has a default
        default_idx = i - default_offset
        if default_idx >= 0 and default_idx < num_defaults:
            param["default"] = _get_default_str(args.defaults[default_idx])
        params.append(param)

    # *args
    if args.vararg:
        param = {"name": f"*{args.vararg.arg}"}
        if args.vararg.annotation:
            param["type"] = _get_annotation_str(args.vararg.annotation)
        params.append(param)

    # keyword-only args
    for i, arg in enumerate(args.kwonlyargs):
        param = {"name": arg.arg}
        if arg.annotation:
            param["type"] = _get_annotation_str(arg.annotation)
        kw_default = args.kw_defaults[i] if i < len(args.kw_defaults) else None
        if kw_default is not None:
            param["default"] = _get_default_str(kw_default)
        params.append(param)

    # **kwargs
    if args.kwarg:
        param = {"name": f"**{args.kwarg.arg}"}
        if args.kwarg.annotation:
            param["type"] = _get_annotation_str(args.kwarg.annotation)
        params.append(param)

    return params


def _extract_class_variable(node: ast.AnnAssign) -> Optional[Dict[str, Any]]:
    """Extract a class-level annotated variable."""
    if not isinstance(node.target, ast.Name):
        return None
    result: Dict[str, Any] = {
        "name": node.target.id,
        "type": _get_annotation_str(node.annotation),
    }
    return result


def _extract_module_constant(
    node: ast.Assign | ast.AnnAssign, source: str
) -> Optional[Dict[str, Any]]:
    """Extract module-level constant assignment (ALL_CAPS names only)."""
    if isinstance(node, ast.AnnAssign):
        if isinstance(node.target, ast.Name) and node.target.id.isupper():
            return {
                "type": "constant",
                "name": node.target.id,
                "annotation": _get_annotation_str(node.annotation),
                "line": node.lineno,
            }
    elif isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id.isupper():
                return {
                    "type": "constant",
                    "name": target.id,
                    "line": node.lineno,
                }
    return None


def _extract_imports(tree: ast.Module) -> List[str]:
    """Extract import statements as concise strings."""
    imports: List[str] = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname:
                    imports.append(f"import {alias.name} as {alias.asname}")
                else:
                    imports.append(f"import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            dots = "." * (node.level or 0)
            names = ", ".join(
                f"{a.name} as {a.asname}" if a.asname else a.name
                for a in node.names
            )
            imports.append(f"from {dots}{module} import {names}")
    return imports


def _get_annotation_str(node: Optional[ast.expr]) -> str:
    """Convert an annotation AST node to a string representation."""
    if node is None:
        return ""
    return ast.unparse(node)


def _get_decorator_str(node: ast.expr) -> str:
    """Convert a decorator AST node to a string representation."""
    return ast.unparse(node)


def _get_default_str(node: ast.expr) -> str:
    """Convert a default value AST node to a string representation."""
    return ast.unparse(node)


def _build_signature(
    name: str,
    params: List[Dict[str, Any]],
    return_annotation: Optional[str],
    is_async: bool = False,
) -> str:
    """Build a human-readable function signature string."""
    param_strs = []
    for p in params:
        s = p["name"]
        if "type" in p:
            s += f": {p['type']}"
        if "default" in p:
            s += f" = {p['default']}"
        param_strs.append(s)

    prefix = "async def" if is_async else "def"
    sig = f"{prefix} {name}({', '.join(param_strs)})"
    if return_annotation:
        sig += f" -> {return_annotation}"
    return sig
