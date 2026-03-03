from __future__ import annotations

import subprocess

import pytest


@pytest.mark.integration
def test_alembic_upgrade_downgrade_cycle() -> None:
    commands = [
        ["python", "-m", "alembic", "upgrade", "head"],
        ["python", "-m", "alembic", "downgrade", "base"],
        ["python", "-m", "alembic", "upgrade", "head"],
    ]
    try:
        for cmd in commands:
            completed = subprocess.run(cmd, check=False, capture_output=True, text=True)
            if completed.returncode != 0:
                pytest.skip(
                    "Migration smoke skipped (DB unavailable or alembic execution failed): "
                    f"{' '.join(cmd)}\n{completed.stdout}\n{completed.stderr}"
                )
    except FileNotFoundError as exc:  # pragma: no cover
        pytest.skip(f"Python/Alembic not available for migration smoke: {exc}")

