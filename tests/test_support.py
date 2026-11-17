from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory


def repo_tempdir() -> TemporaryDirectory[str]:
    root = Path.cwd() / ".test-tmp"
    root.mkdir(exist_ok=True)
    return TemporaryDirectory(dir=root)
