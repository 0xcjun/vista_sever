"""Cold-start perf baselines.

Numbers drift with any change to import graph or handler setup. The harness
records them via pytest-benchmark so a regression shows up as a percentile
jump rather than a vague "it feels slower". Compare across commits with::

    uv run pytest tests/perf --benchmark-save=main
    uv run pytest tests/perf --benchmark-compare=main

No hard thresholds here — CI can add them once we have several runs of history.
"""

from __future__ import annotations

import importlib
import sys
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch


def _reset_handler_imports() -> None:
    """Drop handler / vista_fc modules from sys.modules so `import` pays the real cost."""
    for mod_name in list(sys.modules):
        if mod_name.startswith(("handlers", "vista_fc")):
            del sys.modules[mod_name]


def test_import_all_handlers_cost(benchmark) -> None:
    """Baseline for how long it takes to import every handler module.

    This is the dominant FC cold-start work — if it balloons, the factor-detect
    function's first invocation pays the price before we even enter the HTTP
    dispatcher.
    """

    def _import_all() -> None:
        _reset_handler_imports()
        for name in (
            "handlers.factor_plan",
            "handlers.factor_builder",
            "handlers.factor_detect",
            "handlers.factor_duplicate",
            "handlers.factor_evaluate",
            "handlers.factor_filter",
            "handlers.strategy_backtest",
            "handlers.vista_realtime",
            "handlers.deadletter",
        ):
            importlib.import_module(name)

    benchmark.pedantic(_import_all, rounds=5, iterations=1, warmup_rounds=1)


@patch("handlers._base.WorkspaceStorage")
@patch("handlers._base.OssClient")
def test_handler_hot_path_cost(mock_oss_cls: MagicMock, mock_ws_cls: MagicMock, benchmark) -> None:
    """Hot-path dispatch: envelope parse → log context → service → envelope out.

    Mocks out WorkspaceStorage and OssClient so the number reflects the
    framework cost, not OSS latency.
    """
    from pydantic import BaseModel

    from handlers._base import run_handler

    class _In(BaseModel):
        hello: str

    class _Out(BaseModel):
        echo: str

    def service(*, tenant, payload, workspace) -> _Out:  # noqa: ARG001
        return _Out(echo=payload.hello)

    mock_oss_cls.from_env.return_value = MagicMock()
    mock_ws_cls.return_value = MagicMock()

    event = {
        "tenant": {
            "user_hash": "u",
            "workspace_id": "EXP_1",
            "workspace_kind": "research",
            "run_id": "r",
            "requested_at": datetime.now(UTC).isoformat(),
        },
        "payload": {"hello": "world"},
    }

    def _invoke() -> dict:
        return run_handler(
            event=event,
            context=None,
            input_cls=_In,
            output_cls=_Out,
            service=service,
            function_name="bench-fn",
        )

    result = benchmark(_invoke)
    assert result["status"] == "succeeded"
