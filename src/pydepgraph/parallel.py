# pydepgraph/parallel.py
import logging
from pathlib import Path
from .extractors.base import ExtractionResult
from .extractors.tach_extractor import TachExtractor
from .extractors.code2flow_extractor import Code2FlowExtractor
from .normalizer import DataNormalizer

logger = logging.getLogger(__name__)


class ParallelAnalyzer:
    """Runs analysis in parallel."""

    def __init__(self):
        self.tach_extractor = TachExtractor()
        self.code2flow_extractor = Code2FlowExtractor()
        self.normalizer = DataNormalizer()

    def analyze_project_parallel(self, project_path: Path) -> ExtractionResult:
        logger.info(f"Starting parallel analysis for {project_path}")
        tach_result = self.tach_extractor.extract(str(project_path))
        code2flow_result = self.code2flow_extractor.extract(str(project_path))
        return self.normalizer.normalize_extraction_results(
            [tach_result, code2flow_result]
        )
