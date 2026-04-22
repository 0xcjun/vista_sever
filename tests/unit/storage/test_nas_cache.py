from __future__ import annotations

from pathlib import Path

import pytest

from vista_fc.storage.nas_cache import NasCache


def test_klines_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NAS_CACHE_ROOT", str(tmp_path))
    cache = NasCache.from_env()
    p = cache.klines_path(symbol="SFIF9001.CFE", freq="1m")
    assert p == tmp_path / "klines" / "1m" / "SFIF9001.CFE.parquet"


def test_model_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NAS_CACHE_ROOT", str(tmp_path))
    cache = NasCache.from_env()
    p = cache.model_path(model_id="ensemble_v1")
    assert p == tmp_path / "models" / "ensemble_v1.pkl"


def test_missing_root_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NAS_CACHE_ROOT", raising=False)
    with pytest.raises(RuntimeError):
        NasCache.from_env()
