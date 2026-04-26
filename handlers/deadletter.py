"""FC handler for the deadletter trap (P2-10: FnF DLQ)."""

from __future__ import annotations

from typing import Any

from handlers._base import run_handler
from vista_fc.contracts.deadletter import DeadLetterInput, DeadLetterOutput
from vista_fc.services.deadletter import deadletter_service


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    return run_handler(
        event=event,
        context=context,
        input_cls=DeadLetterInput,
        output_cls=DeadLetterOutput,
        service=deadletter_service,
        function_name="deadletter",
    )
