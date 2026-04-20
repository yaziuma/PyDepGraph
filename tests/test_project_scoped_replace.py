from pathlib import Path

from pydepgraph.database import GraphDatabase


def test_delete_project_data_is_project_scoped_and_preserves_other_projects(tmp_path: Path):
    db_path = tmp_path / "graph.db"
    project_a = tmp_path / "project_a"
    project_b = tmp_path / "project_b"
    project_a.mkdir()
    project_b.mkdir()

    db = GraphDatabase(str(db_path))
    db.initialize_schema()

    # Node seed
    db.bulk_insert_modules(
        [
            {
                "id": "m_a",
                "name": "module_a",
                "file_path": str(project_a / "a.py"),
                "package": "a",
                "lines_of_code": 10,
                "complexity_score": 1.0,
                "is_external": False,
                "is_test": False,
                "role": "",
            },
            {
                "id": "m_b",
                "name": "module_b",
                "file_path": str(project_b / "b.py"),
                "package": "b",
                "lines_of_code": 11,
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
                "id": "f_a",
                "name": "fa",
                "qualified_name": "project_a.fa",
                "file_path": str(project_a / "a.py"),
                "line_number": 1,
                "cyclomatic_complexity": 1,
                "parameter_count": 0,
                "is_method": False,
                "is_static": False,
                "is_class_method": False,
                "class_id": "",
            },
            {
                "id": "f_b",
                "name": "fb",
                "qualified_name": "project_b.fb",
                "file_path": str(project_b / "b.py"),
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
                "id": "c_a",
                "name": "CA",
                "qualified_name": "project_a.CA",
                "file_path": str(project_a / "a.py"),
                "line_number": 1,
                "method_count": 1,
                "inheritance_depth": 1,
                "is_abstract": False,
            },
            {
                "id": "c_b",
                "name": "CB",
                "qualified_name": "project_b.CB",
                "file_path": str(project_b / "b.py"),
                "line_number": 1,
                "method_count": 1,
                "inheritance_depth": 1,
                "is_abstract": False,
            },
        ]
    )

    # Relationship seed (project A 由来と project B 内部の両方を作る)
    db.bulk_insert_module_imports(
        [
            {
                "source_module_id": "m_a",
                "target_module_id": "m_b",
                "import_type": "standard",
                "import_alias": "",
                "line_number": 1,
                "is_conditional": False,
            },
            {
                "source_module_id": "m_b",
                "target_module_id": "m_b",
                "import_type": "standard",
                "import_alias": "",
                "line_number": 2,
                "is_conditional": False,
            },
        ]
    )
    db.bulk_insert_function_calls(
        [
            {
                "relationship_type": "FunctionCalls",
                "source_function_id": "f_a",
                "target_function_id": "f_b",
                "call_type": "direct",
                "line_number": 1,
            },
            {
                "relationship_type": "FunctionCalls",
                "source_function_id": "f_b",
                "target_function_id": "f_b",
                "call_type": "direct",
                "line_number": 2,
            },
        ]
    )
    db.bulk_insert_inheritance(
        [
            {
                "relationship_type": "Inheritance",
                "source_class_id": "c_a",
                "target_class_id": "c_b",
                "line_number": 1,
            },
            {
                "relationship_type": "Inheritance",
                "source_class_id": "c_b",
                "target_class_id": "c_b",
                "line_number": 2,
            },
        ]
    )
    db.bulk_insert_contains(
        [
            {
                "relationship_type": "Contains",
                "source_class_id": "c_a",
                "target_function_id": "f_a",
                "line_number": 1,
            },
            {
                "relationship_type": "Contains",
                "source_class_id": "c_b",
                "target_function_id": "f_b",
                "line_number": 2,
            },
        ]
    )

    db.delete_project_data(str(project_a))

    assert _count(db, "MATCH (m:Module) WHERE m.file_path STARTS WITH $p RETURN count(m) AS cnt", {"p": str(project_a)}) == 0
    assert _count(db, "MATCH (f:Function) WHERE f.file_path STARTS WITH $p RETURN count(f) AS cnt", {"p": str(project_a)}) == 0
    assert _count(db, "MATCH (c:Class) WHERE c.file_path STARTS WITH $p RETURN count(c) AS cnt", {"p": str(project_a)}) == 0

    # project B data must remain
    assert _count(db, "MATCH (m:Module) WHERE m.file_path STARTS WITH $p RETURN count(m) AS cnt", {"p": str(project_b)}) == 1
    assert _count(db, "MATCH (f:Function) WHERE f.file_path STARTS WITH $p RETURN count(f) AS cnt", {"p": str(project_b)}) == 1
    assert _count(db, "MATCH (c:Class) WHERE c.file_path STARTS WITH $p RETURN count(c) AS cnt", {"p": str(project_b)}) == 1

    # project A に関わる関係は消え、project B 内部関係は残る
    assert _count(db, "MATCH (:Module)-[r:ModuleImports]->(:Module) RETURN count(r) AS cnt") == 1
    assert _count(db, "MATCH (:Function)-[r:FunctionCalls]->(:Function) RETURN count(r) AS cnt") == 1
    assert _count(db, "MATCH (:Class)-[r:Inheritance]->(:Class) RETURN count(r) AS cnt") == 1
    assert _count(db, "MATCH (:Class)-[r:Contains]->(:Function) RETURN count(r) AS cnt") == 1


def test_delete_project_data_does_not_match_by_basename_only(tmp_path: Path):
    db_path = tmp_path / "graph.db"
    project_x = tmp_path / "x" / "app"
    project_y = tmp_path / "y" / "app"
    project_x.mkdir(parents=True)
    project_y.mkdir(parents=True)

    db = GraphDatabase(str(db_path))
    db.initialize_schema()

    db.bulk_insert_modules(
        [
            {
                "id": "m_x",
                "name": "module_x",
                "file_path": str(project_x / "main.py"),
                "package": "x",
                "lines_of_code": 10,
                "complexity_score": 1.0,
                "is_external": False,
                "is_test": False,
                "role": "",
            },
            {
                "id": "m_y",
                "name": "module_y",
                "file_path": str(project_y / "main.py"),
                "package": "y",
                "lines_of_code": 20,
                "complexity_score": 1.0,
                "is_external": False,
                "is_test": False,
                "role": "",
            },
        ]
    )

    db.delete_project_data(str(project_x))

    assert _count(db, "MATCH (m:Module) WHERE m.file_path STARTS WITH $p RETURN count(m) AS cnt", {"p": str(project_x)}) == 0
    assert _count(db, "MATCH (m:Module) WHERE m.file_path STARTS WITH $p RETURN count(m) AS cnt", {"p": str(project_y)}) == 1


def test_delete_project_data_removes_only_absolute_project_prefix_matches(tmp_path: Path):
    db_path = tmp_path / "graph.db"
    project_root = tmp_path / "target"
    project_root.mkdir()

    db = GraphDatabase(str(db_path))
    db.initialize_schema()

    db.bulk_insert_modules(
        [
            {
                "id": "m_abs",
                "name": "module_abs",
                "file_path": str(project_root / "pkg" / "mod.py"),
                "package": "pkg",
                "lines_of_code": 10,
                "complexity_score": 1.0,
                "is_external": False,
                "is_test": False,
                "role": "",
            },
            {
                "id": "m_relative",
                "name": "module_relative",
                "file_path": "target/pkg/mod.py",
                "package": "pkg",
                "lines_of_code": 10,
                "complexity_score": 1.0,
                "is_external": False,
                "is_test": False,
                "role": "",
            },
        ]
    )

    db.delete_project_data(str(project_root))

    assert _count(db, "MATCH (m:Module) WHERE m.id = 'm_abs' RETURN count(m) AS cnt") == 0
    assert _count(db, "MATCH (m:Module) WHERE m.id = 'm_relative' RETURN count(m) AS cnt") == 1


def _count(db: GraphDatabase, query: str, params=None) -> int:
    rows = db.execute_query(query, params)
    return int(rows[0]["cnt"])
