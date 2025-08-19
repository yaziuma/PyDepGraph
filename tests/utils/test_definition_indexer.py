# tests/utils/test_definition_indexer.py
import pytest
from pathlib import Path
import tempfile
import shutil
import textwrap

# The class we are testing doesn't exist yet.
# from pydepgraph.utils.definition_indexer import DefinitionIndexer

@pytest.fixture
def sample_project_for_indexing():
    """Creates a sample project with a complex structure for indexer testing."""
    project_dir = Path(tempfile.mkdtemp())

    # 1. Root file
    (project_dir / "root_module.py").write_text(textwrap.dedent("""\
        def root_func():
            pass

        class RootClass:
            def root_method(self):
                pass
    """))

    # 2. Subdirectory with a package
    services_dir = project_dir / "services"
    services_dir.mkdir()
    (services_dir / "__init__.py").touch() # Empty init
    (services_dir / "user_service.py").write_text(textwrap.dedent("""\
        # services/user_service.py

        class User:
            def __init__(self, name):
                self.name = name

            def get_profile(self):
                # A nested function
                def format_profile():
                    return f"User: {self.name}"
                return format_profile()

        async def fetch_user(user_id):
            return User("test")
    """))

    # 3. Another subdirectory for deeper nesting, but not a package
    utils_dir = project_dir / "utils"
    utils_dir.mkdir()
    (utils_dir / "helpers.py").write_text(textwrap.dedent("""\
        # utils/helpers.py
        def format_string(s):
            return s.strip()
    """))

    yield str(project_dir)

    shutil.rmtree(project_dir)

def test_definition_indexer(sample_project_for_indexing):
    """
    Tests that the DefinitionIndexer correctly indexes all definitions
    in a sample project, generating correct FQNs.
    """
    # This import will fail until the class is created.
    from pydepgraph.utils.definition_indexer import DefinitionIndexer

    project_path = sample_project_for_indexing
    indexer = DefinitionIndexer(project_path)
    index = indexer.index_project()

    # Expected FQNs and their data
    expected_fqns = {
        "root_module.root_func",
        "root_module.RootClass",
        "root_module.RootClass.root_method",
        "services.user_service.User",
        "services.user_service.User.__init__",
        "services.user_service.User.get_profile",
        "services.user_service.User.get_profile.format_profile", # Nested function
        "services.user_service.fetch_user", # async function
        "utils.helpers.format_string",
    }

    # Basic check: all expected FQNs are present
    assert set(index.keys()) == expected_fqns

    # Detailed check for a few items
    # Check root_module.RootClass.root_method
    root_method_info = index["root_module.RootClass.root_method"]
    assert root_method_info["node_type"] == "method"
    assert root_method_info["file_path"].endswith("root_module.py")
    assert isinstance(root_method_info["start_line"], int)
    assert isinstance(root_method_info["end_line"], int)
    assert root_method_info["start_line"] > 0
    assert root_method_info["end_line"] >= root_method_info["start_line"]

    # Check services.user_service.fetch_user (async)
    fetch_user_info = index["services.user_service.fetch_user"]
    assert fetch_user_info["node_type"] == "function"
    assert "user_service.py" in fetch_user_info["file_path"]
    assert isinstance(fetch_user_info["start_line"], int)

    # Check nested function
    nested_func_info = index["services.user_service.User.get_profile.format_profile"]
    assert nested_func_info["node_type"] == "function"
    assert "user_service.py" in nested_func_info["file_path"]
