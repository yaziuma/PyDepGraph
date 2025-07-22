# tests/test_integration.py

import pytest
import tempfile
import shutil
from pathlib import Path

# Import placeholder classes from the project
from pydepgraph.incremental import IncrementalAnalyzer
from pydepgraph.database import GraphDatabase
from pydepgraph.parallel import ParallelAnalyzer
from pydepgraph.reporting import AdvancedReporter
from pydepgraph.services.analytics_service import GraphAnalyticsService
from pydepgraph.services.query_service import BasicQueryService

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


import json
import subprocess

def test_phase1_integration(temp_project, monkeypatch):
    """Phase1の統合テスト"""
    from pydepgraph.extractors.tach_extractor import TachExtractor
    from pydepgraph.database import GraphDatabase
    from pydepgraph.services.query_service import BasicQueryService

    # tachの出力をモック
    dummy_output = {
        "main.py": ["utils.py"],
        "utils.py": [],
    }
    dummy_json = json.dumps(dummy_output)

    def mock_subprocess_run(*args, **kwargs):
        return subprocess.CompletedProcess(args[0], 0, stdout=dummy_json)

    monkeypatch.setattr(subprocess, "run", mock_subprocess_run)

    # 1. TachExtractor動作確認
    extractor = TachExtractor()
    result = extractor.extract(str(temp_project))

    assert len(result.modules) == 2
    assert len(result.relationships) == 1
    assert result.metadata['extractor'] == 'tach'

    # 2. GraphDatabase動作確認
    db_path = temp_project / "test.db"
    db = GraphDatabase(str(db_path))
    db.initialize_schema()
    db.bulk_insert_modules(result.modules)
    db.bulk_insert_module_imports(result.relationships)

    # 3. 基本クエリ動作確認
    query_service = BasicQueryService(db)
    all_modules = query_service.get_all_modules()

    assert len(all_modules) == 2

    # 4. 依存関係検索確認
    main_module = next((m for m in result.modules if m['name'] == 'main'), None)
    assert main_module is not None

    dependencies = query_service.find_module_dependencies(main_module['id'])
    assert len(dependencies) == 1
    assert dependencies[0]['name'] == 'utils'

    # 5. 逆依存関係検索確認
    utils_module = next((m for m in result.modules if m['name'] == 'utils'), None)
    assert utils_module is not None

    dependents = query_service.find_module_dependents(utils_module['id'])
    assert len(dependents) == 1
    assert dependents[0]['name'] == 'main'

    db.close()


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
        db = GraphDatabase(str(db_path))
        db.initialize_schema()

        query = "MATCH (m:Module) RETURN m.name ORDER BY m.name"
        # optimized_query = db.optimize_query_plan(query)

        # # Check if a basic optimization (like adding LIMIT) is applied
        # assert "LIMIT" in optimized_query

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

    @pytest.mark.skip(reason="QueryCache not implemented in Phase 1.")
    def test_cache_functionality(self):
        """Tests the basic functionality of the query cache."""
        pass


@pytest.mark.skip(reason="End-to-end workflow requires full implementation.")
def test_end_to_end_workflow(temp_project):
    """A full end-to-end workflow test."""
    db_path = temp_project / "workflow_test.db"

    # 1. Analyze project in parallel
    analyzer = ParallelAnalyzer()
    result = analyzer.analyze_project_parallel(temp_project)

    # 2. Store results in an optimized database
    db = GraphDatabase(str(db_path))
    db.initialize_schema()
    if result.modules:
        db.bulk_insert_modules(result.modules)
    if result.functions:
        db.bulk_insert_functions(result.functions)

    # 3. Query data using a basic service
    query_service = BasicQueryService(db)
    search_result = query_service.find_module_by_name("main")
    assert search_result is not None

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
