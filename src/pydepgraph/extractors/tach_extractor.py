# pydepgraph/extractors/tach_extractor.py

from typing import List
from .base import ExtractorBase, ExtractionResult


class TachExtractor(ExtractorBase):
    """Extractor for module-level dependencies using Tach."""

    def extract(self, project_path: str) -> ExtractionResult:
        """Extracts module dependencies using Tach."""
        # This is a placeholder implementation.
        print(f"TachExtractor: Pretending to extract from {project_path}")
        return ExtractionResult(metadata={"extractor": "tach"})

    def get_supported_file_types(self) -> List[str]:
        """Returns supported file types."""
        return [".py"]
