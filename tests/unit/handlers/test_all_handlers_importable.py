"""Ensure every handler module exposes a callable `handler(event, context)`."""

from __future__ import annotations

import importlib

import pytest

HANDLER_MODULES = [
    "handlers.factor_plan",
    "handlers.factor_builder",
    "handlers.factor_detect",
    "handlers.factor_duplicate",
    "handlers.factor_evaluate",
    "handlers.factor_filter",
    "handlers.strategy_backtest",
    "handlers.vista_realtime",
]


@pytest.mark.parametrize("module_name", HANDLER_MODULES)
def test_handler_is_callable(module_name: str) -> None:
    mod = importlib.import_module(module_name)
    assert callable(getattr(mod, "handler", None)), f"{module_name} must export 'handler'"
