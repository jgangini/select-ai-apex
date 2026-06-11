from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "installer"))

from select_ai_apex.demo_data import validate_demo_catalog


def main() -> int:
    for message in validate_demo_catalog():
        print(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
