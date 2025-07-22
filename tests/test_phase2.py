# tests/test_phase2.py

"""
Phase 2: Code2Flow統合とFunction/Classノード実装のテスト
このフェーズでは以下の機能をテストする必要がある：

確認事項：
1. Code2FlowExtractorの実装
   - 関数間の呼び出し関係を正しく抽出できるか
   - クラス内メソッドの依存関係を抽出できるか
   - 継承関係を検出できるか

2. GraphDatabaseスキーマ拡張
   - Functionノードテーブルが正しく作成されるか
   - Classノードテーブルが正しく作成されるか
   - FunctionCalls、Inheritance、Containsエッジテーブルが作成されるか

3. データ統合機能
   - TachExtractorとCode2FlowExtractorの結果を統合できるか
   - 重複データを適切に処理できるか
   - データの正規化が正しく行われるか

4. 拡張Query Service
   - 関数レベルの依存関係検索ができるか
   - クラス階層の検索ができるか
   - 複合条件でのクエリができるか
"""

import pytest
import tempfile
import shutil
from pathlib import Path

# Import Phase 2 components
from pydepgraph.extractors.code2flow_extractor import Code2FlowExtractor
from pydepgraph.extractors.tach_extractor import TachExtractor
from pydepgraph.database import GraphDatabase
from pydepgraph.services.query_service import ExtendedQueryService
from pydepgraph.data_integrator import DataIntegrator


@pytest.fixture
def temp_project_with_classes():
    """クラスと関数を含むテスト用プロジェクトを作成"""
    temp_dir = Path(tempfile.mkdtemp(prefix="pydepgraph_phase2_"))

    # メインファイル
    (temp_dir / "main.py").write_text(
        '"""Main entry point."""\n'
        "from utils import HelperClass\n\n"
        "def main():\n"
        "    helper = HelperClass()\n"
        "    helper.process_data()\n"
        "    return helper.get_result()\n\n"
        "if __name__ == '__main__':\n"
        "    main()\n"
    )

    # ユーティリティファイル
    (temp_dir / "utils.py").write_text(
        '"""Utility classes and functions."""\n\n'
        "class BaseHelper:\n"
        "    def __init__(self):\n"
        "        self.initialized = True\n\n"
        "    def setup(self):\n"
        "        pass\n\n\n"
        "class HelperClass(BaseHelper):\n"
        "    def __init__(self):\n"
        "        super().__init__()\n"
        "        self.data = []\n\n"
        "    def process_data(self):\n"
        "        self.setup()\n"
        "        return self._internal_process()\n\n"
        "    def _internal_process(self):\n"
        "        if self.initialized:\n"
        "            return True\n"
        "        return False\n\n"
        "    @staticmethod\n"
        "    def static_method():\n"
        "        return 'static'\n\n"
        "    def get_result(self):\n"
        "        return len(self.data)\n\n\n"
        "def utility_function():\n"
        "    return HelperClass.static_method()\n"
    )

    yield temp_dir
    shutil.rmtree(temp_dir)


class TestPhase2:
    """Phase 2機能のテスト"""
    
    def test_code2flow_extractor(self, temp_project_with_classes):
        """Code2FlowExtractorの基本動作をテスト"""
        extractor = Code2FlowExtractor()
        result = extractor.extract(str(temp_project_with_classes))
        
        # 関数が抽出されているかチェック
        assert len(result.functions) > 0
        assert len(result.classes) > 0
        assert result.metadata['extractor'] == 'code2flow_ast'
        
        # 特定の関数が存在するかチェック
        function_names = [f['name'] for f in result.functions]
        assert 'main' in function_names
        assert 'process_data' in function_names
        
        # 特定のクラスが存在するかチェック
        class_names = [c['name'] for c in result.classes]
        assert 'HelperClass' in class_names
        assert 'BaseHelper' in class_names
    
    def test_function_node_creation(self, temp_project_with_classes):
        """Functionノードの作成をテスト"""
        # データ抽出
        extractor = Code2FlowExtractor()
        result = extractor.extract(str(temp_project_with_classes))
        
        # データベース作成と挿入
        db_path = temp_project_with_classes / "test.db"
        db = GraphDatabase(str(db_path))
        db.initialize_schema()
        db.bulk_insert_functions(result.functions)
        
        # クエリでの確認
        query_service = ExtendedQueryService(db)
        all_functions = query_service.get_all_functions()
        
        assert len(all_functions) > 0
        function_names = [f['name'] for f in all_functions]
        assert 'main' in function_names
        
        db.close()
    
    def test_class_node_creation(self, temp_project_with_classes):
        """Classノードの作成をテスト"""
        # データ抽出
        extractor = Code2FlowExtractor()
        result = extractor.extract(str(temp_project_with_classes))
        
        # データベース作成と挿入
        db_path = temp_project_with_classes / "test.db"
        db = GraphDatabase(str(db_path))
        db.initialize_schema()
        db.bulk_insert_classes(result.classes)
        
        # クエリでの確認
        query_service = ExtendedQueryService(db)
        all_classes = query_service.get_all_classes()
        
        assert len(all_classes) > 0
        class_names = [c['name'] for c in all_classes]
        assert 'HelperClass' in class_names
        assert 'BaseHelper' in class_names
        
        db.close()
    
    def test_data_integration(self, temp_project_with_classes):
        """TachとCode2Flowの結果統合をテスト"""
        # モックデータでTach結果を作成
        from pydepgraph.extractors.base import ExtractionResult
        
        tach_result = ExtractionResult(
            modules=[
                {
                    'id': 'module_000001',
                    'name': 'main',
                    'file_path': 'main.py',
                    'package': '',
                    'lines_of_code': 10,
                    'complexity_score': 1.0,
                    'is_external': False,
                    'is_test': False,
                }
            ],
            functions=[],
            classes=[],
            relationships=[],
            metadata={'extractor': 'tach'}
        )
        
        # Code2Flow結果を取得
        extractor = Code2FlowExtractor()
        code2flow_result = extractor.extract(str(temp_project_with_classes))
        
        # データ統合
        integrator = DataIntegrator()
        integrated_result = integrator.integrate([tach_result, code2flow_result])
        
        # 統合結果の確認
        assert len(integrated_result.modules) == 1
        assert len(integrated_result.functions) > 0
        assert len(integrated_result.classes) > 0
        assert integrated_result.metadata['integrated'] == True
        assert 'extractors' in integrated_result.metadata
        assert 'tach' in integrated_result.metadata['extractors']
        assert 'code2flow_ast' in integrated_result.metadata['extractors']
    
    def test_extended_queries(self, temp_project_with_classes):
        """拡張クエリ機能をテスト"""
        # データ準備
        extractor = Code2FlowExtractor()
        result = extractor.extract(str(temp_project_with_classes))
        
        db_path = temp_project_with_classes / "test.db"
        db = GraphDatabase(str(db_path))
        db.initialize_schema()
        db.bulk_insert_functions(result.functions)
        db.bulk_insert_classes(result.classes)
        db.bulk_insert_contains(result.relationships)
        
        # 拡張クエリサービスのテスト
        query_service = ExtendedQueryService(db)
        
        # 関数検索テスト
        main_func = query_service.find_function_by_name('main')
        assert main_func is not None
        assert main_func['name'] == 'main'
        
        # クラス検索テスト
        helper_class = query_service.find_class_by_name('HelperClass')
        assert helper_class is not None
        assert helper_class['name'] == 'HelperClass'
        
        # クラスメソッド検索テスト
        if helper_class:
            methods = query_service.find_class_methods(helper_class['id'])
            method_names = [m['name'] for m in methods]
            # Contains関係が正しく作られていればメソッドが見つかる
            
        db.close()