import argparse
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from pydepgraph.cli import create_parser, cmd_analyze
from pydepgraph.config import Config
from pydepgraph.core import PyDepGraphCore
from pydepgraph.database import GraphDatabase
from pydepgraph.extractors.base import RawExtractionResult


def test_report_format_html_is_not_supported_anymore():
    parser = create_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(["report", "--format", "html"])


def test_cmd_analyze_respects_database_override(capsys):
    config = Config.get_default_config()
    args = argparse.Namespace(project_path=".", output="table", database="custom.db")

    with patch("pydepgraph.cli.PyDepGraphCore") as core_cls:
        core_instance = core_cls.return_value
        core_instance.analyze_project.return_value = SimpleNamespace(
            modules=[],
            functions=[],
            classes=[],
            module_imports=[],
            function_calls=[],
            to_dict=lambda: {},
        )

        rc = cmd_analyze(args, config)

    assert rc == 0
    assert config.database.path == "custom.db"
    core_cls.assert_called_once_with(config)
    captured = capsys.readouterr()
    assert "Using database: custom.db" in captured.out


def test_partial_config_uses_default_merge(tmp_path):
    config_file = tmp_path / "pydepgraph.toml"
    config_file.write_text('[database]\npath = "x.db"\n', encoding="utf-8")

    config = Config.load_from_file(config_file)

    assert config.database.path == "x.db"
    assert "tach" in config.extractors
    assert config.extractors["tach"].enabled is True


def test_initialize_non_destructive_and_reset_destructive():
    db = GraphDatabase.__new__(GraphDatabase)
    db._create_tables_if_needed = MagicMock()
    db._drop_existing_tables = MagicMock()

    db.initialize_schema()
    db._drop_existing_tables.assert_not_called()
    db._create_tables_if_needed.assert_called_once()

    db.reset_schema()
    db._drop_existing_tables.assert_called_once()
    assert db._create_tables_if_needed.call_count == 2


def test_analyze_project_deletes_project_scoped_data_before_store(monkeypatch, tmp_path):
    config = Config.get_default_config()
    config.extractors["tach"].enabled = False
    config.extractors["code2flow"].enabled = False
    config.extractors["dependency_file"].enabled = True

    call_order = []

    class DummyDatabase:
        def initialize_schema(self):
            pass

        def delete_project_data(self, project_root: str):
            call_order.append(("delete_project_data", project_root))

    core = PyDepGraphCore(config)
    core.database = DummyDatabase()

    def fake_initialize_database():
        return None

    def fake_extract(self):
        return RawExtractionResult(
            modules=[],
            functions=[],
            classes=[],
            relationships=[],
            metadata={"extractor": "dependency_file"},
        )

    def fake_store_results(_result):
        call_order.append(("store_results", None))

    monkeypatch.setattr(core, "_initialize_database", fake_initialize_database)
    monkeypatch.setattr(core, "_store_results", fake_store_results)
    monkeypatch.setattr("pydepgraph.core.DependencyFileExtractor.extract", fake_extract)
    monkeypatch.setattr("pydepgraph.core.infer_roles_for_modules", lambda modules: modules)
    monkeypatch.setattr("pydepgraph.core.DataNormalizer.normalize", lambda self, result: result)

    project_dir = tmp_path / "target_project"
    project_dir.mkdir()
    core.analyze_project(str(project_dir))

    assert call_order[0][0] == "delete_project_data"
    assert call_order[0][1] == str(project_dir.resolve())
    assert call_order[1][0] == "store_results"
