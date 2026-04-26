"""DTO for the dead-letter handler.

When an FnF step exhausts its retry policy (or hits a non-retriable error), the
flow catches the error and invokes `deadletter-handler` with the upstream step's
envelope plus the classified error. The handler persists that payload to OSS so
an operator can inspect it without trawling FC logs, then returns — letting the
flow transition to its terminal `fail` state.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from vista_fc.contracts.common import ArtifactRef, ErrorInfo


class DeadLetterInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Name of the failed upstream step (e.g. "factor-detect").
    failed_function: str = Field(min_length=1)
    # Freeform original payload that triggered the failure.
    original_payload: dict[str, object] = Field(default_factory=dict)
    # Classified error info surfaced by the upstream handler.
    error: ErrorInfo


class DeadLetterOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    deadletter_artifact: ArtifactRef
