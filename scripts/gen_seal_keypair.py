#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["pynacl>=1.5.0"]
# ///
"""一次性生成 sealed_box(X25519) 密钥对,用于 vista-fc 字段级加密.

输出:
  - SK_B64: 私钥 (32 字节 X25519, base64). 配到 FC 函数环境变量
           ``VISTA_FC_SEAL_SK_V1`` (轮换时再加 _V2 ...).
  - PK_B64: 公钥 (32 字节, base64). 下发给所有调用方,可公开.

用法:
    ./scripts/gen_seal_keypair.py              # 默认 kid=v1
    ./scripts/gen_seal_keypair.py --kid v2     # 轮换时换 kid
    ./scripts/gen_seal_keypair.py --json       # 机器可读输出

私钥只在终端打印一次. 立即写到密码管理器或部署密钥源 (阿里云 KMS / FC 控制台
环境变量),不要落任何 shell history / 日志 / git.
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
from typing import Any

from nacl.public import PrivateKey


def _gen(kid: str) -> dict[str, Any]:
    sk = PrivateKey.generate()
    return {
        "kid": kid,
        "sk_b64": base64.b64encode(bytes(sk)).decode("ascii"),
        "pk_b64": base64.b64encode(bytes(sk.public_key)).decode("ascii"),
        "sk_env_var": f"VISTA_FC_SEAL_SK_{kid.upper()}",
    }


def _print_human(info: dict[str, Any]) -> None:
    print()
    print("\033[1;33m═══ vista-fc sealed_box keypair ═══\033[0m")
    print(f"  kid         : {info['kid']}")
    print(f"  公钥 PK_B64 : {info['pk_b64']}")
    print(f"  私钥 SK_B64 : {info['sk_b64']}")
    print()
    print("\033[1;36m下一步\033[0m")
    print(f"  1) FC 函数环境变量加: \033[1m{info['sk_env_var']}={info['sk_b64']}\033[0m")
    print(f"  2) 客户端持公钥: PK_B64={info['pk_b64']}")
    print()
    print("\033[1;31m注意: 私钥只在此打印一次,立刻保存到密码管理器或 KMS.\033[0m")
    print()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="生成 vista-fc 字段级加密密钥对")
    ap.add_argument("--kid", default="v1", help="key id (默认 v1; 轮换时用 v2/v3...)")
    ap.add_argument("--json", action="store_true", help="输出 JSON,便于脚本消费")
    args = ap.parse_args(argv)

    info = _gen(args.kid)
    if args.json:
        print(json.dumps(info, ensure_ascii=False))
    else:
        _print_human(info)
    return 0


if __name__ == "__main__":
    sys.exit(main())
