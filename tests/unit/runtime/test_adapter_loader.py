from __future__ import annotations

import sys
import types
from typing import Any

import pytest

from vista_fc.runtime.adapter.handlers_loader import load_handler


def _example(event: dict[str, Any], context: object) -> dict[str, Any]:  # noqa: ARG001
    return {"echo": event}


def test_load_handler_from_spec() -> None:
    mod = types.ModuleType("_fake_handlers_loader_test")
    mod.handler = _example  # type: ignore[attr-defined]
    sys.modules["_fake_handlers_loader_test"] = mod

    fn = load_handler("_fake_handlers_loader_test:handler")
    assert fn({"x": 1}, None) == {"echo": {"x": 1}}


def test_load_handler_rejects_missing_colon() -> None:
    with pytest.raises(ValueError):
        load_handler("no-colon-here")


def test_load_handler_rejects_missing_module() -> None:
    with pytest.raises(ModuleNotFoundError):
        load_handler("no_such_module_9fc8abcd:handler")


def test_load_handler_rejects_non_callable() -> None:
    mod = types.ModuleType("_fake_non_callable_loader_test")
    mod.not_a_fn = "stringly"  # type: ignore[attr-defined]
    sys.modules["_fake_non_callable_loader_test"] = mod
    with pytest.raises(TypeError):
        load_handler("_fake_non_callable_loader_test:not_a_fn")
