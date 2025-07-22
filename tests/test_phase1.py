# tests/test_phase1.py

import pytest
import tempfile
import shutil
import json
import subprocess
from pathlib import Path

# Import classes for Phase 1 testing
from pydepgraph.database import GraphDatabase
from pydepgraph.services.query_service import BasicQueryService


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


def test_phase1_integration(temp_project, monkeypatch):
    """Phase1の統合テスト"""
    from pydepgraph.extractors.tach_extractor import TachExtractor

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