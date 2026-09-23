"""Launcher so the app can be started from the workspace root."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
APP_DIR = ROOT_DIR / "StudentResultSystem"


def main() -> None:
	if str(APP_DIR) not in sys.path:
		sys.path.insert(0, str(APP_DIR))
	runpy.run_path(str(APP_DIR / "main.py"), run_name="__main__")


if __name__ == "__main__":
	main()
