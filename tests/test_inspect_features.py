from pathlib import Path
import argparse

from pydepgraph.cli import cmd_query
from pydepgraph.config import Config
from pydepgraph.inspect import render_skeleton, render_target_function, render_context


def test_render_skeleton_includes_ellipsis(tmp_path: Path):
    target = tmp_path / "sample.py"
    target.write_text(
        "class A:\n"
        "    def run(self, x: int) -> int:\n"
        "        return x + 1\n"
        "\n"
        "def hello(name: str) -> str:\n"
        "    return f'hi {name}'\n",
        encoding="utf-8",
    )

    out = render_skeleton(str(target))
    assert "class A:" in out
    assert "def run(x: int) -> int: ..." in out
    assert "def hello(name: str) -> str: ..." in out
    assert "return x + 1" not in out


def test_render_target_function_returns_implementation(tmp_path: Path):
    target = tmp_path / "sample.py"
    target.write_text(
        "def first():\n"
        "    return 1\n"
        "\n"
        "def second():\n"
        "    value = first()\n"
        "    return value\n",
        encoding="utf-8",
    )

    out = render_target_function(str(target), "second")
    assert "def second()" in out
    assert "value = first()" in out
    assert "def first()" not in out


def test_context_query_outputs_dependency_skeleton_and_target(tmp_path: Path, capsys):
    root = tmp_path / "proj"
    root.mkdir()
    (root / "dep.py").write_text(
        "class Dep:\n"
        "    def run(self):\n"
        "        return 'ok'\n",
        encoding="utf-8",
    )
    target = root / "main.py"
    target.write_text(
        "from dep import Dep\n"
        "\n"
        "def execute():\n"
        "    return Dep().run()\n",
        encoding="utf-8",
    )

    args = argparse.Namespace(
        query_type="context",
        target=str(target),
        depth=1,
        project_root=str(root),
        filter=None,
        format="table",
        node_type="module",
        value=None,
    )

    code = cmd_query(args, Config.get_default_config())
    assert code == 0
    output = capsys.readouterr().out
    assert "=== Dependencies (Skeleton) ===" in output
    assert "class Dep:" in output
    assert "def run(): ..." in output
    assert "=== Target Implementation ===" in output
    assert "return Dep().run()" in output


def test_render_context_direct_call(tmp_path: Path):
    root = tmp_path / "proj"
    root.mkdir()
    (root / "x.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    target = root / "y.py"
    target.write_text("import x\n\n\ndef g():\n    return x.f()\n", encoding="utf-8")

    out = render_context(str(target), depth=1, project_root=str(root))
    assert "=== Dependencies (Skeleton) ===" in out
    assert "def f(): ..." in out
    assert "=== Target Implementation ===" in out
