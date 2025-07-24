# pydepgraph/incremental.py
import logging
from pathlib import Path
from typing import Dict, Set, Tuple
from .database import GraphDatabase

logger = logging.getLogger(__name__)


class FileChangeDetector:
    """Detects file changes in a project directory."""

    def detect_changes(
        self, project_path: Path
    ) -> Tuple[Set[Path], Set[Path], Set[Path]]:
        logger.info(f"Detecting changes in {project_path}")
        # Placeholder: Pretend the first two files are new.
        py_files = list(project_path.glob("**/*.py"))
        return set(py_files[:2]), set(), set()


class IncrementalAnalyzer:
    """Performs incremental analysis of a project."""

    def __init__(self, database: GraphDatabase):
        self.database = database
        self.detector = FileChangeDetector()

    def analyze_incremental(self, project_path: Path) -> Dict[str, any]:
        logger.info(f"Starting incremental analysis for {project_path}")
        added, modified, deleted = self.detector.detect_changes(project_path)
        return {
            "status": "completed",
            "added": len(added),
            "modified": len(modified),
            "deleted": len(deleted),
        }
