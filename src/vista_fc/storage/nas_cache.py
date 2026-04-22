"""NAS-backed cache paths for klines and model weights.

NAS is mounted at `$NAS_CACHE_ROOT` (default `/mnt/vista-cache`).
Cache contents are shared across all 8 functions.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class NasCache:
    root: Path

    @classmethod
    def from_env(cls) -> NasCache:
        raw = os.environ.get("NAS_CACHE_ROOT")
        if not raw:
            raise RuntimeError("NAS_CACHE_ROOT is not set")
        return cls(root=Path(raw))

    def klines_path(self, *, symbol: str, freq: str) -> Path:
        return self.root / "klines" / freq / f"{symbol}.parquet"

    def model_path(self, *, model_id: str) -> Path:
        return self.root / "models" / f"{model_id}.pkl"
