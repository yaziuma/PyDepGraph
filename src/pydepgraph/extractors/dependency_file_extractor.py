# src/pydepgraph/extractors/dependency_file_extractor.py

import re
import tomllib
import logging
from pathlib import Path
from typing import List, Set, Optional, Dict, Any

from pydepgraph.extractors.base import ExtractorBase, RawExtractionResult
from pydepgraph.models import Module, ModuleImport

logger = logging.getLogger(__name__)

class DependencyFileExtractor(ExtractorBase):
    """
    Extracts external library dependencies from `requirements.txt` and `pyproject.toml`.
    """
    EXTRACTOR_NAME = "dependency_file"

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.project_name = self.project_path.name # Default project name
        self._dependencies: Set[str] = set()
        self._modules: List[Dict[str, Any]] = []
        self._relationships: List[Dict[str, Any]] = []

    def extract(self) -> RawExtractionResult:
        """
        Orchestrates the extraction of dependencies from supported files.
        """
        self._parse_pyproject_toml() # Parse this first to get the project name
        self._parse_requirements_txt()

        self._build_results()

        return RawExtractionResult(
            modules=self._modules,
            relationships=self._relationships,
        )

    def _parse_pyproject_toml(self):
        """Finds and parses pyproject.toml."""
        try:
            pyproject_path = self.project_path / "pyproject.toml"
            if pyproject_path.is_file():
                with open(pyproject_path, "rb") as f:
                    data = tomllib.load(f)

                # Get project name from [project.name] (PEP 621)
                if 'project' in data and 'name' in data['project']:
                    self.project_name = data['project']['name']

                # Get dependencies from [project.dependencies] (PEP 621)
                deps1 = data.get("project", {}).get("dependencies", [])
                for dep in deps1:
                    self._add_dependency(dep)

                # Get dependencies from [tool.poetry.dependencies]
                deps2 = data.get("tool", {}).get("poetry", {}).get("dependencies", {})
                for dep in deps2.keys():
                    if dep.lower() != "python": # Ignore python dependency
                        self._add_dependency(dep)
        except Exception as e:
            logger.warning(f"Could not parse pyproject.toml: {e}", exc_info=True)

    def _parse_requirements_txt(self):
        """Finds and parses requirements.txt."""
        try:
            req_path = self.project_path / "requirements.txt"
            if req_path.is_file():
                with open(req_path, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            self._add_dependency(line)
        except Exception as e:
            logger.warning(f"Could not parse requirements.txt: {e}", exc_info=True)

    def _add_dependency(self, dep_string: str):
        """Normalizes and adds a dependency string to the set."""
        # Regex to split by version specifiers
        lib_name = re.split(r'[<>=~\[]', dep_string)[0].strip()
        if lib_name:
            self._dependencies.add(lib_name)

    def _build_results(self):
        """Builds the Module and ModuleImport objects from the dependency set."""
        for lib in self._dependencies:
            # Create a Module for the external library
            # Use a unique pseudo-path for external libraries to avoid collisions in the integrator.
            file_path = f"external:{lib}"
            module_data = Module(
                name=lib,
                file_path=file_path,
                is_external=True,
                extractor=self.EXTRACTOR_NAME
            ).to_dict()
            self._modules.append(module_data)

            # Create a ModuleImport relationship from the project to the library
            import_data = ModuleImport(
                source_module=self.project_name,
                target_module=lib,
                import_type="EXTERNAL_LIBRARY",
                extractor=self.EXTRACTOR_NAME
            ).to_dict()
            self._relationships.append({
                "type": "ModuleImport",
                "data": import_data
            })

    def get_supported_file_types(self) -> List[str]:
        """Returns the file types this extractor supports."""
        return ["requirements.txt", "pyproject.toml"]
