# tests/test_phase3.py

"""
Phase 3: 高度なクエリ機能とGraph Analytics Serviceのテスト
このフェーズでは以下の機能をテストする必要がある：

確認事項：
1. Graph Analytics Service
   - グラフ統計情報の取得（ノード数、エッジ数、密度等）
   - 循環依存の検出アルゴリズム
   - パス検索アルゴリズム（最短パス、全パス）
   - 依存関係の深度分析

2. 高度なクエリ機能
   - 複雑なグラフ検索クエリ
   - パフォーマンス最適化されたクエリ
   - 条件付き検索とフィルタリング

3. キャッシュ機能
   - クエリ結果のキャッシング
   - キャッシュの無効化とリフレッシュ
   - メモリ効率的なキャッシュ管理

4. パフォーマンステスト
   - 大規模グラフでの検索パフォーマンス
   - メモリ使用量の監視
   - クエリ応答時間の測定
"""

import pytest
import tempfile
import os
from unittest.mock import MagicMock

from pydepgraph.database import GraphDatabase
from pydepgraph.services.analytics_service import GraphAnalyticsService
from pydepgraph.models import Module, Function, Class, ModuleImport, FunctionCall, Inheritance


@pytest.fixture
def temp_db():
    """テスト用の一時データベース"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = f.name
    
    database = GraphDatabase(db_path)
    database.initialize_schema()
    yield database
    database.close()
    os.unlink(db_path)


@pytest.fixture
def sample_graph_data(temp_db):
    """サンプルグラフデータを挿入"""
    # Sample modules (as dictionaries for database insertion)
    modules = [
        {"id": 1, "name": "moduleA", "file_path": "/path/to/moduleA.py", "package": None, 
         "lines_of_code": 100, "complexity_score": 5.2, "is_external": False, "is_test": False},
        {"id": 2, "name": "moduleB", "file_path": "/path/to/moduleB.py", "package": None,
         "lines_of_code": 80, "complexity_score": 3.1, "is_external": False, "is_test": False},
        {"id": 3, "name": "moduleC", "file_path": "/path/to/moduleC.py", "package": None,
         "lines_of_code": 120, "complexity_score": 7.8, "is_external": False, "is_test": False},
        {"id": 4, "name": "moduleD", "file_path": "/path/to/moduleD.py", "package": None,
         "lines_of_code": 60, "complexity_score": 2.5, "is_external": False, "is_test": False}
    ]
    
    # Sample functions
    functions = [
        {"id": 1, "name": "funcA1", "qualified_name": "moduleA.funcA1", 
         "file_path": "/path/to/moduleA.py", "line_number": 5,
         "cyclomatic_complexity": 3, "parameter_count": 2, 
         "is_method": False, "is_static": False, "is_class_method": False},
        {"id": 2, "name": "funcA2", "qualified_name": "moduleA.funcA2",
         "file_path": "/path/to/moduleA.py", "line_number": 15,
         "cyclomatic_complexity": 2, "parameter_count": 1,
         "is_method": False, "is_static": False, "is_class_method": False},
        {"id": 3, "name": "funcB1", "qualified_name": "moduleB.funcB1",
         "file_path": "/path/to/moduleB.py", "line_number": 10,
         "cyclomatic_complexity": 4, "parameter_count": 3,
         "is_method": False, "is_static": False, "is_class_method": False},
        {"id": 4, "name": "funcC1", "qualified_name": "moduleC.funcC1",
         "file_path": "/path/to/moduleC.py", "line_number": 8,
         "cyclomatic_complexity": 5, "parameter_count": 2,
         "is_method": False, "is_static": False, "is_class_method": False}
    ]
    
    # Sample classes
    classes = [
        {"id": 1, "name": "ClassA", "qualified_name": "moduleA.ClassA",
         "file_path": "/path/to/moduleA.py", "line_number": 25,
         "method_count": 3, "inheritance_depth": 1, 
         "is_abstract": False},
        {"id": 2, "name": "ClassB", "qualified_name": "moduleB.ClassB",
         "file_path": "/path/to/moduleB.py", "line_number": 20,
         "method_count": 2, "inheritance_depth": 2,
         "is_abstract": False}
    ]
    
    # Sample relationships
    module_imports = [
        {"id": 1, "source_module_id": 1, "target_module_id": 2, "import_type": "standard", 
         "import_alias": None, "line_number": 1, "is_conditional": False},
        {"id": 2, "source_module_id": 2, "target_module_id": 3, "import_type": "standard",
         "import_alias": None, "line_number": 1, "is_conditional": False}, 
        {"id": 3, "source_module_id": 3, "target_module_id": 1, "import_type": "standard",  # Creates cycle
         "import_alias": None, "line_number": 1, "is_conditional": False}
    ]
    
    function_calls = [
        {"id": 1, "relationship_type": "FunctionCalls", "source_function_id": 1, "target_function_id": 3, "call_type": "direct", 
         "line_number": 5, "is_conditional": False},
        {"id": 2, "relationship_type": "FunctionCalls", "source_function_id": 3, "target_function_id": 4, "call_type": "direct", 
         "line_number": 8, "is_conditional": False}
    ]
    
    inheritance = [
        {"id": 1, "relationship_type": "Inheritance", "source_class_id": 2, "target_class_id": 1, "inheritance_type": "direct", "line_number": 20}
    ]
    
    # Insert data
    temp_db.bulk_insert_modules(modules)
    temp_db.bulk_insert_functions(functions)
    temp_db.bulk_insert_classes(classes)
    temp_db.bulk_insert_module_imports(module_imports)
    temp_db.bulk_insert_function_calls(function_calls)
    temp_db.bulk_insert_inheritance(inheritance)
    
    return temp_db


@pytest.fixture
def analytics_service(sample_graph_data):
    """GraphAnalyticsServiceのインスタンス"""
    return GraphAnalyticsService(sample_graph_data)


class TestPhase3:
    """Phase 3機能のテスト"""
    
    def test_graph_statistics(self, analytics_service):
        """グラフ統計情報の取得をテスト"""
        stats = analytics_service.get_graph_statistics()
        
        # 基本カウント
        assert stats["node_counts"]["modules"] == 4
        assert stats["node_counts"]["functions"] == 4
        assert stats["node_counts"]["classes"] == 2
        assert stats["node_counts"]["total"] == 10
        
        # エッジカウント
        assert stats["edge_counts"]["imports"] == 3
        assert stats["edge_counts"]["function_calls"] == 2
        assert stats["edge_counts"]["inheritance"] == 1
        assert stats["edge_counts"]["total"] == 6
        
        # グラフメトリクス
        assert "density" in stats["graph_metrics"]
        assert stats["graph_metrics"]["total_lines_of_code"] == 360  # 100+80+120+60
        assert stats["graph_metrics"]["average_complexity"] == 4.65  # (5.2+3.1+7.8+2.5)/4
    
    def test_circular_dependency_detection(self, analytics_service):
        """循環依存検出をテスト"""
        cycles = analytics_service.detect_circular_dependencies(node_type="module")
        
        # 循環依存が検出されることを確認
        assert len(cycles) == 1
        cycle = cycles[0]
        assert len(cycle) == 3
        assert set(cycle) == {"moduleA", "moduleB", "moduleC"}
    
    def test_path_search_shortest_path(self, analytics_service):
        """最短パス検索をテスト"""
        path = analytics_service.find_shortest_path("moduleA", "moduleC", node_type="module")
        
        assert path is not None
        assert len(path) >= 2
        assert path[0] == "moduleA"
        assert path[-1] == "moduleC"
    
    def test_path_search_no_path(self, analytics_service):
        """存在しないパスの検索をテスト"""
        path = analytics_service.find_shortest_path("moduleA", "nonexistent", node_type="module")
        assert path is None
    
    def test_all_paths_search(self, analytics_service):
        """全パス検索をテスト"""
        paths = analytics_service.find_all_paths("moduleA", "moduleC", node_type="module", max_length=5)
        
        assert len(paths) > 0
        for path in paths:
            assert path[0] == "moduleA"
            assert path[-1] == "moduleC"
            assert len(path) <= 5
    
    def test_importance_scores(self, analytics_service):
        """重要性スコア算出をテスト"""
        scores = analytics_service.calculate_importance_scores(node_type="module")
        
        assert len(scores) == 4
        assert all(isinstance(score, float) for score in scores.values())
        assert all(0 <= score <= 1 for score in scores.values())
        
        # 全スコアの合計は1に近い
        total_score = sum(scores.values())
        assert 0.9 <= total_score <= 1.1
    
    def test_dependency_depth_analysis(self, analytics_service):
        """依存関係の深度分析をテスト"""
        depth_analysis = analytics_service.analyze_dependency_depth("moduleA", node_type="module")
        
        assert "root_node" in depth_analysis
        assert depth_analysis["root_node"] == "moduleA"
        assert "max_depth" in depth_analysis
        assert "average_depth" in depth_analysis
        assert "depth_distribution" in depth_analysis
        assert "reachable_nodes" in depth_analysis
        
        assert isinstance(depth_analysis["max_depth"], int)
        assert isinstance(depth_analysis["average_depth"], float)
        assert isinstance(depth_analysis["reachable_nodes"], int)
    
    def test_dependency_depth_nonexistent_node(self, analytics_service):
        """存在しないノードでの深度分析をテスト"""
        depth_analysis = analytics_service.analyze_dependency_depth("nonexistent", node_type="module")
        
        assert "error" in depth_analysis
        assert "not found" in depth_analysis["error"].lower()
    
    def test_graph_cache_functionality(self, analytics_service):
        """グラフキャッシュ機能をテスト"""
        # 初回呼び出し
        stats1 = analytics_service.get_graph_statistics()
        
        # キャッシュされたグラフを使用した2回目の呼び出し
        stats2 = analytics_service.get_graph_statistics()
        
        # 結果が同じであることを確認
        assert stats1 == stats2
        
        # キャッシュを無効化
        analytics_service.invalidate_cache()
        
        # キャッシュ無効化後の呼び出し
        stats3 = analytics_service.get_graph_statistics()
        assert stats3 == stats1  # データは変わっていないので結果は同じ
    
    def test_function_level_analysis(self, analytics_service):
        """関数レベルでの分析をテスト"""
        # 関数の重要性スコア
        func_scores = analytics_service.calculate_importance_scores(node_type="function")
        assert len(func_scores) == 4
        
        # 関数の循環依存検出
        func_cycles = analytics_service.detect_circular_dependencies(node_type="function")
        assert isinstance(func_cycles, list)
    
    def test_class_level_analysis(self, analytics_service):
        """クラスレベルでの分析をテスト"""
        # クラスの重要性スコア
        class_scores = analytics_service.calculate_importance_scores(node_type="class")
        assert len(class_scores) == 2
        
        # クラスの循環依存検出
        class_cycles = analytics_service.detect_circular_dependencies(node_type="class")
        assert isinstance(class_cycles, list)
    
    def test_empty_graph_handling(self):
        """空のグラフでの処理をテスト"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
            db_path = f.name
        
        database = GraphDatabase(db_path)
        database.initialize_schema()
        
        analytics_service = GraphAnalyticsService(database)
        
        # 空のグラフでの統計情報
        stats = analytics_service.get_graph_statistics()
        assert stats["node_counts"]["total"] == 0
        assert stats["edge_counts"]["total"] == 0
        
        # 空のグラフでの循環依存検出
        cycles = analytics_service.detect_circular_dependencies()
        assert cycles == []
        
        # 空のグラフでの重要性スコア
        scores = analytics_service.calculate_importance_scores()
        assert scores == {}
        
        database.close()
        os.unlink(db_path)