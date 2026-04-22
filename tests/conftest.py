"""pytest global fixtures."""

from __future__ import annotations

import random
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _deterministic_seeds() -> None:
    """Fix seeds for reproducibility across all tests.

    numpy is seeded lazily — only if a test pulls it in as a transitive dep.
    """
    random.seed(42)
    try:
        import numpy as np  # pyright: ignore[reportMissingImports]

        np.random.seed(42)
    except ImportError:
        pass


@pytest.fixture
def fixtures_dir() -> Path:
    """Absolute path to tests/fixtures/."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def events_dir(fixtures_dir: Path) -> Path:
    """Absolute path to tests/fixtures/events/."""
    return fixtures_dir / "events"
