from fnmatch import fnmatch
from pathlib import Path
from typing import Iterator, Sequence


DEFAULT_EXCLUDE_PATTERNS = [
    "__pycache__",
    ".git",
    ".pytest_cache",
    "*.pyc",
    "venv",
    ".venv",
]


def _should_exclude(path: Path, exclude_patterns: Sequence[str]) -> bool:
    for part in path.parts:
        for pattern in exclude_patterns:
            if "*" in pattern:
                if fnmatch(part, pattern):
                    return True
            elif part == pattern:
                return True
    return False


def iter_python_files(root: Path, exclude_patterns: list[str] | None = None) -> Iterator[Path]:
    """
    Recursively yields .py files under root while excluding paths matching patterns.

    Directory/file-name parts are matched by exact name, while wildcard patterns are
    matched with fnmatch.
    """
    patterns = exclude_patterns or DEFAULT_EXCLUDE_PATTERNS
    for py_file in root.rglob("*.py"):
        if _should_exclude(py_file.relative_to(root), patterns):
            continue
        yield py_file
