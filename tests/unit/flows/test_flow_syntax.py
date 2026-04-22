"""Invoke scripts/validate_flow.py as a pytest to gate CI."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_all_flows_pass_static_validation() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate_flow.py")],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"flow lint failed:\nstderr:\n{result.stderr}\nstdout:\n{result.stdout}"
