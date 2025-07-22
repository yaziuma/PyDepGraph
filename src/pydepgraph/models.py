# pydepgraph/models.py

from dataclasses import dataclass
from typing import Optional


@dataclass
class Module:
    """Module model"""
    name: str
    file_path: str
    package: Optional[str] = None
    lines_of_code: Optional[int] = None
    complexity_score: Optional[float] = None
    extractor: Optional[str] = None


@dataclass
class Function:
    """Function model"""
    name: str
    qualified_name: str
    module_id: int
    cyclomatic_complexity: Optional[int] = None
    parameters_count: Optional[int] = None
    return_type: Optional[str] = None
    docstring: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None


@dataclass
class Class:
    """Class model"""
    name: str
    qualified_name: str
    module_id: int
    method_count: Optional[int] = None
    inheritance_depth: Optional[int] = None
    docstring: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None


@dataclass
class ModuleImport:
    """Module import relationship model"""
    source_module_id: int
    target_module_id: int
    import_type: str
    import_alias: Optional[str] = None


@dataclass
class FunctionCall:
    """Function call relationship model"""
    caller_id: int
    callee_id: int
    call_type: str
    line_number: Optional[int] = None


@dataclass
class Inheritance:
    """Class inheritance relationship model"""
    child_id: int
    parent_id: int
    inheritance_type: str = "direct"


@dataclass
class Contains:
    """Contains relationship model (module contains function/class)"""
    container_id: int
    contained_id: int
    contained_type: str  # 'function' or 'class'