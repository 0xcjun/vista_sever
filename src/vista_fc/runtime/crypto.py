"""Field-level encryption for sensitive request payload fields.

威胁模型: FC 调用 payload 会落到 FnF 执行历史 / FC 控制台调用记录,
HTTPS 只保护链路,不保护这些后置审计面. 本模块对 SecretStr 字段做端到端
加密,明文只在 handler 进程内存里短暂存在.

方案: libsodium sealed_box (X25519). 发送方仅需公钥; 接收方(本进程)持有
私钥,从环境变量 ``VISTA_FC_SEAL_SK_<KID>`` 加载. sealed_box 每次生成新的
ephemeral key,相同明文密文不同(防关联).

线协议:
    enc:v1:<kid>:<base64-standard>(<sealed_box_ciphertext>)

向后兼容: 不以 ``enc:v1:`` 开头的字符串原样透传,旧调用方继续工作.

密钥发放(一次性):
    python -c "import base64; from nacl.public import PrivateKey; \\
        sk=PrivateKey.generate(); \\
        print('SK_B64=', base64.b64encode(bytes(sk)).decode()); \\
        print('PK_B64=', base64.b64encode(bytes(sk.public_key)).decode())"

把 SK_B64 配到 FC 环境变量 ``VISTA_FC_SEAL_SK_V1``,把 PK_B64 下发给客户端.

轮换: 同时配置 ``VISTA_FC_SEAL_SK_V2``,客户端切到 kid=v2,迁完后下线 V1.
"""

from __future__ import annotations

import base64
import os
from functools import lru_cache

from nacl.exceptions import CryptoError
from nacl.public import PrivateKey, PublicKey, SealedBox

from vista_fc.runtime.errors import FcError

PREFIX = "enc:v1:"
_ENV_PREFIX = "VISTA_FC_SEAL_SK_"
_X25519_KEY_LEN = 32


def _input_validation(message: str, *, cause: BaseException | None = None) -> FcError:
    err = FcError("INPUT_VALIDATION", message, retriable=False, trace_id="")
    if cause is not None:
        err.__cause__ = cause
    return err


@lru_cache(maxsize=8)
def _load_sk(kid: str) -> PrivateKey:
    """加载并缓存指定 kid 的私钥. 进程级缓存; 测试需调 ``_load_sk.cache_clear()``."""
    env_name = f"{_ENV_PREFIX}{kid.upper()}"
    raw = os.environ.get(env_name)
    if not raw:
        raise _input_validation(f"missing decryption key env var: {env_name}")
    try:
        sk_bytes = base64.b64decode(raw, validate=True)
    except Exception as e:
        raise _input_validation(f"{env_name}: invalid base64") from e
    if len(sk_bytes) != _X25519_KEY_LEN:
        raise _input_validation(f"{env_name}: expected {_X25519_KEY_LEN} bytes, got {len(sk_bytes)}")
    return PrivateKey(sk_bytes)


def decrypt_field(value: str) -> str:
    """解密单个 sealed_box 字段. 无前缀的明文直接透传.

    解密失败一律抛 ``FcError(INPUT_VALIDATION)``,触发 FnF 不可重试失败.
    """
    if not value.startswith(PREFIX):
        return value
    rest = value[len(PREFIX) :]
    kid, sep, ct_b64 = rest.partition(":")
    if not sep or not kid:
        raise _input_validation("malformed enc:v1 envelope: missing kid")
    sk = _load_sk(kid)
    try:
        ct = base64.b64decode(ct_b64, validate=True)
    except Exception as e:
        raise _input_validation("malformed enc:v1 envelope: bad base64") from e
    box = SealedBox(sk)
    try:
        plaintext = box.decrypt(ct)
    except CryptoError as e:
        raise _input_validation("decryption failed: authentication or corruption") from e
    return plaintext.decode("utf-8")


def encrypt_field(plaintext: str, public_key_b64: str, *, kid: str = "v1") -> str:
    """客户端/测试侧的加密辅助. 生产发送方通常在 Python 之外用对应 libsodium 实现."""
    pk_bytes = base64.b64decode(public_key_b64, validate=True)
    if len(pk_bytes) != _X25519_KEY_LEN:
        raise ValueError(f"public_key must decode to {_X25519_KEY_LEN} bytes, got {len(pk_bytes)}")
    box = SealedBox(PublicKey(pk_bytes))
    ct = box.encrypt(plaintext.encode("utf-8"))
    return f"{PREFIX}{kid}:{base64.b64encode(ct).decode('ascii')}"
