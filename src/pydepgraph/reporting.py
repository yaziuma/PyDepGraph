# pydepgraph/reporting.py
import logging
from pathlib import Path
from .services.analytics_service import GraphAnalyticsService

logger = logging.getLogger(__name__)


class AdvancedReporter:
    """Generates advanced analysis reports."""

    def __init__(self, analytics: GraphAnalyticsService):
        self.analytics = analytics

    def generate_comprehensive_report(self, output_path: Path) -> None:
        logger.info(f"Generating comprehensive report to {output_path}")
        (output_path / "report.json").touch()
        (output_path / "report.html").touch()
