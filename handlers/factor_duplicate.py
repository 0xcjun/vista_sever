"""FC handler for factor-duplicate."""

from __future__ import annotations

from typing import Any

from handlers._base import run_handler
from vista_fc.contracts.factor_duplicate import (
    FactorDuplicateInput,
    FactorDuplicateOutput,
)
from vista_fc.services.factor_duplicate import factor_duplicate_service


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    return run_handler(
        event=event,
        context=context,
        input_cls=FactorDuplicateInput,
        output_cls=FactorDuplicateOutput,
        service=factor_duplicate_service,
        function_name="factor-duplicate",
    )
