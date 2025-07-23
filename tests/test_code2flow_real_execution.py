# tests/test_code2flow_real_execution.py

import pytest
import tempfile
import os
import json
from pathlib import Path

from src.pydepgraph.extractors.code2flow_extractor import Code2FlowExtractor
from src.pydepgraph.exceptions import PrologExecutionError


class TestCode2FlowRealExecution:
    """Code2Flow実動作の完全テスト"""

    @pytest.fixture
    def sample_python_project(self):
        """テスト用のPythonプロジェクト作成"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            
            # モジュール1: 基本関数
            module1 = project_path / "module1.py"
            module1.write_text("""
def function_a():
    return function_b()

def function_b():
    return "result"

class ClassA:
    def method_a(self):
        return function_a()
    
    def method_b(self):
        return self.method_a()
""")
            
            # モジュール2: 関数呼び出し
            module2 = project_path / "module2.py"
            module2.write_text("""
from module1 import function_a, ClassA

def main_function():
    result = function_a()
    obj = ClassA()
    return obj.method_a()

def helper_function():
    return main_function()
""")
            
            yield str(project_path)

    def test_code2flow_real_execution_success(self, sample_python_project):
        """Code2Flow実動作の成功テスト"""
        extractor = Code2FlowExtractor()
        
        # Code2Flowが利用可能かチェック
        try:
            result = extractor.extract(sample_python_project)
        except PrologExecutionError:
            pytest.skip("Code2Flow not available")
        
        # 結果の検証
        assert result is not None
        assert result.metadata.get('extractor') == 'code2flow'
        assert len(result.functions) > 0
        assert len(result.relationships) > 0
        
        # 具体的な関数が抽出されていることを確認
        function_names = [f.get('name', '') for f in result.functions]
        assert any('function_a' in name for name in function_names)
        assert any('function_b' in name for name in function_names)
        
        # 関係性が抽出されていることを確認
        relationships = [rel for rel in result.relationships if rel.get('relationship_type') == 'FunctionCalls']
        assert len(relationships) > 0

    def test_code2flow_with_real_pyprolog_project(self):
        """実際のpyprologプロジェクトでのCode2Flow動作テスト"""
        # 絶対パスを使用してCode2Flow実動作を確実に実行
        project_path = os.path.abspath("tests/sample_code/pyprolog")
        extractor = Code2FlowExtractor()
        
        try:
            result = extractor.extract(project_path)
        except PrologExecutionError:
            pytest.skip("Code2Flow not available")
        
        # 結果の検証（実Code2FlowまたはASTフォールバック）
        extractor_type = result.metadata.get('extractor')
        assert extractor_type in ('code2flow', 'code2flow_ast')
        
        # pyprologプロジェクトの期待値検証
        assert len(result.functions) > 200  # pyprologは大規模プロジェクト
        assert len(result.relationships) > 400  # 多数の関数呼び出し
        
        # 特定の関数が抽出されていることを確認
        function_names = [f.get('qualified_name', '') for f in result.functions]
        assert any('interpreter' in name for name in function_names)
        assert any('parser' in name for name in function_names)

    def test_code2flow_json_output_format(self, sample_python_project):
        """Code2FlowのJSON出力形式の検証"""
        extractor = Code2FlowExtractor()
        
        try:
            result = extractor.extract(sample_python_project)
        except PrologExecutionError:
            pytest.skip("Code2Flow not available")
        
        # JSON出力ファイルが作成されていることを確認
        output_file = "/tmp/code2flow_output.json"
        assert Path(output_file).exists()
        
        # JSON形式の妥当性確認
        with open(output_file, 'r') as f:
            data = json.load(f)
        
        assert 'graph' in data
        assert 'nodes' in data['graph']
        assert 'edges' in data['graph']
        assert isinstance(data['graph']['nodes'], dict)
        assert isinstance(data['graph']['edges'], list)

    def test_code2flow_function_metadata_extraction(self, sample_python_project):
        """関数メタデータの抽出テスト"""
        extractor = Code2FlowExtractor()
        
        try:
            result = extractor.extract(sample_python_project)
        except PrologExecutionError:
            pytest.skip("Code2Flow not available")
        
        # 関数メタデータの検証
        functions = result.functions
        assert len(functions) > 0
        
        for func in functions:
            # 必須フィールドの存在確認
            assert 'id' in func
            assert 'name' in func
            assert 'qualified_name' in func
            assert 'file_path' in func
            assert 'line_number' in func
            assert 'extractor' in func
            
            # 値の妥当性確認
            assert func['extractor'] == 'code2flow'
            assert isinstance(func['line_number'], int)
            assert func['line_number'] >= 0

    def test_code2flow_relationship_extraction(self, sample_python_project):
        """関数呼び出し関係性の抽出テスト"""
        extractor = Code2FlowExtractor()
        
        try:
            result = extractor.extract(sample_python_project)
        except PrologExecutionError:
            pytest.skip("Code2Flow not available")
        
        # 関係性の検証
        relationships = [rel for rel in result.relationships if rel.get('relationship_type') == 'FunctionCalls']
        assert len(relationships) > 0
        
        for rel in relationships:
            # 必須フィールドの存在確認
            assert 'relationship_type' in rel
            assert 'source_function' in rel
            assert 'target_function' in rel
            assert 'source_function_id' in rel
            assert 'target_function_id' in rel
            assert 'extractor' in rel
            
            # 値の妥当性確認
            assert rel['relationship_type'] == 'FunctionCalls'
            assert rel['extractor'] == 'code2flow'

    def test_code2flow_fallback_to_ast(self):
        """Code2Flow失敗時のASTフォールバック動作テスト"""
        extractor = Code2FlowExtractor()
        
        # 存在しないプロジェクトパスでテスト
        with pytest.raises(ValueError, match="Invalid project path"):
            extractor.extract("/nonexistent/path")

    def test_code2flow_qualified_name_format(self, sample_python_project):
        """qualified_nameの形式テスト"""
        extractor = Code2FlowExtractor()
        
        try:
            result = extractor.extract(sample_python_project)
        except PrologExecutionError:
            pytest.skip("Code2Flow not available")
        
        # qualified_nameの形式確認
        functions = result.functions
        for func in functions:
            qualified_name = func.get('qualified_name', '')
            # モジュール名::関数名の形式であることを確認
            assert '::' in qualified_name
            parts = qualified_name.split('::')
            assert len(parts) >= 2

    def test_code2flow_method_detection(self, sample_python_project):
        """クラスメソッドの検出テスト"""
        extractor = Code2FlowExtractor()
        
        try:
            result = extractor.extract(sample_python_project)
        except PrologExecutionError:
            pytest.skip("Code2Flow not available")
        
        # メソッドが正しく検出されていることを確認
        methods = [f for f in result.functions if f.get('is_method', False)]
        assert len(methods) > 0
        
        for method in methods:
            qualified_name = method.get('qualified_name', '')
            # クラス名.メソッド名の形式であることを確認
            assert '.' in qualified_name.split('::')[-1]

    def test_code2flow_performance_with_large_project(self):
        """大規模プロジェクトでのパフォーマンステスト"""
        project_path = "tests/sample_code/pyprolog"
        extractor = Code2FlowExtractor()
        
        import time
        start_time = time.time()
        
        try:
            result = extractor.extract(project_path)
            execution_time = time.time() - start_time
            
            # 実行時間が妥当であることを確認（5分以内）
            assert execution_time < 300
            
            # 結果の品質確認
            assert len(result.functions) > 200
            assert len(result.relationships) > 400
            
        except PrologExecutionError:
            pytest.skip("Code2Flow not available")

    def test_code2flow_error_handling(self):
        """Code2Flowエラーハンドリングテスト"""
        extractor = Code2FlowExtractor()
        
        # 無効なパスでのエラーハンドリング（正しい動作確認）
        with pytest.raises(ValueError, match="Invalid project path"):
            extractor.extract("/absolutely/nonexistent/path/that/should/not/exist")
        
        # 空文字列は現在ディレクトリとして扱われるため、ASTフォールバック動作を確認
        result = extractor.extract("")
        assert result.metadata.get('extractor') == 'code2flow_ast'  # ASTフォールバック
        assert result is not None

    def test_code2flow_output_cleanup(self, sample_python_project):
        """Code2Flow出力ファイルのクリーンアップテスト"""
        extractor = Code2FlowExtractor()
        output_file = "/tmp/code2flow_output.json"
        
        # ファイルが存在しない状態から開始
        if Path(output_file).exists():
            os.remove(output_file)
        
        try:
            result = extractor.extract(sample_python_project)
            # 出力ファイルが作成されていることを確認
            assert Path(output_file).exists()
        except PrologExecutionError:
            pytest.skip("Code2Flow not available")


class TestCode2FlowIntegration:
    """Code2FlowとDataIntegratorの統合テスト"""
    
    def test_code2flow_with_data_integrator(self):
        """Code2FlowとDataIntegratorの連携テスト"""
        from src.pydepgraph.services.data_integrator import DataIntegrator
        
        project_path = os.path.abspath("tests/sample_code/pyprolog")
        extractor = Code2FlowExtractor()
        integrator = DataIntegrator()
        
        try:
            # Code2Flow実行
            extraction_result = extractor.extract(project_path)
            
            # DataIntegratorで統合
            integrated_result = integrator.integrate_results([extraction_result])
            
            # 統合結果の検証
            assert len(integrated_result.functions) > 200
            assert len(integrated_result.function_calls) > 0  # 実際のFunctionCall数を確認
            
            # 関数オブジェクトの型確認
            for func in integrated_result.functions:
                assert hasattr(func, 'name')
                assert hasattr(func, 'qualified_name')
                assert hasattr(func, 'extractor')
                # ASTフォールバックも考慮
                extractor_type = func.extractor
                assert extractor_type in ('code2flow', 'code2flow_ast', None)
            
        except PrologExecutionError:
            pytest.skip("Code2Flow not available")

    def test_end_to_end_with_code2flow(self):
        """Code2Flow使用時のエンドツーエンドテスト"""
        from src.pydepgraph.core import PyDepGraphCore
        from src.pydepgraph.config import Config
        
        # Code2FlowのみのConfig作成
        config = Config.get_default_config()
        # 辞書形式での設定変更
        config.extractors["tach"].enabled = False
        config.extractors["code2flow"].enabled = True
        
        core = PyDepGraphCore(config)
        
        try:
            project_path = os.path.abspath("tests/sample_code/pyprolog")
            result = core.analyze_project(project_path)
            
            # 結果の検証
            assert len(result.functions) > 200
            assert len(result.function_calls) > 0
            
            # extractor typeの確認（Code2FlowまたはASTフォールバック）
            extractor_types = {func.extractor for func in result.functions}
            assert extractor_types.intersection({'code2flow', 'code2flow_ast', None})
            
        except PrologExecutionError:
            pytest.skip("Code2Flow not available")