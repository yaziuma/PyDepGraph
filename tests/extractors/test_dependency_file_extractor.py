# tests/extractors/test_dependency_file_extractor.py
import pytest
from pathlib import Path
import tempfile
import shutil

from pydepgraph.extractors.dependency_file_extractor import DependencyFileExtractor
from pydepgraph.extractors.base import RawExtractionResult

@pytest.fixture
def temp_project():
    """Set up a temporary project directory with dependency files for testing."""
    test_dir = tempfile.mkdtemp()
    project_path = Path(test_dir)

    # Create requirements.txt
    (project_path / "requirements.txt").write_text(
        "# This is a comment\n"
        "requests==2.25.1\n"
        "numpy>=1.20.0\n"
        "  # another comment\n"
        "pandas\n"
    )

    # Create pyproject.toml
    pyproject_toml_content = """
[project]
name = "my-test-project"
version = "0.1.0"
dependencies = [
    "flask~=2.0",
    "sqlalchemy[asyncio]",
]

[tool.poetry]
name = "my-poetry-project"
[tool.poetry.dependencies]
python = "^3.9"
poetry-dep = "^1.0"
"""
    (project_path / "pyproject.toml").write_text(pyproject_toml_content)

    yield str(project_path)

    # Teardown
    shutil.rmtree(test_dir)


def test_extract_dependencies_from_files(temp_project):
    """
    Test that the extractor correctly finds dependencies from both
    requirements.txt and pyproject.toml using pytest style.
    """
    extractor = DependencyFileExtractor(temp_project)
    result = extractor.extract()

    assert isinstance(result, RawExtractionResult)

    # Expected libraries - 'python' is not a library dependency
    expected_libs = {"requests", "numpy", "pandas", "flask", "sqlalchemy", "poetry-dep"}

    # Verify Modules
    extracted_module_names = {m['name'] for m in result.modules}
    assert expected_libs == extracted_module_names

    for module in result.modules:
        assert module['is_external'] is True
        assert module['extractor'] == 'dependency_file'

    # Verify ModuleImports (as dicts in RawExtractionResult)
    project_name_from_toml = "my-test-project"

    extracted_imports = result.relationships
    assert len(expected_libs) == len(extracted_imports)

    found_targets = set()
    for imprt in extracted_imports:
        assert imprt['type'] == 'ModuleImport'
        assert imprt['data']['source_module'] == project_name_from_toml
        assert imprt['data']['target_module'] in expected_libs
        assert imprt['data']['import_type'] == 'EXTERNAL_LIBRARY'
        assert imprt['data']['extractor'] == 'dependency_file'
        found_targets.add(imprt['data']['target_module'])

    # Check that all expected libs were found
    assert expected_libs == found_targets
