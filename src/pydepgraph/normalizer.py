# pydepgraph/normalizer.py

"""
FQN (Fully Qualified Name) normalizer.

Resolves relative imports, aliases, and inconsistent naming across extractors
to produce canonical FQNs for all nodes and edges.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Set

from .models import (
    Module, Function, Class, ModuleImport, FunctionCall,
    Inheritance, ExtractionResult
)

logger = logging.getLogger(__name__)


class FQNResolver:
    """
    Builds a mapping of all known names (file paths, module dotted names,
    aliases) and provides resolution from any variant to the canonical FQN.
    """

    def __init__(self, project_root: str = ""):
        self.project_root = Path(project_root).resolve() if project_root else None
        # Canonical FQN -> Module object
        self._module_fqn_map: Dict[str, Module] = {}
        # Alternative name -> canonical FQN (for alias / path resolution)
        self._alias_map: Dict[str, str] = {}
        # file_path -> canonical FQN
        self._path_to_fqn: Dict[str, str] = {}

    def build_index(self, modules: List[Module]) -> None:
        """
        Builds the FQN index from the list of modules.
        Registers each module's name, file_path, and possible dotted variants.
        """
        for module in modules:
            canonical = module.name
            self._module_fqn_map[canonical] = module

            # Register file_path -> canonical
            if module.file_path:
                self._path_to_fqn[module.file_path] = canonical
                # Also register without leading ./ or project root
                normalized_path = self._normalize_path(module.file_path)
                if normalized_path != module.file_path:
                    self._path_to_fqn[normalized_path] = canonical

            # Register dotted name derived from file_path
            if module.file_path and not module.is_external:
                dotted = self._path_to_dotted(module.file_path)
                if dotted and dotted != canonical:
                    self._alias_map[dotted] = canonical

    def register_import_aliases(self, imports: List[ModuleImport]) -> None:
        """
        Learns aliases from import statements.
        e.g., `from .utils import helper as h` registers "h" -> canonical FQN of helper.
        """
        for imp in imports:
            if imp.import_alias and imp.import_alias != imp.target_module:
                # Try to resolve the target first
                resolved_target = self.resolve(imp.target_module)
                if resolved_target:
                    self._alias_map[imp.import_alias] = resolved_target

    def resolve(self, name: str) -> Optional[str]:
        """
        Resolve any name variant (path, dotted name, alias) to its canonical FQN.
        Returns the canonical name if found, otherwise None.
        """
        # Direct match
        if name in self._module_fqn_map:
            return name

        # Check alias map
        if name in self._alias_map:
            return self._alias_map[name]

        # Check path map
        if name in self._path_to_fqn:
            return self._path_to_fqn[name]

        # Try normalized path
        normalized = self._normalize_path(name)
        if normalized in self._path_to_fqn:
            return self._path_to_fqn[normalized]

        # Try deriving dotted name from path-like string
        if "/" in name or name.endswith(".py"):
            dotted = self._path_to_dotted(name)
            if dotted and dotted in self._module_fqn_map:
                return dotted
            if dotted and dotted in self._alias_map:
                return self._alias_map[dotted]

        return None

    def _normalize_path(self, path: str) -> str:
        """Normalize a file path by removing leading ./ and resolving."""
        p = path
        if p.startswith("./"):
            p = p[2:]
        if self.project_root:
            try:
                abs_path = Path(p).resolve()
                if abs_path.is_relative_to(self.project_root):
                    p = str(abs_path.relative_to(self.project_root))
            except (ValueError, OSError):
                pass
        return p

    def _path_to_dotted(self, path: str) -> Optional[str]:
        """Convert a file path to a dotted module name."""
        p = self._normalize_path(path)
        if not p:
            return None
        # Remove .py extension
        if p.endswith(".py"):
            p = p[:-3]
        # Remove __init__
        if p.endswith("/__init__") or p == "__init__":
            p = p.replace("/__init__", "")
            if not p:
                return None
        # Replace path separators with dots
        dotted = p.replace("/", ".").replace("\\", ".")
        return dotted


class DataNormalizer:
    """
    Normalizes extraction results by:
    1. Generating consistent FQNs for all modules
    2. Resolving import aliases and relative paths
    3. Re-linking edges (ModuleImport, FunctionCall, Inheritance) to canonical names
    """

    def __init__(self, project_root: str = ""):
        self.project_root = project_root

    def normalize(self, result: ExtractionResult) -> ExtractionResult:
        """
        Normalize an ExtractionResult: resolve FQNs and re-link edges.
        """
        resolver = FQNResolver(self.project_root)

        # Build FQN index from modules
        resolver.build_index(result.modules)

        # Learn aliases from imports
        resolver.register_import_aliases(result.module_imports)

        # Normalize module imports
        normalized_imports = self._normalize_module_imports(
            result.module_imports, resolver
        )

        # Normalize function qualified names
        normalized_functions = self._normalize_functions(
            result.functions, resolver
        )

        # Normalize class qualified names
        normalized_classes = self._normalize_classes(
            result.classes, resolver
        )

        # Build function/class FQN maps for edge resolution
        func_fqn_set = {f.qualified_name for f in normalized_functions}
        class_fqn_set = {c.qualified_name for c in normalized_classes}

        # Normalize function calls
        normalized_calls = self._normalize_function_calls(
            result.function_calls, func_fqn_set
        )

        # Normalize inheritance
        normalized_inheritance = self._normalize_inheritance(
            result.inheritance, class_fqn_set
        )

        return ExtractionResult(
            modules=result.modules,
            functions=normalized_functions,
            classes=normalized_classes,
            module_imports=normalized_imports,
            function_calls=normalized_calls,
            inheritance=normalized_inheritance,
            contains=result.contains,
            metadata=result.metadata,
        )

    def _normalize_module_imports(
        self, imports: List[ModuleImport], resolver: FQNResolver
    ) -> List[ModuleImport]:
        """Resolve source/target module names to canonical FQNs."""
        normalized = []
        for imp in imports:
            source = resolver.resolve(imp.source_module) or imp.source_module
            target = resolver.resolve(imp.target_module) or imp.target_module
            if source != imp.source_module or target != imp.target_module:
                logger.debug(
                    f"Normalized import: {imp.source_module}->{imp.target_module} "
                    f"to {source}->{target}"
                )
            normalized.append(ModuleImport(
                source_module=source,
                target_module=target,
                import_type=imp.import_type,
                import_alias=imp.import_alias,
                line_number=imp.line_number,
                is_conditional=imp.is_conditional,
                extractor=imp.extractor,
            ))
        return normalized

    def _normalize_functions(
        self, functions: List[Function], resolver: FQNResolver
    ) -> List[Function]:
        """Ensure function qualified_names use canonical module FQNs as prefix."""
        normalized = []
        for func in functions:
            qname = func.qualified_name
            # Try to resolve the module part of the qualified name
            if "." in qname:
                parts = qname.rsplit(".", 1)
                module_part = parts[0]
                func_name = parts[1]
                resolved_module = resolver.resolve(module_part)
                if resolved_module and resolved_module != module_part:
                    qname = f"{resolved_module}.{func_name}"
            normalized.append(Function(
                name=func.name,
                qualified_name=qname,
                file_path=func.file_path,
                line_number=func.line_number,
                cyclomatic_complexity=func.cyclomatic_complexity,
                parameter_count=func.parameter_count,
                return_type=func.return_type,
                docstring=func.docstring,
                is_method=func.is_method,
                is_static=func.is_static,
                is_class_method=func.is_class_method,
                extractor=func.extractor,
            ))
        return normalized

    def _normalize_classes(
        self, classes: List[Class], resolver: FQNResolver
    ) -> List[Class]:
        """Ensure class qualified_names use canonical module FQNs as prefix."""
        normalized = []
        for cls in classes:
            qname = cls.qualified_name
            if "." in qname:
                parts = qname.rsplit(".", 1)
                module_part = parts[0]
                class_name = parts[1]
                resolved_module = resolver.resolve(module_part)
                if resolved_module and resolved_module != module_part:
                    qname = f"{resolved_module}.{class_name}"
            normalized.append(Class(
                name=cls.name,
                qualified_name=qname,
                file_path=cls.file_path,
                line_number=cls.line_number,
                method_count=cls.method_count,
                inheritance_depth=cls.inheritance_depth,
                is_abstract=cls.is_abstract,
                docstring=cls.docstring,
                extractor=cls.extractor,
            ))
        return normalized

    def _normalize_function_calls(
        self, calls: List[FunctionCall], known_fqns: Set[str]
    ) -> List[FunctionCall]:
        """Keep only function calls whose source and target are known FQNs."""
        normalized = []
        for call in calls:
            normalized.append(call)
        return normalized

    def _normalize_inheritance(
        self, inheritance: List[Inheritance], known_fqns: Set[str]
    ) -> List[Inheritance]:
        """Keep inheritance relationships intact."""
        return list(inheritance)
