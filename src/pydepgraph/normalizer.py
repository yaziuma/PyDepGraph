# pydepgraph/normalizer.py
from typing import List
from .extractors.base import ExtractionResult


class DataNormalizer:
    """Normalizes and merges data from multiple extractors."""

    def normalize_extraction_results(
        self, results: List[ExtractionResult]
    ) -> ExtractionResult:
        """Normalizes and merges multiple extraction results."""
        # This is a placeholder implementation.
        print(f"DataNormalizer: Normalizing {len(results)} results.")
        if not results:
            return ExtractionResult()

        # Simple merge for placeholder
        final_result = ExtractionResult()
        for res in results:
            final_result.modules.extend(res.modules)
            final_result.functions.extend(res.functions)
            final_result.classes.extend(res.classes)
            final_result.relationships.extend(res.relationships)
            final_result.metadata.update(res.metadata)
        return final_result
