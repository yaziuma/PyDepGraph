from unittest.mock import MagicMock

from pydepgraph.config import Config
from pydepgraph.core import PyDepGraphCore
from pydepgraph.models import Class, Contains, ExtractionResult, Function, Module


def _make_core_with_mock_db() -> tuple[PyDepGraphCore, MagicMock]:
    config = Config.get_default_config()
    core = PyDepGraphCore(config)
    db = MagicMock()
    core.database = db
    return core, db


def _base_result(contains):
    return ExtractionResult(
        modules=[
            Module(
                name="pkg.mod",
                file_path="/tmp/project/pkg/mod.py",
                package="pkg",
            )
        ],
        functions=[
            Function(
                name="method",
                qualified_name="pkg.mod.MyClass.method",
                file_path="/tmp/project/pkg/mod.py",
                is_method=True,
            )
        ],
        classes=[
            Class(
                name="MyClass",
                qualified_name="pkg.mod.MyClass",
                file_path="/tmp/project/pkg/mod.py",
            )
        ],
        module_imports=[],
        function_calls=[],
        inheritance=[],
        contains=contains,
        metadata={},
    )


def test_store_results_inserts_contains_relationship_when_resolvable():
    core, db = _make_core_with_mock_db()
    result = _base_result(
        [
            Contains(
                container="pkg.mod.MyClass",
                contained="pkg.mod.MyClass.method",
                contained_type="function",
            )
        ]
    )

    core._store_results(result)

    db.bulk_insert_contains.assert_called_once_with(
        [
            {
                "id": "1",
                "relationship_type": "Contains",
                "source_class_id": "1",
                "target_function_id": "1",
                "line_number": 0,
            }
        ]
    )


def test_store_results_skips_unresolved_or_non_function_contains():
    core, db = _make_core_with_mock_db()
    result = _base_result(
        [
            Contains(
                container="pkg.mod.MyClass",
                contained="pkg.mod.MyClass.missing_method",
                contained_type="function",
            ),
            Contains(
                container="pkg.mod.MyClass",
                contained="pkg.mod.OtherClass",
                contained_type="class",
            ),
        ]
    )

    core._store_results(result)

    db.bulk_insert_contains.assert_not_called()
