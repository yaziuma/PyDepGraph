# tests/test_phase5.py

"""
Phase 5: 高度な機能とパフォーマンス最適化のテスト
このフェーズでは以下の機能をテストする必要がある：

確認事項：
1. 増分解析機能
   - ファイル変更検出とタイムスタンプ管理
   - 差分解析とグラフの部分更新
   - データベースの整合性保証

2. 並列処理
   - マルチプロセスでの分析実行
   - タスクの分散と結果のマージ
   - リソース管理とエラーハンドリング

3. 高度なレポート機能
   - HTMLレポートの生成
   - グラフ可視化
   - 統計情報とメトリクス

4. パフォーマンス最適化
   - インデックス作成と管理
   - クエリ最適化
   - メモリ使用量の最適化

5. 大規模プロジェクト対応
   - スケーラビリティテスト
   - メモリリークの検証
   - 長時間実行の安定性
"""

import pytest
import tempfile
import shutil
from pathlib import Path


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
        from pydepgraph.incremental import IncrementalAnalyzer
        from pydepgraph.database import GraphDatabase
        
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
        from pydepgraph.database import GraphDatabase
        
        db_path = temp_project / "test_opt.db"
        db = GraphDatabase(str(db_path))
        db.initialize_schema()

        # This would test query optimization if implemented

    @pytest.mark.skip(reason="Parallel processing logic not yet implemented.")
    def test_parallel_processing(self, temp_project):
        """Tests the parallel analysis execution."""
        from pydepgraph.parallel import ParallelAnalyzer
        
        parallel_analyzer = ParallelAnalyzer()
        result = parallel_analyzer.analyze_project_parallel(temp_project)

        assert result is not None
        assert result.metadata["extractor"] in ["tach", "code2flow"]

    @pytest.mark.skip(reason="Reporting logic not yet implemented.")
    def test_comprehensive_reporting(self, temp_project):
        """Tests the generation of comprehensive analysis reports."""
        from pydepgraph.database import GraphDatabase
        from pydepgraph.reporting import AdvancedReporter
        from pydepgraph.services.analytics_service import GraphAnalyticsService
        
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
    from pydepgraph.parallel import ParallelAnalyzer
    from pydepgraph.database import GraphDatabase
    from pydepgraph.services.query_service import BasicQueryService
    from pydepgraph.services.analytics_service import GraphAnalyticsService
    from pydepgraph.reporting import AdvancedReporter
    
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