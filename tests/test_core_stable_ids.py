from unittest.mock import MagicMock

from pydepgraph.config import Config
from pydepgraph.core import PyDepGraphCore
from pydepgraph.models import (
    Class,
    Contains,
    ExtractionResult,
    Function,
    FunctionCall,
    Inheritance,
    Module,
    ModuleImport,
)


def _make_core_with_mock_db() -> tuple[PyDepGraphCore, MagicMock]:
    config = Config.get_default_config()
    core = PyDepGraphCore(config)
    db = MagicMock()
    core.database = db
    return core, db


def _result_a() -> ExtractionResult:
    return ExtractionResult(
        modules=[
            Module(name="pkg.a", file_path="/tmp/project/pkg/a.py", package="pkg"),
            Module(name="pkg.b", file_path="/tmp/project/pkg/b.py", package="pkg"),
        ],
        functions=[
            Function(name="foo", qualified_name="pkg.a.foo", file_path="/tmp/project/pkg/a.py"),
            Function(name="bar", qualified_name="pkg.b.bar", file_path="/tmp/project/pkg/b.py"),
        ],
        classes=[
            Class(name="A", qualified_name="pkg.a.A", file_path="/tmp/project/pkg/a.py"),
            Class(name="B", qualified_name="pkg.b.B", file_path="/tmp/project/pkg/b.py"),
        ],
        module_imports=[],
        function_calls=[],
        inheritance=[],
        contains=[],
        metadata={},
    )


def _result_b_reordered() -> ExtractionResult:
    return ExtractionResult(
        modules=[
            Module(name="pkg.b", file_path="/tmp/project/pkg/b.py", package="pkg"),
            Module(name="pkg.a", file_path="/tmp/project/pkg/a.py", package="pkg"),
        ],
        functions=[
            Function(name="bar", qualified_name="pkg.b.bar", file_path="/tmp/project/pkg/b.py"),
            Function(name="foo", qualified_name="pkg.a.foo", file_path="/tmp/project/pkg/a.py"),
        ],
        classes=[
            Class(name="B", qualified_name="pkg.b.B", file_path="/tmp/project/pkg/b.py"),
            Class(name="A", qualified_name="pkg.a.A", file_path="/tmp/project/pkg/a.py"),
        ],
        module_imports=[],
        function_calls=[],
        inheritance=[],
        contains=[],
        metadata={},
    )


def _id_map(records, key_field):
    return {item[key_field]: item["id"] for item in records}


def test_store_results_uses_stable_ids_for_same_entities():
    core_1, db_1 = _make_core_with_mock_db()
    core_2, db_2 = _make_core_with_mock_db()

    core_1._store_results(_result_a())
    core_2._store_results(_result_b_reordered())

    modules_1 = db_1.bulk_insert_modules.call_args.args[0]
    modules_2 = db_2.bulk_insert_modules.call_args.args[0]
    assert _id_map(modules_1, "file_path") == _id_map(modules_2, "file_path")
    assert all(item["id"].startswith("module:") for item in modules_1)

    functions_1 = db_1.bulk_insert_functions.call_args.args[0]
    functions_2 = db_2.bulk_insert_functions.call_args.args[0]
    assert _id_map(functions_1, "qualified_name") == _id_map(functions_2, "qualified_name")
    assert all(item["id"].startswith("function:") for item in functions_1)

    classes_1 = db_1.bulk_insert_classes.call_args.args[0]
    classes_2 = db_2.bulk_insert_classes.call_args.args[0]
    assert _id_map(classes_1, "qualified_name") == _id_map(classes_2, "qualified_name")
    assert all(item["id"].startswith("class:") for item in classes_1)


def test_store_results_relationship_resolution_still_works_with_stable_ids():
    core, db = _make_core_with_mock_db()
    result = ExtractionResult(
        modules=[
            Module(name="pkg.a", file_path="/tmp/project/pkg/a.py", package="pkg"),
            Module(name="pkg.b", file_path="/tmp/project/pkg/b.py", package="pkg"),
        ],
        functions=[
            Function(name="foo", qualified_name="pkg.a.foo", file_path="/tmp/project/pkg/a.py"),
            Function(name="bar", qualified_name="pkg.b.bar", file_path="/tmp/project/pkg/b.py"),
        ],
        classes=[
            Class(name="A", qualified_name="pkg.a.A", file_path="/tmp/project/pkg/a.py"),
            Class(name="B", qualified_name="pkg.b.B", file_path="/tmp/project/pkg/b.py"),
        ],
        module_imports=[
            ModuleImport(source_module="/tmp/project/pkg/a.py", target_module="/tmp/project/pkg/b.py"),
        ],
        function_calls=[
            FunctionCall(source_function="pkg.a.foo", target_function="pkg.b.bar"),
        ],
        inheritance=[
            Inheritance(child_class="pkg.b.B", parent_class="pkg.a.A"),
        ],
        contains=[
            Contains(container="pkg.b.B", contained="pkg.b.bar", contained_type="function"),
        ],
        metadata={},
    )

    core._store_results(result)

    modules = db.bulk_insert_modules.call_args.args[0]
    functions = db.bulk_insert_functions.call_args.args[0]
    classes = db.bulk_insert_classes.call_args.args[0]
    module_ids = _id_map(modules, "file_path")
    function_ids = _id_map(functions, "qualified_name")
    class_ids = _id_map(classes, "qualified_name")

    module_imports = db.bulk_insert_module_imports.call_args.args[0]
    assert module_imports[0]["source_module_id"] == module_ids["/tmp/project/pkg/a.py"]
    assert module_imports[0]["target_module_id"] == module_ids["/tmp/project/pkg/b.py"]

    function_calls = db.bulk_insert_function_calls.call_args.args[0]
    assert function_calls[0]["source_function_id"] == function_ids["pkg.a.foo"]
    assert function_calls[0]["target_function_id"] == function_ids["pkg.b.bar"]

    inheritance = db.bulk_insert_inheritance.call_args.args[0]
    assert inheritance[0]["source_class_id"] == class_ids["pkg.b.B"]
    assert inheritance[0]["target_class_id"] == class_ids["pkg.a.A"]

    contains = db.bulk_insert_contains.call_args.args[0]
    assert contains[0]["source_class_id"] == class_ids["pkg.b.B"]
    assert contains[0]["target_function_id"] == function_ids["pkg.b.bar"]
