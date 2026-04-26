#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "alibabacloud-fc20230330>=4.0.0",
#   "alibabacloud-fnf20190315>=2.0.0",
#   "alibabacloud-tea-openapi>=0.3.0",
# ]
# ///
"""上线后调用所有函数的 Python 演示脚本。

这个脚本用阿里云 SDK 直调 FC + FnF，是 scripts/invoke_all.sh 的 Python 等价物。
拿来：
  1) 部署后冒烟工具（同 bash 版）
  2) 客户端代码模板 — 复制 InvokeFC.invoke / FnFClient.start 那两段到你自己的服务里改改就能用

执行靠 uv 的 inline metadata 自动装依赖（不污染项目 venv）：

    ALIYUN_AK=... ALIYUN_SK=... ./scripts/invoke_all.py fnf
    ALIYUN_AK=... ALIYUN_SK=... uv run scripts/invoke_all.py plan

环境变量：
  ALIYUN_AK / ALIYUN_SK   必填  AccessKey / Secret
                                可从 ~/.s/access.yaml 里部署用的 alias 抠出来：
                                  yq '.<alias>.AccessKeyID' ~/.s/access.yaml
  FC_REGION               可选  默认 cn-hangzhou
  FC_SUFFIX               可选  函数名后缀（多环境隔离用），默认空
  OSS_BUCKET              可选  默认 vista-fc-prod
  USER_HASH               可选  默认 u_demo
  WORKSPACE_ID            可选  默认 EXP_DEMO
  RUN_ID                  可选  默认 demo-时间戳；FnF 重跑同名时已成功 step 自动跳过
  FNF_POLL                可选  fnf 命令是否轮询执行状态（默认 1）
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import UTC, datetime
from typing import Any

from alibabacloud_fc20230330 import models as fc_models
from alibabacloud_fc20230330.client import Client as FCClient
from alibabacloud_fnf20190315 import models as fnf_models
from alibabacloud_fnf20190315.client import Client as FnFClient
from alibabacloud_tea_openapi import models as openapi_models

# ──────────────────────────────────────────────────────────────────────────
# 配置
# ──────────────────────────────────────────────────────────────────────────


def _env(name: str, default: str | None = None, *, required: bool = False) -> str:
    v = os.environ.get(name, default)
    if required and not v:
        sys.exit(f"环境变量 {name} 必填")
    return v or ""


AK = _env("ALIYUN_AK", required=True)
SK = _env("ALIYUN_SK", required=True)
REGION = _env("FC_REGION", "cn-hangzhou")
SUFFIX = _env("FC_SUFFIX", "")
OSS_BUCKET = _env("OSS_BUCKET", "vista-fc-prod")
USER_HASH = _env("USER_HASH", "u_demo")
WORKSPACE_ID = _env("WORKSPACE_ID", "EXP_DEMO")
RUN_ID = _env("RUN_ID", f"demo-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
FNF_POLL = _env("FNF_POLL", "1") == "1"

# 演示用 problem code（vista 3.2.x 命名）
DEMO_PROBLEM_CODE = "FTS_PROBLEM_A504A636"  # 期货-股指-30分钟-量价择时

# 共用 tenant 块（所有函数都消费 EnvelopeIn.tenant）
TENANT: dict[str, Any] = {
    "user_hash": USER_HASH,
    "workspace_id": WORKSPACE_ID,
    "workspace_kind": "research",
    "run_id": RUN_ID,
    "requested_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
}

WS_BASE = f"oss://{OSS_BUCKET}/user_data/{USER_HASH}/research/{WORKSPACE_ID}"
RESEARCH_DATA_URI = f"oss://{OSS_BUCKET}/research_data/future_kline.duckdb"

# ──────────────────────────────────────────────────────────────────────────
# SDK 客户端
# ──────────────────────────────────────────────────────────────────────────


def _openapi_config(endpoint: str) -> openapi_models.Config:
    return openapi_models.Config(access_key_id=AK, access_key_secret=SK, endpoint=endpoint)


def fc_client() -> FCClient:
    # FC 3.0 endpoint 的标准形式：<region>.fc.aliyuncs.com
    return FCClient(_openapi_config(f"{REGION}.fc.aliyuncs.com"))


def fnf_client() -> FnFClient:
    return FnFClient(_openapi_config(f"cn-{REGION.removeprefix('cn-')}.fnf.aliyuncs.com"))


# ──────────────────────────────────────────────────────────────────────────
# 调单个 fc 函数
# ──────────────────────────────────────────────────────────────────────────


def _banner(msg: str) -> None:
    print(f"\n\033[1;36m═══ {msg} ═══\033[0m")


def invoke_fc(fn: str, payload: dict[str, Any]) -> dict[str, Any]:
    """调一个 FC 3.0 函数，返回解析后的 envelope。"""
    fname = f"{fn}{SUFFIX}"
    envelope_in = {"tenant": TENANT, "payload": payload}

    _banner(f"▶ invoke {fname}")
    print("envelope-in:")
    print(json.dumps(envelope_in, ensure_ascii=False, indent=2))
    print()

    req = fc_models.InvokeFunctionRequest(
        body=json.dumps(envelope_in, ensure_ascii=False).encode("utf-8"),
    )
    resp = fc_client().invoke_function(fname, req)

    body_bytes = resp.body if isinstance(resp.body, bytes) else resp.body.read()
    try:
        envelope_out = json.loads(body_bytes.decode("utf-8"))
    except json.JSONDecodeError:
        envelope_out = {"_raw": body_bytes.decode("utf-8", errors="replace")}

    print("envelope-out:")
    print(json.dumps(envelope_out, ensure_ascii=False, indent=2))
    return envelope_out


# ──────────────────────────────────────────────────────────────────────────
# 各 step 示例（payload 形态见 src/vista_fc/contracts/<name>.py）
# ──────────────────────────────────────────────────────────────────────────


def do_plan() -> dict[str, Any]:
    return invoke_fc(
        "factor-plan",
        {
            "user_input": "动量反转因子挖掘",
            "plan_model": None,
            "skill_path": None,
            "interactive": False,
            "factor_numbers": 4,
        },
    )


def do_builder() -> dict[str, Any]:
    routes_uri = os.environ.get("ROUTES_URI", f"{WS_BASE}/factor_routes.toml")
    return invoke_fc(
        "factor-builder",
        {
            "routes_toml_uri": routes_uri,
            "builder_type": "agno_agent",
            "factor_numbers": 4,
            "batch_size": 4,
            "max_workers": 1,
            "multi_turn": False,
            "model": None,
            "max_retries": 2,
        },
    )


def do_detect() -> dict[str, Any]:
    db_uri = os.environ.get("FACTORS_DB_URI", f"{WS_BASE}/factors.duckdb")
    return invoke_fc(
        "factor-detect",
        {
            "factors_db_uri": db_uri,
            "research_data_uri": RESEARCH_DATA_URI,
            "max_workers": 4,
            "timeout": 60,
        },
    )


def do_duplicate() -> dict[str, Any]:
    db_uri = os.environ.get("FACTORS_DB_URI", f"{WS_BASE}/factors.duckdb")
    return invoke_fc(
        "factor-duplicate",
        {
            "factors_db_uri": db_uri,
            "research_data_uri": RESEARCH_DATA_URI,
            "route_codes": [],
            "problem_codes": [DEMO_PROBLEM_CODE],
            "threshold": 0.8,
            "max_workers": 1,
            "timeout": 120,
        },
    )


def do_evaluate() -> dict[str, Any]:
    db_uri = os.environ.get("FACTORS_DB_URI", f"{WS_BASE}/factors.duckdb")
    return invoke_fc(
        "factor-evaluate",
        {
            "factors_db_uri": db_uri,
            "research_data_uri": RESEARCH_DATA_URI,
            "route_codes": [],
            "problem_codes": [DEMO_PROBLEM_CODE],
            "models": ["DirectExposure"],
            "max_workers": 1,
            "timeout": 180,
            "fee_rate": 0.0,
        },
    )


def do_filter() -> dict[str, Any]:
    db_uri = os.environ.get("FACTORS_DB_URI", f"{WS_BASE}/factors.duckdb")
    return invoke_fc(
        "factor-filter",
        {
            "factors_db_uri": db_uri,
            "research_data_uri": RESEARCH_DATA_URI,
            "problem_codes": [DEMO_PROBLEM_CODE],
            "route_codes": [],
            "evaluate_methods": [],
            "filter_methods": [],
            "positive_threshold": 0.0,
            "n": 10,
            "creator": "vista-fc-tutorial",
            "outsample_sdt": "20250101",
        },
    )


def do_backtest() -> dict[str, Any]:
    toml_uri = os.environ.get("STRATEGY_TOML_URI", f"{WS_BASE}/strategy.toml")
    return invoke_fc(
        "strategy-backtest",
        {
            "strategy_toml_uri": toml_uri,
            "research_data_uri": RESEARCH_DATA_URI,
            "mode": "research",
            "data_mode": "total",
            "backtest_workers": 1,
            "fee_rate": 0.0,
            "digits": 2,
            "n_jobs": 1,
            "yearly_days": 252,
        },
    )


def do_realtime() -> dict[str, Any]:
    toml_uri = os.environ.get(
        "STRATEGY_TOML_URI",
        f"oss://{OSS_BUCKET}/user_data/{USER_HASH}/realtime/{WORKSPACE_ID}/strategy.toml",
    )
    return invoke_fc(
        "vista-realtime",
        {
            "strategy_toml_uri": toml_uri,
            "update_mode": "auto",
            "push_targets": ["default"],
        },
    )


def do_deadletter() -> dict[str, Any]:
    """演示直调；正常路径是 FnF catch.goto 触发，不需要客户端调它。"""
    return invoke_fc(
        "deadletter",
        {
            "failed_function": "factor-detect",
            "original_payload": {"factors_db_uri": "oss://example/factors.duckdb"},
            "error": {
                "code": "VISTA_LOGIC_ERROR",
                "message": "demo failure for tutorial",
                "retriable": False,
                "trace_id": "tr-tutorial-demo",
            },
        },
    )


# ──────────────────────────────────────────────────────────────────────────
# FnF — 推荐生产路径
# ──────────────────────────────────────────────────────────────────────────


def do_fnf() -> dict[str, Any]:
    flow_name = f"research-pipeline{SUFFIX}"
    fnf_input: dict[str, Any] = {
        "tenant": TENANT,
        # factor-plan
        "user_input": "动量反转因子挖掘",
        "plan_model": None,
        "skill_path": None,
        "interactive": False,
        # factor-builder
        "build_model": None,
        "builder_type": "agno_agent",
        "factor_numbers": 4,
        "batch_size": 4,
        "build_workers": 1,
        "multi_turn": False,
        "build_max_retries": 2,
        # factor-detect
        "detect_workers": 4,
        "detect_timeout": 60,
        # factor-duplicate
        "dup_workers": 1,
        "dup_threshold": 0.8,
        "dup_timeout": 120,
        # factor-evaluate
        "eval_workers": 1,
        "eval_timeout": 180,
        "eval_models": ["DirectExposure"],
        "fee_rate": 0.0,
        # factor-filter
        "problem_codes": [DEMO_PROBLEM_CODE],
        "evaluate_methods": [],
        "filter_methods": [],
        "positive_extractor": "ratio_across_problems",
        "positive_metric": "绝对收益",
        "positive_threshold": 0.0,
        "top_n": 10,
        "author": "vista-fc-tutorial",
        "outsample_sdt": "20250101",
        # strategy-backtest (foreach fanout)
        "mode": "research",
        "data_mode": "total",
        "backtest_concurrency": 4,
        "backtest_workers": 1,
        "wbt": {"fee_rate": 0.0, "digits": 2, "n_jobs": 1, "yearly_days": 252},
        "research_data_uri": RESEARCH_DATA_URI,
    }

    _banner(f"▶ start FnF flow {flow_name}")
    print(f"execution name: {RUN_ID}")
    print("input:")
    print(json.dumps(fnf_input, ensure_ascii=False, indent=2))
    print()

    fnf = fnf_client()
    fnf.start_execution(
        fnf_models.StartExecutionRequest(
            flow_name=flow_name,
            execution_name=RUN_ID,
            input=json.dumps(fnf_input, ensure_ascii=False),
        )
    )
    print(f"started, execution_name = {RUN_ID}")

    if not FNF_POLL:
        print("\n查执行状态（FNF_POLL=0 时手动）：")
        print(
            f"  s cli fnf DescribeExecution --flow-name {flow_name} " f"--execution-name {RUN_ID} --access <your-alias>"
        )
        return {"execution_name": RUN_ID}

    # 轮询执行状态
    print("\n轮询执行状态（每 10s 一次）...")
    last_status = ""
    while True:
        time.sleep(10)
        desc = fnf.describe_execution(fnf_models.DescribeExecutionRequest(flow_name=flow_name, execution_name=RUN_ID))
        body = desc.body
        status = body.status
        if status != last_status:
            print(f"  [{datetime.now().strftime('%H:%M:%S')}] status = {status}")
            last_status = status
        if status in ("Succeeded", "Failed", "Stopped", "TimedOut"):
            print()
            print(f"flow {status}; output:")
            print(body.output or "(empty)")
            if status != "Succeeded":
                print()
                print("失败时看 deadletter 落盘：")
                print(f"  ossutil ls oss://{OSS_BUCKET}/user_data/{USER_HASH}/deadletter/{RUN_ID}/")
            return {"execution_name": RUN_ID, "status": status, "output": body.output}


# ──────────────────────────────────────────────────────────────────────────
# 主入口
# ──────────────────────────────────────────────────────────────────────────


STEPS = {
    "plan": do_plan,
    "builder": do_builder,
    "detect": do_detect,
    "duplicate": do_duplicate,
    "evaluate": do_evaluate,
    "filter": do_filter,
    "backtest": do_backtest,
    "realtime": do_realtime,
    "deadletter": do_deadletter,
    "fnf": do_fnf,
}


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="invoke_all.py",
        description="上线后调用所有函数的 Python 演示脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="\n".join(
            [
                "示例：",
                "  ALIYUN_AK=... ALIYUN_SK=... ./scripts/invoke_all.py fnf",
                "  ALIYUN_AK=... ALIYUN_SK=... ./scripts/invoke_all.py plan",
                "  ALIYUN_AK=... ALIYUN_SK=... ./scripts/invoke_all.py chain",
            ]
        ),
    )
    parser.add_argument(
        "step",
        choices=[*STEPS.keys(), "chain"],
        help="要跑哪一步；'chain' 按顺序串调每个函数（仅演示，端到端跑请用 fnf）",
    )
    args = parser.parse_args()

    if args.step == "chain":
        for name in ("plan", "builder", "detect", "duplicate", "evaluate", "filter", "backtest", "realtime"):
            STEPS[name]()
        return 0

    STEPS[args.step]()
    return 0


if __name__ == "__main__":
    sys.exit(main())
