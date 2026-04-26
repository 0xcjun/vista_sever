from __future__ import annotations

import pytest

from vista_fc.runtime.retry import is_transient_oss_error, with_retry


def test_retries_until_success() -> None:
    attempts = {"n": 0}

    @with_retry(
        max_attempts=3,
        base_delay=0.0,
        retriable=lambda _e: True,
        sleep=lambda _d: None,
    )
    def flaky() -> str:
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise RuntimeError("transient")
        return "ok"

    assert flaky() == "ok"
    assert attempts["n"] == 3


def test_respects_non_retriable_predicate() -> None:
    attempts = {"n": 0}

    @with_retry(
        max_attempts=5,
        base_delay=0.0,
        retriable=lambda e: not isinstance(e, ValueError),
        sleep=lambda _d: None,
    )
    def fn() -> None:
        attempts["n"] += 1
        raise ValueError("not retriable")

    with pytest.raises(ValueError):
        fn()
    assert attempts["n"] == 1


def test_gives_up_after_max_attempts() -> None:
    attempts = {"n": 0}

    @with_retry(
        max_attempts=3,
        base_delay=0.0,
        retriable=lambda _e: True,
        sleep=lambda _d: None,
    )
    def fn() -> None:
        attempts["n"] += 1
        raise RuntimeError("still bad")

    with pytest.raises(RuntimeError):
        fn()
    assert attempts["n"] == 3


def test_oss_precondition_is_not_retriable() -> None:
    class _Exc(Exception):
        pass

    _Exc.__module__ = "oss2.exceptions"
    _Exc.__qualname__ = "PreconditionFailed"
    _Exc.__name__ = "PreconditionFailed"

    assert is_transient_oss_error(_Exc("412")) is False


def test_oss_server_error_is_retriable() -> None:
    class _Exc(Exception):
        pass

    _Exc.__module__ = "oss2.exceptions"
    _Exc.__name__ = "ServerError"

    assert is_transient_oss_error(_Exc("500")) is True


def test_network_error_is_retriable() -> None:
    assert is_transient_oss_error(ConnectionError("reset")) is True
    assert is_transient_oss_error(TimeoutError("slow")) is True
