# tests/test_integration.py

import pytest
import tempfile
import shutil
from pathlib import Path

# Import placeholder classes from the project
from pydepgraph.incremental import IncrementalAnalyzer
from pydepgraph.database import GraphDatabase, OptimizedGraphDatabase
from pydepgraph.parallel import ParallelAnalyzer
from pydepgraph.reporting import AdvancedReporter
from pydepgraph.services.analytics_service import GraphAnalyticsService
from pydepgraph.services.query_service import CachedQueryService, QueryCache

# Mark all tests in this file as "integration"
pytestmark = pytest.mark.integration


@pytest.fixture
def temp_project():
    """Creates a temporary directory with a few sample Python files for testing."""
    temp_dir = Path(tempfile.mkdtemp(prefix="pydepgraph_test_"))

    # Create sample Python files
    (temp_dir / "main.py").write_text(
        '"""Main entry point."""\n'
        "from utils import helper\n\n"
        "def main():\n"
        "    helper.do_something()\n"
    )

    (temp_dir / "utils.py").write_text(
        '"""Utility functions."""\n\n'
        "class HelperClass:\n"
        "    def method1(self):\n"
        "        return self.method2()\n\n"
        "    def method2(self):\n"
        '        return "Method 2"\n\n'
        "def do_something():\n"
        '    return "Done"\n'
    )

    yield temp_dir

    # Cleanup the temporary directory
    shutil.rmtree(temp_dir)


class TestPhase5Integration:
    """
    Integration tests based on the Phase 5 detailed design.
    Most tests are skipped as the underlying logic is not yet implemented.
    """

    @pytest.mark.skip(reason="Incremental analysis logic not yet implemented.")
    def test_incremental_analysis(self, temp_project):
        """Tests the incremental analysis functionality."""
        db_path = temp_project / "test.db"
        db = GraphDatabase(str(db_path))
        analyzer = IncrementalAnalyzer(db)

        # First-time analysis
        result1 = analyzer.analyze_incremental(temp_project)
        assert result1["status"] == "completed"
        assert result1["added"] >= 2  # main.py, utils.py

        # Create a new file
        (temp_project / "new_file.py").write_text("def new_function(): pass")

        # Incremental analysis should detect the new file
        result2 = analyzer.analyze_incremental(temp_project)
        assert result2["status"] == "completed"
        assert result2["added"] == 1
        assert result2["modified"] == 0

    @pytest.mark.skip(reason="Performance optimization logic not yet implemented.")
    def test_performance_optimization(self, temp_project):
        """Tests performance optimization features like indexing."""
        db_path = temp_project / "test_opt.db"
        db = OptimizedGraphDatabase(str(db_path))
        db.initialize_schema()

        query = "MATCH (m:Module) RETURN m.name ORDER BY m.name"
        optimized_query = db.optimize_query_plan(query)

        # Check if a basic optimization (like adding LIMIT) is applied
        assert "LIMIT" in optimized_query

    @pytest.mark.skip(reason="Parallel processing logic not yet implemented.")
    def test_parallel_processing(self, temp_project):
        """Tests the parallel analysis execution."""
        parallel_analyzer = ParallelAnalyzer()
        result = parallel_analyzer.analyze_project_parallel(temp_project)

        assert result is not None
        assert result.metadata["extractor"] in ["tach", "code2flow"]

    @pytest.mark.skip(reason="Reporting logic not yet implemented.")
    def test_comprehensive_reporting(self, temp_project):
        """Tests the generation of comprehensive analysis reports."""
        db_path = temp_project / "test_report.db"
        db = GraphDatabase(str(db_path))
        db.initialize_schema()

        # Insert some dummy data for the report
        db.bulk_insert_modules(
            [{"id": "m1", "name": "test_module", "file_path": "test.py"}]
        )

        analytics = GraphAnalyticsService(db)
        reporter = AdvancedReporter(analytics)

        report_dir = temp_project / "reports"
        report_dir.mkdir()

        reporter.generate_comprehensive_report(report_dir)

        # Check if report files were created
        assert (report_dir / "report.json").exists()
        assert (report_dir / "report.html").exists()

    def test_cache_functionality(self):
        """Tests the basic functionality of the query cache."""
        cache = QueryCache(max_size=2, ttl=10)

        cache.set("key1", [{"data": "value1"}])
        cache.set("key2", [{"data": "value2"}])

        assert cache.get("key1") == [{"data": "value1"}]
        assert cache.get("key2") is not None

        # Test cache size limit
        cache.set("key3", [{"data": "value3"}])
        assert cache.get("key1") is None  # Oldest entry should be evicted
        assert cache.get("key2") is not None
        assert cache.get("key3") is not None


@pytest.mark.skip(reason="End-to-end workflow requires full implementation.")
def test_end_to_end_workflow(temp_project):
    """A full end-to-end workflow test."""
    db_path = temp_project / "workflow_test.db"

    # 1. Analyze project in parallel
    analyzer = ParallelAnalyzer()
    result = analyzer.analyze_project_parallel(temp_project)

    # 2. Store results in an optimized database
    db = OptimizedGraphDatabase(str(db_path))
    db.initialize_schema()
    if result.modules:
        db.bulk_insert_modules(result.modules)
    if result.functions:
        db.bulk_insert_functions(result.functions)

    # 3. Query data using a cached service
    query_service = CachedQueryService(db)
    search_result = query_service.search_by_name("main", "function")
    assert search_result.total_count == 0  # Placeholder returns empty

    # 4. Get statistics
    analytics = GraphAnalyticsService(db)
    stats = analytics.get_graph_statistics()
    assert "module_count" in stats

    # 5. Generate a report
    reporter = AdvancedReporter(analytics)
    report_dir = temp_project / "final_report"
    report_dir.mkdir()
    reporter.generate_comprehensive_report(report_dir)
    assert (report_dir / "report.json").exists()
