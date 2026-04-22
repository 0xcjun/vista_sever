"""FC handler for strategy-backtest."""

from __future__ import annotations

from typing import Any

from handlers._base import run_handler
from vista_fc.contracts.strategy_backtest import (
    StrategyBacktestInput,
    StrategyBacktestOutput,
)
from vista_fc.services.strategy_backtest import strategy_backtest_service


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    return run_handler(
        event=event,
        context=context,
        input_cls=StrategyBacktestInput,
        output_cls=StrategyBacktestOutput,
        service=strategy_backtest_service,
        function_name="strategy-backtest",
    )
