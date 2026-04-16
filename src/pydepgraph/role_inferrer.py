# pydepgraph/role_inferrer.py

"""
Heuristic-based role inference for modules.

Assigns a `role` label (e.g. "api", "service", "model", "cli", "test", "config",
"util", "data_access") to each Module by inspecting:
  1. Directory name patterns
  2. File name patterns
  3. Class inheritance patterns (from AST)
"""

import ast
import logging
import re
from pathlib import Path
from typing import Optional, List

from .models import Module

logger = logging.getLogger(__name__)

# Directory name -> role mapping (checked against any component in the path)
_DIR_ROLE_MAP: dict[str, str] = {
    "api": "api",
    "apis": "api",
    "endpoints": "api",
    "routes": "api",
    "views": "api",
    "handlers": "api",
    "controllers": "api",
    "service": "service",
    "services": "service",
    "usecase": "service",
    "usecases": "service",
    "model": "model",
    "models": "model",
    "schemas": "model",
    "entities": "model",
    "domain": "model",
    "cli": "cli",
    "commands": "cli",
    "cmd": "cli",
    "test": "test",
    "tests": "test",
    "testing": "test",
    "config": "config",
    "configs": "config",
    "settings": "config",
    "conf": "config",
    "util": "util",
    "utils": "util",
    "helpers": "util",
    "common": "util",
    "shared": "util",
    "lib": "util",
    "db": "data_access",
    "database": "data_access",
    "dao": "data_access",
    "repositories": "data_access",
    "repository": "data_access",
    "persistence": "data_access",
    "migrations": "data_access",
    "middleware": "middleware",
    "extractors": "extractor",
    "parsers": "extractor",
    "reporting": "reporting",
    "reports": "reporting",
}

# File name patterns -> role mapping
_FILE_ROLE_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"^test_|_test\.py$|^tests\.py$"), "test"),
    (re.compile(r"^conftest\.py$"), "test"),
    (re.compile(r"^cli\.py$|^__main__\.py$"), "cli"),
    (re.compile(r"^config\.py$|^settings\.py$|^conf\.py$"), "config"),
    (re.compile(r"^models?\.py$|^schemas?\.py$|^entities\.py$"), "model"),
    (re.compile(r"^views?\.py$|^routes?\.py$|^endpoints?\.py$|^handlers?\.py$"), "api"),
    (re.compile(r"^services?\.py$"), "service"),
    (re.compile(r"^utils?\.py$|^helpers?\.py$|^common\.py$"), "util"),
    (re.compile(r"^db\.py$|^database\.py$|^dao\.py$"), "data_access"),
    (re.compile(r"^exceptions?\.py$|^errors?\.py$"), "util"),
    (re.compile(r"^middleware\.py$"), "middleware"),
]

# Base class names that hint at a role
_BASE_CLASS_ROLE_MAP: dict[str, str] = {
    "BaseModel": "model",
    "Model": "model",
    "Schema": "model",
    "SQLModel": "model",
    "DeclarativeBase": "model",
    "APIRouter": "api",
    "Resource": "api",
    "ViewSet": "api",
    "View": "api",
    "TestCase": "test",
    "Command": "cli",
    "BaseCommand": "cli",
}


def infer_role(module: Module) -> Optional[str]:
    """
    Infers the role of a module using heuristic rules.
    Returns the inferred role string, or None if no strong signal is found.
    """
    if module.is_test:
        return "test"

    if module.is_external:
        return "external"

    file_path = module.file_path

    # 1. Check directory name
    role = _infer_from_directory(file_path)
    if role:
        return role

    # 2. Check file name patterns
    role = _infer_from_filename(file_path)
    if role:
        return role

    # 3. Check base class names via AST
    role = _infer_from_base_classes(file_path)
    if role:
        return role

    # 4. Check function name patterns in the file
    role = _infer_from_function_names(file_path)
    if role:
        return role

    return None


def _infer_from_directory(file_path: str) -> Optional[str]:
    """Infer role from directory name components."""
    if not file_path:
        return None
    parts = Path(file_path).parts
    for part in parts:
        lower = part.lower()
        if lower in _DIR_ROLE_MAP:
            return _DIR_ROLE_MAP[lower]
    return None


def _infer_from_filename(file_path: str) -> Optional[str]:
    """Infer role from file name patterns."""
    if not file_path:
        return None
    filename = Path(file_path).name
    for pattern, role in _FILE_ROLE_PATTERNS:
        if pattern.search(filename):
            return role
    return None


def _infer_from_base_classes(file_path: str) -> Optional[str]:
    """Infer role from base class names found in the file's AST."""
    if not file_path:
        return None
    path = Path(file_path)
    if not path.is_file() or path.suffix != ".py":
        return None

    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except Exception:
        return None

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                base_name = _get_base_name(base)
                if base_name and base_name in _BASE_CLASS_ROLE_MAP:
                    return _BASE_CLASS_ROLE_MAP[base_name]
    return None


def _infer_from_function_names(file_path: str) -> Optional[str]:
    """Infer role from function name patterns in the file."""
    if not file_path:
        return None
    path = Path(file_path)
    if not path.is_file() or path.suffix != ".py":
        return None

    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except Exception:
        return None

    test_count = 0
    total_count = 0
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            total_count += 1
            if node.name.startswith("test_"):
                test_count += 1

    if total_count > 0 and test_count / total_count >= 0.5:
        return "test"

    return None


def _get_base_name(base_node: ast.expr) -> Optional[str]:
    """Extract the simple name from a base class AST node."""
    if isinstance(base_node, ast.Name):
        return base_node.id
    elif isinstance(base_node, ast.Attribute):
        return base_node.attr
    return None


def infer_roles_for_modules(modules: List[Module]) -> List[Module]:
    """
    Assigns inferred roles to a list of modules.
    Returns new Module objects with the role field populated.
    """
    result = []
    for module in modules:
        if module.role is not None:
            result.append(module)
            continue
        role = infer_role(module)
        if role:
            # Create a new frozen dataclass with the role set
            result.append(Module(
                name=module.name,
                file_path=module.file_path,
                package=module.package,
                lines_of_code=module.lines_of_code,
                complexity_score=module.complexity_score,
                is_external=module.is_external,
                is_test=module.is_test,
                extractor=module.extractor,
                role=role,
            ))
        else:
            result.append(module)
    return result
