"""FC handler for factor-builder."""

from __future__ import annotations

from typing import Any

from handlers._base import run_handler
from vista_fc.contracts.factor_builder import FactorBuilderInput, FactorBuilderOutput
from vista_fc.services.factor_builder import factor_builder_service


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    return run_handler(
        event=event,
        context=context,
        input_cls=FactorBuilderInput,
        output_cls=FactorBuilderOutput,
        service=factor_builder_service,
        function_name="factor-builder",
    )
