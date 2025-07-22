# tests/test_phase4.py

"""
Phase 4: CLI実装とユーザーインターフェースのテスト
このフェーズでは以下の機能をテストする必要がある：

確認事項：
1. CLI基本コマンド
   - analyze: プロジェクト分析の実行
   - query: 依存関係の検索
   - report: 分析結果のレポート生成
   - help: ヘルプ表示

2. 設定管理
   - pydepgraph.tomlの読み込み
   - デフォルト設定の適用
   - 設定値の検証とエラーハンドリング

3. エラー処理とユーザビリティ
   - 分かりやすいエラーメッセージ
   - プログレス表示
   - ログレベル制御

4. 出力フォーマット
   - JSON形式での結果出力
   - 表形式での結果表示
   - グラフ可視化用データ出力

5. インタラクティブモード
   - 対話的なクエリ実行
   - 履歴機能
   - 補完機能
"""

import pytest
import tempfile
import os
import json
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open
import argparse

from pydepgraph.config import Config, ExtractorConfig, DatabaseConfig, AnalysisConfig
from pydepgraph.core import PyDepGraphCore
from pydepgraph.cli import create_parser, format_output, format_table, cmd_analyze, cmd_query, cmd_analytics, main
from pydepgraph.exceptions import PyDepGraphError


class TestPhase4:
    """Phase 4機能のテスト"""
    
    def test_config_default_loading(self):
        """デフォルト設定の読み込みをテスト"""
        config = Config.get_default_config()
        
        assert config.extractors["tach"].enabled is True
        assert config.extractors["code2flow"].enabled is True
        assert config.database.path == "pydepgraph.db"
        assert config.analysis.include_tests is True
        assert len(config.analysis.exclude_patterns) > 0
    
    def test_config_file_loading(self):
        """設定ファイル読み込みをテスト"""
        config_content = '''
        [extractors]
        tach = { enabled = true }
        code2flow = { enabled = false }
        
        [database]
        path = "custom.db"
        enable_wal = false
        
        [analysis]
        include_tests = false
        max_file_size_mb = 20
        '''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write(config_content)
            config_path = Path(f.name)
        
        try:
            config = Config.load_from_file(config_path)
            
            assert config.extractors["tach"].enabled is True
            assert config.extractors["code2flow"].enabled is False
            assert config.database.path == "custom.db"
            assert config.database.enable_wal is False
            assert config.analysis.include_tests is False
            assert config.analysis.max_file_size_mb == 20
        finally:
            os.unlink(config_path)
    
    def test_config_validation(self):
        """設定値検証をテスト"""
        # Valid config
        config = Config.get_default_config()
        config.validate()  # Should not raise
        
        # Invalid database path
        config.database.path = ""
        with pytest.raises(PyDepGraphError, match="Database path cannot be empty"):
            config.validate()
        
        # Invalid max_file_size_mb
        config.database.path = "test.db"
        config.analysis.max_file_size_mb = -1
        with pytest.raises(PyDepGraphError, match="max_file_size_mb must be positive"):
            config.validate()
        
        # No enabled extractors
        config.analysis.max_file_size_mb = 10
        for extractor in config.extractors.values():
            extractor.enabled = False
        with pytest.raises(PyDepGraphError, match="At least one extractor must be enabled"):
            config.validate()
    
    def test_cli_parser_creation(self):
        """CLIパーサー作成をテスト"""
        parser = create_parser()
        
        # Test basic structure
        assert parser.prog == 'pydepgraph'
        
        # Test analyze command
        args = parser.parse_args(['analyze', '/path/to/project'])
        assert args.command == 'analyze'
        assert args.project_path == '/path/to/project'
        assert args.output == 'table'
        
        # Test query command
        args = parser.parse_args(['query', 'modules', '--format', 'json'])
        assert args.command == 'query'
        assert args.query_type == 'modules'
        assert args.format == 'json'
        
        # Test analytics command
        args = parser.parse_args(['analytics', 'stats', '--node-type', 'function'])
        assert args.command == 'analytics'
        assert args.analysis_type == 'stats'
        assert args.node_type == 'function'
        
        # Test report command
        args = parser.parse_args(['report', '--format', 'markdown'])
        assert args.command == 'report'
        assert args.format == 'markdown'
    
    def test_format_output_json(self):
        """JSON出力フォーマットをテスト"""
        data = {"test": "value", "number": 42}
        result = format_output(data, "json")
        
        parsed = json.loads(result)
        assert parsed["test"] == "value"
        assert parsed["number"] == 42
    
    def test_format_output_table(self):
        """テーブル出力フォーマットをテスト"""
        # Test graph statistics format
        stats_data = {
            "node_counts": {"total": 10, "modules": 5, "functions": 3, "classes": 2},
            "edge_counts": {"total": 8, "imports": 4, "function_calls": 2, "inheritance": 2},
            "graph_metrics": {"density": 0.15, "total_lines_of_code": 1000, "average_complexity": 3.5}
        }
        
        result = format_output(stats_data, "table")
        assert "Graph Statistics:" in result
        assert "Nodes: 10" in result
        assert "Modules: 5" in result
        assert "Functions: 3" in result
        assert "Classes: 2" in result
        assert "Density: 0.15" in result
        
        # Test list format (cycles/paths)
        cycles_data = [["moduleA", "moduleB", "moduleC"], ["classX", "classY"]]
        result = format_output(cycles_data, "table")
        assert "1. moduleA -> moduleB -> moduleC" in result
        assert "2. classX -> classY" in result
        
        # Test empty list
        empty_data = []
        result = format_output(empty_data, "table")
        assert result == "No results found"
    
    @patch('pydepgraph.cli.PyDepGraphCore')
    def test_cmd_analyze_success(self, mock_core_class):
        """analyzeコマンド成功ケースをテスト"""
        # Setup mocks
        mock_core = MagicMock()
        mock_core_class.return_value = mock_core
        
        mock_result = MagicMock()
        mock_result.modules = [MagicMock(), MagicMock()]
        mock_result.functions = [MagicMock()]
        mock_result.classes = []
        mock_result.module_imports = [MagicMock()]
        mock_result.function_calls = []
        mock_result.to_dict.return_value = {"test": "data"}
        
        mock_core.analyze_project.return_value = mock_result
        
        # Create args
        args = argparse.Namespace()
        args.project_path = "/test/path"
        args.output = "table"
        
        config = Config.get_default_config()
        
        # Test execution
        with patch('builtins.print') as mock_print:
            result = cmd_analyze(args, config)
            
            assert result == 0
            mock_core.analyze_project.assert_called_once_with("/test/path")
            
            # Check printed output
            print_calls = [call.args[0] for call in mock_print.call_args_list]
            assert any("Analysis completed successfully!" in call for call in print_calls)
            assert any("Modules found: 2" in call for call in print_calls)
    
    @patch('pydepgraph.cli.PyDepGraphCore')
    def test_cmd_analyze_json_output(self, mock_core_class):
        """analyzeコマンドのJSON出力をテスト"""
        mock_core = MagicMock()
        mock_core_class.return_value = mock_core
        
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {"modules": [], "functions": []}
        mock_core.analyze_project.return_value = mock_result
        
        args = argparse.Namespace()
        args.project_path = "/test/path"
        args.output = "json"
        
        config = Config.get_default_config()
        
        with patch('builtins.print') as mock_print:
            result = cmd_analyze(args, config)
            
            assert result == 0
            # Check JSON output was printed
            json_output = mock_print.call_args_list[1][0][0]  # Second print call
            parsed = json.loads(json_output)
            assert "modules" in parsed
    
    @patch('pydepgraph.cli.ExtendedQueryService')
    @patch('pydepgraph.cli.GraphDatabase')
    def test_cmd_query_modules(self, mock_db_class, mock_query_class):
        """queryコマンド（modules）をテスト"""
        # Setup mocks
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        
        mock_query = MagicMock()
        mock_query_class.return_value = mock_query
        
        mock_module = MagicMock()
        mock_module.to_dict.return_value = {"name": "test_module"}
        mock_query.get_all_modules.return_value = [mock_module]
        
        args = argparse.Namespace()
        args.query_type = "modules"
        args.filter = None
        args.format = "json"
        
        config = Config.get_default_config()
        
        with patch('builtins.print') as mock_print:
            result = cmd_query(args, config)
            
            assert result == 0
            mock_query.get_all_modules.assert_called_once()
    
    @patch('pydepgraph.cli.GraphAnalyticsService')
    @patch('pydepgraph.cli.GraphDatabase')
    def test_cmd_analytics_stats(self, mock_db_class, mock_analytics_class):
        """analyticsコマンド（stats）をテスト"""
        # Setup mocks
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        
        mock_analytics = MagicMock()
        mock_analytics_class.return_value = mock_analytics
        
        mock_stats = {
            "node_counts": {"total": 5, "modules": 3, "functions": 2, "classes": 0},
            "edge_counts": {"total": 3, "imports": 2, "function_calls": 1, "inheritance": 0},
            "graph_metrics": {"density": 0.2, "total_lines_of_code": 500, "average_complexity": 2.5}
        }
        mock_analytics.get_graph_statistics.return_value = mock_stats
        
        args = argparse.Namespace()
        args.analysis_type = "stats"
        args.node_type = "module"
        args.format = "table"
        
        config = Config.get_default_config()
        
        with patch('builtins.print') as mock_print:
            result = cmd_analytics(args, config)
            
            assert result == 0
            mock_analytics.get_graph_statistics.assert_called_once()
    
    @patch('pydepgraph.cli.GraphAnalyticsService')
    @patch('pydepgraph.cli.GraphDatabase')
    def test_cmd_analytics_depth_without_root(self, mock_db_class, mock_analytics_class):
        """analyticsコマンド（depth）でrootが未指定の場合をテスト"""
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        
        args = argparse.Namespace()
        args.analysis_type = "depth"
        args.node_type = "module"
        args.root = None
        args.format = "table"
        
        config = Config.get_default_config()
        
        with patch('builtins.print') as mock_print:
            result = cmd_analytics(args, config)
            
            assert result == 1  # Should fail
            error_output = mock_print.call_args_list[0][0][0]
            assert "--root is required for depth analysis" in error_output
    
    def test_error_handling(self):
        """エラーハンドリングをテスト"""
        # Test PyDepGraphError handling in analyze command
        args = argparse.Namespace()
        args.project_path = "/nonexistent/path"
        args.output = "table"
        
        config = Config.get_default_config()
        
        # Simple test: just verify that analyze returns error code for invalid path
        result = cmd_analyze(args, config)
        
        # The main thing is that it returns exit code 1 for invalid paths
        assert result == 1, "Should return error code 1 for nonexistent path"
    
    @patch('pydepgraph.cli.Config.load_from_file')
    def test_main_with_config_error(self, mock_config_load):
        """メイン関数での設定エラーハンドリングをテスト"""
        mock_config_load.side_effect = PyDepGraphError("Invalid config")
        
        with patch('sys.argv', ['pydepgraph', 'analyze']):
            with patch('builtins.print'):
                result = main()
                assert result == 1
    
    @patch('pydepgraph.cli.Config.load_from_file')
    def test_main_help_command(self, mock_config_load):
        """ヘルプコマンドをテスト"""
        with patch('sys.argv', ['pydepgraph']):
            with patch('builtins.print'):
                result = main()
                assert result == 1  # No command provided, should show help and exit
    
    def test_format_table_edge_cases(self):
        """format_table関数のエッジケースをテスト"""
        # Test generic dict
        generic_dict = {"key1": "value1", "key2": 42}
        result = format_table(generic_dict)
        assert "key1: value1" in result
        assert "key2: 42" in result
        
        # Test simple string
        result = format_table("simple string")
        assert result == "simple string"
        
        # Test simple list
        simple_list = ["item1", "item2", "item3"]
        result = format_table(simple_list)
        assert "item1" in result
        assert "item2" in result
        assert "item3" in result