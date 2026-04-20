import argparse
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from pydepgraph.cli import create_parser, cmd_analyze
from pydepgraph.config import Config
from pydepgraph.database import GraphDatabase


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
