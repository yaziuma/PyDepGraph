# pydepgraph/extractors/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Any


@dataclass
class ExtractionResult:
    """Represents the result of an extraction process."""

    modules: List[Dict[str, Any]] = field(default_factory=list)
    functions: List[Dict[str, Any]] = field(default_factory=list)
    classes: List[Dict[str, Any]] = field(default_factory=list)
    relationships: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ExtractorBase(ABC):
    """Abstract base class for all dependency extractors."""

    @abstractmethod
    def extract(self, project_path: str) -> ExtractionResult:
        """
        Extracts dependency information from a project.

        Args:
            project_path: The root path of the project to analyze.

        Returns:
            An ExtractionResult object containing the extracted data.
        """
        pass

    @abstractmethod
    def get_supported_file_types(self) -> List[str]:
        """
        Returns a list of file extensions supported by the extractor.

        Returns:
            A list of strings, e.g., ['.py', '.pyi'].
        """
        pass
