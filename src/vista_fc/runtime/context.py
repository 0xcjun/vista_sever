"""Event -> EnvelopeIn parsing."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from pydantic import BaseModel

from vista_fc.contracts.common import EnvelopeIn

P = TypeVar("P", bound=BaseModel)


def parse_envelope_in[P: BaseModel](event: Mapping[str, Any], payload_cls: type[P]) -> EnvelopeIn[P]:
    """Parse a raw FC event JSON object into a typed EnvelopeIn.

    Raises pydantic.ValidationError on bad input (classifier will map to
    ``INPUT_VALIDATION``).
    """
    return EnvelopeIn[payload_cls].model_validate(event)  # type: ignore[valid-type]
