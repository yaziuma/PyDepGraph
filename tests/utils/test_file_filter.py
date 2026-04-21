from pathlib import Path

from pydepgraph.utils.file_filter import iter_python_files


def test_iter_python_files_excludes_venv_and_pycache(tmp_path: Path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "ok.py").write_text("print('ok')\n", encoding="utf-8")

    (tmp_path / ".venv" / "lib").mkdir(parents=True)
    (tmp_path / ".venv" / "lib" / "skip.py").write_text("print('skip')\n", encoding="utf-8")

    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "skip_too.py").write_text("print('skip')\n", encoding="utf-8")

    found = {p.relative_to(tmp_path).as_posix() for p in iter_python_files(tmp_path)}
    assert found == {"pkg/ok.py"}


def test_iter_python_files_keeps_non_excluded_files(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "src" / "b.py").write_text("x = 2\n", encoding="utf-8")

    found = sorted(p.relative_to(tmp_path).as_posix() for p in iter_python_files(tmp_path))
    assert found == ["src/a.py", "src/b.py"]
