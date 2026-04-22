"""FC handler for vista-realtime."""

from __future__ import annotations

from typing import Any

from handlers._base import run_handler
from vista_fc.contracts.vista_realtime import (
    VistaRealtimeInput,
    VistaRealtimeOutput,
)
from vista_fc.services.vista_realtime import vista_realtime_service


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    return run_handler(
        event=event,
        context=context,
        input_cls=VistaRealtimeInput,
        output_cls=VistaRealtimeOutput,
        service=vista_realtime_service,
        function_name="vista-realtime",
    )
