"""Load a handler callable by `<module>:<func>` spec."""

from __future__ import annotations

import importlib
from collections.abc import Callable
from typing import Any, cast

HandlerFn = Callable[[dict[str, Any], Any], dict[str, Any]]


def load_handler(spec: str) -> HandlerFn:
    if ":" not in spec:
        raise ValueError(f"handler spec must be '<module>:<func>', got {spec!r}")
    module_name, func_name = spec.split(":", 1)
    module = importlib.import_module(module_name)
    fn = getattr(module, func_name)
    if not callable(fn):
        raise TypeError(f"{spec} is not callable")
    return cast(HandlerFn, fn)
