# tests/test_cli_evolution.py
import pytest
import subprocess
import tempfile
import shutil
from pathlib import Path
import argparse

from pydepgraph.cli import cmd_evolution
from pydepgraph.models import ExtractionResult, Module
from pydepgraph.incremental import SnapshotManager
from pydepgraph.config import Config

# Copied from tests/incremental/test_snapshot_manager.py
# In a real project, this should be in a conftest.py file.
@pytest.fixture
def git_repo_with_commits():
    repo_dir = Path(tempfile.mkdtemp())
    def run_git(command, check=True):
        return subprocess.run(["git"] + command, cwd=repo_dir, check=check, capture_output=True, text=True)
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


def test_cli_evolution_command(git_repo_with_commits, capsys):
    """
    Tests the full `evolution` command from the CLI layer.
    """
    repo_path = git_repo_with_commits
    manager = SnapshotManager(repo_path)
    config = Config.get_default_config()

    # --- Setup: Create two snapshots to compare ---
    # Create snapshot for the first commit
    first_commit_hash = subprocess.run(["git", "rev-parse", "HEAD~1"], cwd=repo_path, check=True, capture_output=True, text=True).stdout.strip()
    result_before = ExtractionResult(
        modules=[Module(name="module_a", file_path="a.py")],
        functions=[], classes=[], module_imports=[], function_calls=[], inheritance=[], contains=[], metadata={}
    )
    snapshot_dir = Path(repo_path) / ".pydepgraph" / "snapshots"
    snapshot_file_1 = snapshot_dir / f"{first_commit_hash}.json"
    manager._write_snapshot_file(snapshot_file_1, first_commit_hash, result_before)

    # Create snapshot for the second (HEAD) commit
    result_after = ExtractionResult(
        modules=[Module(name="module_a", file_path="a.py"), Module(name="module_b", file_path="b.py")],
        functions=[], classes=[], module_imports=[], function_calls=[], inheritance=[], contains=[], metadata={}
    )
    manager.save_snapshot(result_after) # Saves for current HEAD

    # --- Execution: Run the `cmd_evolution` function ---
    args = argparse.Namespace(
        from_ref="HEAD~1",
        to_ref="HEAD",
        project_path=repo_path
    )

    return_code = cmd_evolution(args, config)

    assert return_code == 0

    # --- Verification: Check the output ---
    captured = capsys.readouterr()
    output = captured.out

    assert "Evolution Summary" in output
    assert "Added Nodes" in output and "1" in output
    assert "module_b" in output
    assert "Deleted Nodes" in output and "0" in output
