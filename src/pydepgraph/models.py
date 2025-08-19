# pydepgraph/models.py

from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any, Union


@dataclass(frozen=True)
class Module:
    """Module model"""
    name: str
    file_path: str
    package: Optional[str] = None
    lines_of_code: Optional[int] = None
    complexity_score: Optional[float] = None
    is_external: bool = False
    is_test: bool = False
    extractor: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Function:
    """Function model"""
    name: str
    qualified_name: str
    file_path: str
    line_number: Optional[int] = None
    cyclomatic_complexity: Optional[int] = None
    parameter_count: Optional[int] = None
    return_type: Optional[str] = None
    docstring: Optional[str] = None
    is_method: bool = False
    is_static: bool = False
    is_class_method: bool = False
    extractor: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Class:
    """Class model"""
    name: str
    qualified_name: str
    file_path: str
    line_number: Optional[int] = None
    method_count: Optional[int] = None
    inheritance_depth: Optional[int] = None
    is_abstract: bool = False
    docstring: Optional[str] = None
    extractor: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ModuleImport:
    """Module import relationship model"""
    source_module: str
    target_module: str
    import_type: str = "standard"
    import_alias: Optional[str] = None
    line_number: Optional[int] = None
    is_conditional: bool = False
    extractor: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FunctionCall:
    """Function call relationship model"""
    source_function: str
    target_function: str
    call_type: str = "direct"
    line_number: Optional[int] = None
    is_conditional: bool = False
    extractor: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Inheritance:
    """Class inheritance relationship model"""
    child_class: str
    parent_class: str
    inheritance_type: str = "direct"
    line_number: Optional[int] = None
    extractor: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Contains:
    """Contains relationship model (module contains function/class)"""
    container: str
    contained: str
    contained_type: str  # 'function' or 'class'
    extractor: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExtractionResult:
    """Complete extraction result"""
    modules: List[Module]
    functions: List[Function]
    classes: List[Class]
    module_imports: List[ModuleImport]
    function_calls: List[FunctionCall]
    inheritance: List[Inheritance]
    contains: List[Contains]
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            'modules': [m.to_dict() for m in self.modules],
            'functions': [f.to_dict() for f in self.functions],
            'classes': [c.to_dict() for c in self.classes],
            'module_imports': [mi.to_dict() for mi in self.module_imports],
            'function_calls': [fc.to_dict() for fc in self.function_calls],
            'inheritance': [i.to_dict() for i in self.inheritance],
            'contains': [c.to_dict() for c in self.contains],
            'metadata': self.metadata
        }

    def all_nodes(self) -> List[Union[Module, Function, Class]]:
        """Returns a list of all node objects."""
        return self.modules + self.functions + self.classes

    def all_edges(self) -> List[Union[ModuleImport, FunctionCall, Inheritance]]:
        """Returns a list of all comparable edge objects."""
        return self.module_imports + self.function_calls + self.inheritance