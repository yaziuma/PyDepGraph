# pydepgraph/extractors/code2flow_extractor.py

from typing import List
from .base import ExtractorBase, ExtractionResult


class Code2FlowExtractor(ExtractorBase):
    """Extractor for function-level dependencies using Code2Flow."""

    def extract(self, project_path: str) -> ExtractionResult:
        """Extracts function call dependencies using Code2Flow."""
        # This is a placeholder implementation.
        print(f"Code2FlowExtractor: Pretending to extract from {project_path}")
        return ExtractionResult(metadata={"extractor": "code2flow"})

    def get_supported_file_types(self) -> List[str]:
        """Returns supported file types."""
        return [".py"]
