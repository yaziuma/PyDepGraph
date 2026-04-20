from pathlib import Path

from pydepgraph.config import Config
from pydepgraph.core import PyDepGraphCore
from pydepgraph.database import GraphDatabase
from pydepgraph.extractors.base import RawExtractionResult


EXPECTED_PROJECT_COUNTS = {
    "modules": 2,
    "functions": 2,
    "classes": 2,
    "module_imports": 1,
    "function_calls": 1,
    "inheritance": 1,
    "contains": 1,
}


def _build_raw_result(project_root: Path, project_name: str) -> RawExtractionResult:
    module_main = project_root / "main.py"
    module_utils = project_root / "utils.py"

    class_base = f"{project_name}.main.Base"
    class_child = f"{project_name}.main.Child"
    method_qualified = f"{project_name}.main.Child.method"
    helper_qualified = f"{project_name}.utils.helper"

    return RawExtractionResult(
        modules=[
            {
                "name": f"{project_name}.main",
                "file_path": str(module_main),
                "package": project_name,
                "is_external": False,
                "is_test": False,
                "extractor": "dependency_file",
            },
            {
                "name": f"{project_name}.utils",
                "file_path": str(module_utils),
                "package": project_name,
                "is_external": False,
                "is_test": False,
                "extractor": "dependency_file",
            },
        ],
        functions=[
            {
                "name": "method",
                "qualified_name": method_qualified,
                "file_path": str(module_main),
                "line_number": 3,
                "is_method": True,
                "is_static": False,
                "is_class_method": False,
                "extractor": "dependency_file",
            },
            {
                "name": "helper",
                "qualified_name": helper_qualified,
                "file_path": str(module_utils),
                "line_number": 1,
                "is_method": False,
                "is_static": False,
                "is_class_method": False,
                "extractor": "dependency_file",
            },
        ],
        classes=[
            {
                "name": "Base",
                "qualified_name": class_base,
                "file_path": str(module_main),
                "line_number": 1,
                "method_count": 0,
                "inheritance_depth": 1,
                "is_abstract": False,
                "extractor": "dependency_file",
            },
            {
                "name": "Child",
                "qualified_name": class_child,
                "file_path": str(module_main),
                "line_number": 2,
                "method_count": 1,
                "inheritance_depth": 2,
                "is_abstract": False,
                "extractor": "dependency_file",
            },
        ],
        relationships=[
            {
                "relationship_type": "ModuleImports",
                "source_module": str(module_main),
                "target_module": str(module_utils),
                "import_type": "standard",
                "line_number": 1,
                "is_conditional": False,
                "extractor": "dependency_file",
            },
            {
                "relationship_type": "FunctionCalls",
                "source_function": method_qualified,
                "target_function": helper_qualified,
                "call_type": "direct",
                "line_number": 4,
                "is_conditional": False,
                "extractor": "dependency_file",
            },
            {
                "relationship_type": "Inheritance",
                "child_class": class_child,
                "parent_class": class_base,
                "inheritance_type": "direct",
                "line_number": 2,
                "extractor": "dependency_file",
            },
            {
                "relationship_type": "Contains",
                "source_class": class_child,
                "target_function": method_qualified,
                "contained_type": "function",
                "extractor": "dependency_file",
            },
        ],
        metadata={"extractor": "dependency_file", "project": project_name},
    )


def _count(db: GraphDatabase, query: str, params=None) -> int:
    rows = db.execute_query(query, params)
    return int(rows[0]["cnt"])


def _project_counts(db: GraphDatabase, project_root: Path) -> dict[str, int]:
    project_prefix = str(project_root.resolve())
    params = {"p": project_prefix}

    return {
        "modules": _count(
            db,
            "MATCH (m:Module) WHERE m.file_path STARTS WITH $p RETURN count(m) AS cnt",
            params,
        ),
        "functions": _count(
            db,
            "MATCH (f:Function) WHERE f.file_path STARTS WITH $p RETURN count(f) AS cnt",
            params,
        ),
        "classes": _count(
            db,
            "MATCH (c:Class) WHERE c.file_path STARTS WITH $p RETURN count(c) AS cnt",
            params,
        ),
        "module_imports": _count(
            db,
            """
            MATCH (s:Module)-[r:ModuleImports]->(t:Module)
            WHERE s.file_path STARTS WITH $p AND t.file_path STARTS WITH $p
            RETURN count(r) AS cnt
            """,
            params,
        ),
        "function_calls": _count(
            db,
            """
            MATCH (s:Function)-[r:FunctionCalls]->(t:Function)
            WHERE s.file_path STARTS WITH $p AND t.file_path STARTS WITH $p
            RETURN count(r) AS cnt
            """,
            params,
        ),
        "inheritance": _count(
            db,
            """
            MATCH (s:Class)-[r:Inheritance]->(t:Class)
            WHERE s.file_path STARTS WITH $p AND t.file_path STARTS WITH $p
            RETURN count(r) AS cnt
            """,
            params,
        ),
        "contains": _count(
            db,
            """
            MATCH (s:Class)-[r:Contains]->(t:Function)
            WHERE s.file_path STARTS WITH $p AND t.file_path STARTS WITH $p
            RETURN count(r) AS cnt
            """,
            params,
        ),
    }


def _build_core(db_path: Path) -> PyDepGraphCore:
    config = Config.get_default_config()
    config.database.path = str(db_path)
    config.extractors["tach"].enabled = False
    config.extractors["code2flow"].enabled = False
    config.extractors["dependency_file"].enabled = True
    return PyDepGraphCore(config)


def _seed_project_data(db: GraphDatabase, project_root: Path, project_name: str, id_prefix: str) -> None:
    main_path = str((project_root / "main.py").resolve())
    utils_path = str((project_root / "utils.py").resolve())

    db.bulk_insert_modules(
        [
            {
                "id": f"{id_prefix}_m1",
                "name": f"{project_name}.main",
                "file_path": main_path,
                "package": project_name,
                "lines_of_code": 10,
                "complexity_score": 1.0,
                "is_external": False,
                "is_test": False,
                "role": "",
            },
            {
                "id": f"{id_prefix}_m2",
                "name": f"{project_name}.utils",
                "file_path": utils_path,
                "package": project_name,
                "lines_of_code": 5,
                "complexity_score": 1.0,
                "is_external": False,
                "is_test": False,
                "role": "",
            },
        ]
    )
    db.bulk_insert_functions(
        [
            {
                "id": f"{id_prefix}_f1",
                "name": "method",
                "qualified_name": f"{project_name}.main.Child.method",
                "file_path": main_path,
                "line_number": 3,
                "cyclomatic_complexity": 1,
                "parameter_count": 1,
                "is_method": True,
                "is_static": False,
                "is_class_method": False,
                "class_id": "",
            },
            {
                "id": f"{id_prefix}_f2",
                "name": "helper",
                "qualified_name": f"{project_name}.utils.helper",
                "file_path": utils_path,
                "line_number": 1,
                "cyclomatic_complexity": 1,
                "parameter_count": 0,
                "is_method": False,
                "is_static": False,
                "is_class_method": False,
                "class_id": "",
            },
        ]
    )
    db.bulk_insert_classes(
        [
            {
                "id": f"{id_prefix}_c1",
                "name": "Base",
                "qualified_name": f"{project_name}.main.Base",
                "file_path": main_path,
                "line_number": 1,
                "method_count": 0,
                "inheritance_depth": 1,
                "is_abstract": False,
            },
            {
                "id": f"{id_prefix}_c2",
                "name": "Child",
                "qualified_name": f"{project_name}.main.Child",
                "file_path": main_path,
                "line_number": 2,
                "method_count": 1,
                "inheritance_depth": 2,
                "is_abstract": False,
            },
        ]
    )
    db.bulk_insert_module_imports(
        [
            {
                "source_module_id": f"{id_prefix}_m1",
                "target_module_id": f"{id_prefix}_m2",
                "import_type": "standard",
                "import_alias": "",
                "line_number": 1,
                "is_conditional": False,
            }
        ]
    )
    db.bulk_insert_function_calls(
        [
            {
                "relationship_type": "FunctionCalls",
                "source_function_id": f"{id_prefix}_f1",
                "target_function_id": f"{id_prefix}_f2",
                "call_type": "direct",
                "line_number": 4,
            }
        ]
    )
    db.bulk_insert_inheritance(
        [
            {
                "relationship_type": "Inheritance",
                "source_class_id": f"{id_prefix}_c2",
                "target_class_id": f"{id_prefix}_c1",
                "line_number": 2,
            }
        ]
    )
    db.bulk_insert_contains(
        [
            {
                "relationship_type": "Contains",
                "source_class_id": f"{id_prefix}_c2",
                "target_function_id": f"{id_prefix}_f1",
                "line_number": 3,
            }
        ]
    )


def test_analyze_same_project_twice_does_not_duplicate_graph_data(monkeypatch, tmp_path: Path):
    db_path = tmp_path / "graph.db"
    project_a = tmp_path / "project_a"
    project_a.mkdir()
    (project_a / "main.py").write_text("class Base: ...\nclass Child(Base):\n    def method(self):\n        return helper()\n", encoding="utf-8")
    (project_a / "utils.py").write_text("def helper():\n    return 1\n", encoding="utf-8")

    project_results = {str(project_a.resolve()): _build_raw_result(project_a, "project_a")}

    def fake_extract(self):
        return project_results[str(self.project_path.resolve())]

    monkeypatch.setattr("pydepgraph.core.DependencyFileExtractor.extract", fake_extract)
    monkeypatch.setattr("pydepgraph.core.DataNormalizer.normalize", lambda self, result: result)
    monkeypatch.setattr("pydepgraph.core.infer_roles_for_modules", lambda modules: modules)

    core = _build_core(db_path)

    core.analyze_project(str(project_a))
    first_counts = _project_counts(core.database, project_a)

    assert first_counts == EXPECTED_PROJECT_COUNTS

    core.analyze_project(str(project_a))
    second_counts = _project_counts(core.database, project_a)

    assert second_counts == first_counts


def test_reanalyzing_project_preserves_unrelated_project_data(monkeypatch, tmp_path: Path):
    db_path = tmp_path / "graph.db"
    project_a = tmp_path / "project_a"
    project_b = tmp_path / "project_b"
    project_a.mkdir()
    project_b.mkdir()

    (project_a / "main.py").write_text("class Base: ...\nclass Child(Base):\n    def method(self):\n        return helper()\n", encoding="utf-8")
    (project_a / "utils.py").write_text("def helper():\n    return 1\n", encoding="utf-8")
    (project_b / "main.py").write_text("class Base: ...\nclass Child(Base):\n    def method(self):\n        return helper()\n", encoding="utf-8")
    (project_b / "utils.py").write_text("def helper():\n    return 2\n", encoding="utf-8")

    project_results = {str(project_a.resolve()): _build_raw_result(project_a, "project_a")}

    def fake_extract(self):
        return project_results[str(self.project_path.resolve())]

    monkeypatch.setattr("pydepgraph.core.DependencyFileExtractor.extract", fake_extract)
    monkeypatch.setattr("pydepgraph.core.DataNormalizer.normalize", lambda self, result: result)
    monkeypatch.setattr("pydepgraph.core.infer_roles_for_modules", lambda modules: modules)

    core = _build_core(db_path)

    core.analyze_project(str(project_a))
    _seed_project_data(core.database, project_b, project_name="project_b", id_prefix="project_b")

    counts_a_before = _project_counts(core.database, project_a)
    counts_b_before = _project_counts(core.database, project_b)

    assert counts_a_before == EXPECTED_PROJECT_COUNTS
    assert counts_b_before == EXPECTED_PROJECT_COUNTS

    core.analyze_project(str(project_a))

    counts_a_after = _project_counts(core.database, project_a)
    counts_b_after = _project_counts(core.database, project_b)

    assert counts_a_after == counts_a_before
    assert counts_b_after == counts_b_before
