from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import BaseModel, ValidationError

from vista_fc.runtime.context import parse_envelope_in


class _DummyPayload(BaseModel):
    hello: str


def test_parse_valid_envelope() -> None:
    event = {
        "tenant": {
            "user_hash": "u",
            "workspace_id": "EXP_1",
            "workspace_kind": "research",
            "run_id": "r",
            "requested_at": "2026-04-22T10:00:00Z",
        },
        "payload": {"hello": "world"},
    }
    env = parse_envelope_in(event, _DummyPayload)
    assert env.tenant.user_hash == "u"
    assert env.payload.hello == "world"
    assert env.tenant.requested_at.tzinfo is not None


def test_parse_rejects_missing_tenant() -> None:
    with pytest.raises(ValidationError):
        parse_envelope_in({"payload": {"hello": "x"}}, _DummyPayload)


def test_parse_rejects_extra_top_level() -> None:
    event = {
        "tenant": {
            "user_hash": "u",
            "workspace_id": "EXP_1",
            "workspace_kind": "research",
            "run_id": "r",
            "requested_at": datetime.now(UTC).isoformat(),
        },
        "payload": {"hello": "x"},
        "unknown": "field",
    }
    with pytest.raises(ValidationError):
        parse_envelope_in(event, _DummyPayload)
