from __future__ import annotations

import base64

import pytest
from nacl.public import PrivateKey

from vista_fc.runtime.crypto import PREFIX, _load_sk, decrypt_field, encrypt_field
from vista_fc.runtime.errors import FcError


@pytest.fixture
def keypair_v1(monkeypatch: pytest.MonkeyPatch) -> tuple[str, str]:
    """Generate an X25519 keypair, install SK as VISTA_FC_SEAL_SK_V1, return (sk_b64, pk_b64)."""
    sk = PrivateKey.generate()
    sk_b64 = base64.b64encode(bytes(sk)).decode()
    pk_b64 = base64.b64encode(bytes(sk.public_key)).decode()
    monkeypatch.setenv("VISTA_FC_SEAL_SK_V1", sk_b64)
    _load_sk.cache_clear()
    yield sk_b64, pk_b64
    _load_sk.cache_clear()


def test_plaintext_passthrough() -> None:
    # 不带前缀的字符串原样返回, 保持向后兼容
    assert decrypt_field("sk-plain-text") == "sk-plain-text"
    assert decrypt_field("") == ""


def test_roundtrip(keypair_v1: tuple[str, str]) -> None:
    _, pk = keypair_v1
    plaintext = "sk-ant-api03-roundtrip"  # pragma: allowlist secret
    ct = encrypt_field(plaintext, pk)
    assert ct.startswith(f"{PREFIX}v1:")
    assert decrypt_field(ct) == plaintext


def test_roundtrip_produces_distinct_ciphertexts(keypair_v1: tuple[str, str]) -> None:
    # sealed_box 每次新 ephemeral key, 同明文密文不同, 防关联分析
    _, pk = keypair_v1
    a = encrypt_field("same", pk)
    b = encrypt_field("same", pk)
    assert a != b


def test_tampered_ciphertext_raises(keypair_v1: tuple[str, str]) -> None:
    _, pk = keypair_v1
    ct = encrypt_field("payload", pk)
    head, _, tail = ct.rpartition(":")
    raw = bytearray(base64.b64decode(tail))
    raw[-1] ^= 0x01
    tampered = f"{head}:{base64.b64encode(bytes(raw)).decode()}"
    with pytest.raises(FcError) as ei:
        decrypt_field(tampered)
    assert ei.value.code == "INPUT_VALIDATION"
    assert ei.value.retriable is False


def test_unknown_kid_raises(keypair_v1: tuple[str, str]) -> None:
    _, pk = keypair_v1
    ct = encrypt_field("payload", pk, kid="v99")
    with pytest.raises(FcError) as ei:
        decrypt_field(ct)
    assert ei.value.code == "INPUT_VALIDATION"
    assert "VISTA_FC_SEAL_SK_V99" in ei.value.message


def test_malformed_envelope_missing_kid() -> None:
    with pytest.raises(FcError) as ei:
        decrypt_field(f"{PREFIX}no-colon-here")
    assert ei.value.code == "INPUT_VALIDATION"


def test_malformed_envelope_empty_kid() -> None:
    with pytest.raises(FcError) as ei:
        decrypt_field(f"{PREFIX}:abc")
    assert ei.value.code == "INPUT_VALIDATION"


def test_bad_base64_raises(keypair_v1: tuple[str, str]) -> None:
    with pytest.raises(FcError) as ei:
        decrypt_field(f"{PREFIX}v1:not!valid!b64")
    assert ei.value.code == "INPUT_VALIDATION"


def test_invalid_sk_env_var_length(monkeypatch: pytest.MonkeyPatch) -> None:
    # 私钥长度异常应在加载时抛错, 而不是延迟到解密阶段
    monkeypatch.setenv("VISTA_FC_SEAL_SK_V1", base64.b64encode(b"too-short").decode())
    _load_sk.cache_clear()
    with pytest.raises(FcError) as ei:
        decrypt_field(f"{PREFIX}v1:AAAA")
    assert ei.value.code == "INPUT_VALIDATION"
    assert "32 bytes" in ei.value.message
    _load_sk.cache_clear()
