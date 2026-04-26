"""Event-layer idempotency store backed by OSS tombstones.

FnF retries reuse the same run_id. To make handlers at-most-once, we write a
tombstone object to OSS on first successful completion and, on replay, return
the cached envelope instead of re-running the service.

Failures do NOT write a tombstone: retriable errors must be retryable.

Atomicity relies on OSS's If-None-Match: * semantics (returns 412 if the key
already exists). Two workers racing the same run_id → one wins the claim; the
loser reads the winner's result and returns it.
"""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from pathlib import Path
from typing import Any

from vista_fc.storage.oss_client import OssClient


def is_enabled() -> bool:
    """Opt-in via VISTA_FC_IDEMPOTENCY=1 for safe incremental rollout."""
    return os.environ.get("VISTA_FC_IDEMPOTENCY", "").lower() in ("1", "true", "yes")


def tombstone_key(*, user_hash: str, function_name: str, run_id: str) -> str:
    return f"user_data/{user_hash}/idempotency/{function_name}/{run_id}.json"


class IdempotencyStore:
    """Thin wrapper over OssClient for tombstone read/write."""

    def __init__(self, oss: OssClient) -> None:
        self._oss = oss

    def lookup(self, key: str) -> dict[str, Any] | None:
        """Return the cached envelope if the tombstone exists, else None."""
        if not self._oss.exists(key=key):
            return None
        local = Path(tempfile.gettempdir()) / f"idempotency_{uuid.uuid4().hex}.json"
        try:
            self._oss.get_to_file(key=key, local_path=local)
            return json.loads(local.read_text(encoding="utf-8"))
        finally:
            if local.exists():
                local.unlink()

    def claim(self, key: str, envelope: dict[str, Any]) -> bool:
        """Atomically write the tombstone.

        Returns True if this caller won the claim, False if another caller
        wrote the tombstone first (concurrent replay). Callers that lose the
        race should fall back to :meth:`lookup`.
        """
        local = Path(tempfile.gettempdir()) / f"idempotency_{uuid.uuid4().hex}.json"
        local.write_text(json.dumps(envelope, ensure_ascii=False), encoding="utf-8")
        try:
            try:
                self._oss.put_from_file(key=key, local_path=local, if_none_match="*")  # type: ignore[call-arg]
            except Exception as e:  # noqa: BLE001
                if type(e).__name__ == "PreconditionFailed":
                    return False
                raise
            return True
        finally:
            if local.exists():
                local.unlink()
