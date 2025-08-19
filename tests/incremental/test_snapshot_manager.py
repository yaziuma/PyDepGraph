# tests/incremental/test_snapshot_manager.py
import pytest
import tempfile
import shutil
import subprocess
import json
from pathlib import Path

from pydepgraph.models import ExtractionResult, Module, ModuleImport, FunctionCall, Inheritance, Contains, Function, Class
from pydepgraph.incremental import SnapshotManager
from pydepgraph.exceptions import PyDepGraphError

@pytest.fixture
def git_repo_with_commits():
    """
    Creates a temporary Git repository with two commits for testing.
    Yields the path to the repo.
    """
    repo_dir = Path(tempfile.mkdtemp())

    def run_git(command, check=True):
        return subprocess.run(
            ["git"] + command,
            cwd=repo_dir,
            check=check,
            capture_output=True,
            text=True
        )

    run_git(["init", "-b", "main"])
    run_git(["config", "user.name", "Test User"])
    run_git(["config", "user.email", "test@example.com"])

    (repo_dir / "module.py").write_text("def func_a(): pass")
    run_git(["add", "module.py"])
    run_git(["commit", "-m", "Initial commit"])

    (repo_dir / "module.py").write_text("def func_a(): pass\ndef func_b(): pass")
    run_git(["add", "module.py"])
    run_git(["commit", "-m", "Add func_b"])

    yield str(repo_dir)

    shutil.rmtree(repo_dir)

class TestSnapshotManager:

    @pytest.fixture
    def mock_extraction_result(self):
        """Creates a mock ExtractionResult for saving."""
        return ExtractionResult(
            modules=[Module(name="module_a", file_path="module_a.py")],
            functions=[],
            classes=[],
            module_imports=[ModuleImport(source_module="project", target_module="module_a")],
            function_calls=[],
            inheritance=[],
            contains=[],
            metadata={"test": "data"}
        )

    def test_save_snapshot(self, git_repo_with_commits, mock_extraction_result):
        """Test saving a snapshot."""
        repo_path = git_repo_with_commits
        manager = SnapshotManager(repo_path)

        commit_hash = manager.save_snapshot(mock_extraction_result)

        snapshot_dir = Path(repo_path) / ".pydepgraph" / "snapshots"
        assert snapshot_dir.is_dir()

        snapshot_file = snapshot_dir / f"{commit_hash}.json"
        assert snapshot_file.is_file()

        with open(snapshot_file, 'r') as f:
            data = json.load(f)

        assert data["commit_hash"] == commit_hash
        assert data["graph"]["nodes"][0]["id"] == "module_a"
        assert data["graph"]["edges"][0]["source"] == "project"

    def test_load_snapshot_by_hash(self, git_repo_with_commits, mock_extraction_result):
        """Test loading a snapshot by its full commit hash."""
        repo_path = git_repo_with_commits
        manager = SnapshotManager(repo_path)

        saved_hash = manager.save_snapshot(mock_extraction_result)
        loaded_result = manager.load_snapshot(saved_hash)

        assert isinstance(loaded_result, ExtractionResult)
        assert loaded_result.modules[0].name == "module_a"
        assert loaded_result.metadata["commit_hash"] == saved_hash

    def test_load_snapshot_by_head_and_previous(self, git_repo_with_commits, mock_extraction_result):
        """Test loading snapshots using 'HEAD' and 'HEAD~1'."""
        repo_path = git_repo_with_commits
        manager = SnapshotManager(repo_path)

        second_commit_hash = manager.save_snapshot(mock_extraction_result)

        first_commit_result = ExtractionResult(modules=[], functions=[], classes=[], module_imports=[], function_calls=[], inheritance=[], contains=[], metadata={})
        first_commit_hash_from_git = subprocess.run(["git", "rev-parse", "HEAD~1"], cwd=repo_path, check=True, capture_output=True, text=True).stdout.strip()

        snapshot_dir = Path(repo_path) / ".pydepgraph" / "snapshots"
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        snapshot_file = snapshot_dir / f"{first_commit_hash_from_git}.json"
        manager._write_snapshot_file(snapshot_file, first_commit_hash_from_git, first_commit_result)

        head_result = manager.load_snapshot("HEAD")
        assert head_result.metadata["commit_hash"] == second_commit_hash
        assert len(head_result.modules) == 1

        prev_result = manager.load_snapshot("HEAD~1")
        assert prev_result.metadata["commit_hash"] == first_commit_hash_from_git
        assert len(prev_result.modules) == 0

    def test_load_invalid_git_ref(self, git_repo_with_commits):
        """Test that loading a non-existent git ref raises an error."""
        manager = SnapshotManager(git_repo_with_commits)
        with pytest.raises(PyDepGraphError, match="Could not resolve git reference"):
            manager.load_snapshot("nonexistent_hash_12345")

    def test_load_snapshot_not_found(self, git_repo_with_commits):
        """Test loading a valid commit with no snapshot file raises an error."""
        manager = SnapshotManager(git_repo_with_commits)
        commit_hash = subprocess.run(["git", "rev-parse", "HEAD"], cwd=git_repo_with_commits, check=True, capture_output=True, text=True).stdout.strip()

        with pytest.raises(PyDepGraphError, match="Snapshot not found for commit"):
            manager.load_snapshot(commit_hash)

    def test_snapshot_data_format(self, git_repo_with_commits):
        """Test the exact data format of a saved snapshot."""
        result = ExtractionResult(
            modules=[Module(name="m1", file_path="p1"), Module(name="m2", file_path="p2", is_external=True)],
            functions=[Function(name="f1", qualified_name="f1", file_path="")],
            classes=[Class(name="c1", qualified_name="c1", file_path="")],
            module_imports=[ModuleImport(source_module="m1", target_module="m2")],
            function_calls=[FunctionCall(source_function="f1", target_function="f2")],
            inheritance=[Inheritance(child_class="c1", parent_class="c2")],
            contains=[],
            metadata={}
        )

        manager = SnapshotManager(git_repo_with_commits)
        commit_hash = manager.save_snapshot(result)

        snapshot_file = Path(git_repo_with_commits) / ".pydepgraph" / "snapshots" / f"{commit_hash}.json"
        with open(snapshot_file, 'r') as f:
            data = json.load(f)

        assert data["version"] == "1.0"
        assert data["commit_hash"] == commit_hash

        nodes = data["graph"]["nodes"]
        assert len(nodes) == 4
        assert {"id": "m1", "type": "module", "path": "p1", "is_external": False} in nodes
        assert {"id": "m2", "type": "module", "path": "p2", "is_external": True} in nodes
        assert {"id": "f1", "type": "function"} in nodes
        assert {"id": "c1", "type": "class"} in nodes

        edges = data["graph"]["edges"]
        assert len(edges) == 3
        assert {"source": "m1", "target": "m2", "type": "import"} in edges
        assert {"source": "f1", "target": "f2", "type": "call"} in edges
        assert {"source": "c1", "target": "c2", "type": "inherit"} in edges
