"""Run the same offline checks locally and in CI after uv sync --locked."""

import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    uv = os.environ.get("UV_EXECUTABLE") or shutil.which("uv")
    if not uv:
        raise SystemExit("Install uv 0.12.19 or set UV_EXECUTABLE to its executable path.")
    commands = [
        ["lock", "--check", "--offline"],
        ["run", "--locked", "--no-sync", "ruff", "check", "."],
        ["run", "--locked", "--no-sync", "ruff", "format", "--check", "."],
        [
            "run",
            "--locked",
            "--no-sync",
            "pytest",
            "--junitxml=build/reports/python.xml",
            "--cov",
            "--cov-report=term-missing",
            "--cov-report=xml:build/reports/coverage/python.xml",
            "--cov-report=html:build/reports/coverage/python",
            "--cov-fail-under=80",
        ],
    ]
    for arguments in commands:
        subprocess.run([uv, *arguments], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
