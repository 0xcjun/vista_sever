#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["pynacl>=1.5.0"]
# ///
"""Python 客户端示例:把 anthropic_api_key 加密后塞进 EnvelopeIn.

跑这个脚本只需要公钥,等价于客户端的真实部署形态.复制下面的 ``encrypt_field``
到你自己的服务里直接用.

用法:
    SEAL_PK_B64=<公钥> ./docs/examples/encrypt_field.py "sk-ant-real-key"
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys

from nacl.public import PublicKey, SealedBox

PREFIX = "enc:v1:"


def encrypt_field(plaintext: str, public_key_b64: str, *, kid: str = "v1") -> str:
    """把明文用 sealed_box 加密,返回 ``enc:v1:<kid>:<b64>`` 字符串.

    可放到任何 SecretStr 字段里,FC 入口反序列化后会自动解密.

    线协议: enc:v1:<kid>:<base64( sealed_box(plaintext) )>
    """
    pk_bytes = base64.b64decode(public_key_b64, validate=True)
    if len(pk_bytes) != 32:
        raise ValueError(f"public_key 必须解码成 32 字节, got {len(pk_bytes)}")
    box = SealedBox(PublicKey(pk_bytes))
    ct = box.encrypt(plaintext.encode("utf-8"))
    return f"{PREFIX}{kid}:{base64.b64encode(ct).decode('ascii')}"


def build_envelope(api_key_plain: str, public_key_b64: str) -> dict:
    """演示:构造一份 factor-builder 的 EnvelopeIn,api_key 字段加密.

    线协议见 src/vista_fc/contracts/factor_builder.py.
    """
    return {
        "tenant": {
            "user_hash": "u_demo",
            "workspace_id": "EXP_DEMO",
            "workspace_kind": "research",
            "run_id": "demo-001",
            "requested_at": "2026-05-02T00:00:00Z",
        },
        "payload": {
            "routes_toml_uri": "oss://vista-fc-prod/.../factor_routes.toml",
            "builder_type": "claude",
            "factor_numbers": 4,
            "batch_size": 4,
            "max_workers": 1,
            # 关键:这里是 SecretStr 字段,密文照样能通过 schema 校验,FC 在
            # _base.py 里反射到 SecretStr 字段时识别 enc:v1: 前缀并解密.
            "anthropic_api_key": encrypt_field(api_key_plain, public_key_b64),
            "anthropic_base_url": "https://api.anthropic.com",
            "anthropic_model": "claude-sonnet-4-6",
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="把 API key 加密成 enc:v1:... 串")
    ap.add_argument("plaintext", help="待加密明文 (例如 sk-ant-...)")
    ap.add_argument("--kid", default="v1", help="key id, 默认 v1")
    ap.add_argument(
        "--envelope",
        action="store_true",
        help="额外打印一份完整的 factor-builder EnvelopeIn 演示",
    )
    args = ap.parse_args(argv)

    pk = os.environ.get("SEAL_PK_B64")
    if not pk:
        print("错误: 缺少环境变量 SEAL_PK_B64 (公钥)", file=sys.stderr)
        return 2

    ciphertext = encrypt_field(args.plaintext, pk, kid=args.kid)
    print(ciphertext)

    if args.envelope:
        print()
        print("# 完整 EnvelopeIn (可直接 POST 给 FC):")
        print(json.dumps(build_envelope(args.plaintext, pk), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
