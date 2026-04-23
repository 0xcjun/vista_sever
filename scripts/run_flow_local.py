#!/usr/bin/env python3
"""本地 FnF 执行器 — 读 flows/*.fdl,把每个 task 当作 docker 起 handler,串成完整工作流。

用途: 在没有阿里云 FnF 的本地环境跑通 fdl,验证全链路 inputMappings/outputMappings
是否正确,以及每个 handler 之间的契约能对上。

支持子集:
  - step type: task | flow | foreach | succeed | fail
  - inputMappings/outputMappings: $.path 简单 JSONPath,以及 multi-line JSON 模板(含 $. 替换)
  - retry: 暂未实现(本地一次性失败,真 FnF 才有指数退避)
  - catch errors=["*"]: 触发 goto abort 步骤
  - 子流程通过 flowName 名字找 flows/*.fdl 加载

调用:
  uv run python scripts/run_flow_local.py flows/research_full.fdl tests/fixtures/events/research_full_input.json

依赖:
  - 镜像 :dev 已构建(scripts/build_image.sh --dev)
  - dev/compose.yaml 起的 MinIO 在跑
  - .env.local 配置好(handler 容器从这里读 OSS / LLM key 等)
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
FLOWS_DIR = ROOT / "flows"
IMAGE = "registry.cn-hangzhou.aliyuncs.com/vista/vista-fc-base:dev"
ENV_LOCAL = ROOT / ".env.local"

# 函数名 → handler 模块名
RESOURCE_RE = re.compile(r"functions/([A-Za-z0-9_-]+)")


def _ts() -> str:
    return time.strftime("%H:%M:%S")


def _log(msg: str) -> None:
    print(f"[{_ts()}] {msg}", flush=True)


def _resolve_path(expr: str, state: dict[str, Any]) -> Any:
    """$ → state 整体;$.a.b.c → 嵌套取值;非 $ 开头视为字面量"""
    if expr == "$":
        return state
    if not expr.startswith("$."):
        return expr
    cur: Any = state
    for k in expr[2:].split("."):
        if cur is None:
            return None
        if isinstance(cur, dict):
            cur = cur.get(k)
        else:
            return None
    return cur


def _resolve_template(text: str, state: dict[str, Any]) -> str:
    """把 text 里所有 $.path 替换为对应值的 JSON 字面量"""

    def repl(m: re.Match[str]) -> str:
        v = _resolve_path(m.group(0), state)
        return json.dumps(v, ensure_ascii=False)

    return re.sub(r"\$\.[A-Za-z_][A-Za-z0-9_.]*", repl, text)


def _resolve_source(source: str, state: dict[str, Any]) -> Any:
    s = source.strip()
    if s.startswith("{") or s.startswith("["):
        return json.loads(_resolve_template(s, state))
    return _resolve_path(s, state)


def _set_path(state: dict[str, Any], target: str, value: Any) -> None:
    if not target.startswith("$."):
        raise ValueError(f"target must start with $.: {target}")
    keys = target[2:].split(".")
    cur = state
    for k in keys[:-1]:
        cur = cur.setdefault(k, {})
    cur[keys[-1]] = value


def _apply_input_mappings(mappings: list[dict[str, str]], state: dict[str, Any]) -> dict[str, Any]:
    """按 inputMappings 构造 task 入参 dict (target 是 'tenant'/'payload' 等顶级 key)"""
    event: dict[str, Any] = {}
    for m in mappings or []:
        event[m["target"]] = _resolve_source(m["source"], state)
    return event


def _apply_output_mappings(mappings: list[dict[str, str]], response: Any, state: dict[str, Any]) -> None:
    """按 outputMappings 把 task 的响应写回 state。source 此时是相对 response 的 JSONPath"""
    for m in mappings or []:
        v = _resolve_source(m["source"], response)
        _set_path(state, m["target"], v)


def _docker_invoke(handler: str, event: dict[str, Any], port: int, timeout_s: int) -> dict[str, Any]:
    """启容器,POST /invoke,收响应,清理。返回响应 JSON"""
    name = f"vistaFlow-{handler}-{uuid.uuid4().hex[:8]}"
    # rewrite env
    env_text = ENV_LOCAL.read_text()
    env_text = re.sub(
        r"(=https?://)(localhost|127\.0\.0\.1)([:/]|$)",
        r"\1host.docker.internal\3",
        env_text,
        flags=re.MULTILINE,
    )
    env_file = Path(f"/tmp/vista_flow_env.{uuid.uuid4().hex[:8]}")
    env_file.write_text(env_text)

    event_str = json.dumps(event, ensure_ascii=False)
    try:
        run_args = [
            "docker",
            "run",
            "-d",
            "--rm",
            "--name",
            name,
            "--env-file",
            str(env_file),
            "--add-host=host.docker.internal:host-gateway",
            "-v",
            f"{ROOT}/src:/app/src:ro",
            "-v",
            f"{ROOT}/handlers:/app/handlers:ro",
        ]
        # 可选：用本机 vista 源码覆盖镜像里的 site-packages/vista(无需重建镜像即可验证 patch)
        vista_override = os.environ.get("VISTA_SRC_OVERRIDE")
        if vista_override:
            run_args.extend(
                [
                    "-v",
                    f"{vista_override}:/app/.venv/lib/python3.12/site-packages/vista:ro",
                ]
            )
        run_args.extend(
            [
                "-p",
                f"{port}:9000",
                IMAGE,
                f"handlers.{handler}:handler",
            ]
        )
        subprocess.run(run_args, check=True, capture_output=True)
        # health
        for _ in range(120):
            r = subprocess.run(
                ["curl", "-sf", f"http://localhost:{port}/health"],
                capture_output=True,
            )
            if r.returncode == 0:
                break
            time.sleep(0.25)
        else:
            raise RuntimeError(f"{name}: /health timeout")

        cp = subprocess.run(
            [
                "curl",
                "-s",
                "--max-time",
                str(timeout_s),
                "-X",
                "POST",
                "-H",
                "Content-Type: application/json",
                "--data-binary",
                event_str,
                f"http://localhost:{port}/invoke",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(cp.stdout)
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True)
        env_file.unlink(missing_ok=True)


def _strip_template_vars(s: str) -> str:
    return re.sub(r"\$\{[^}]+\}", "", s).strip()


def _load_flow(name: str) -> dict[str, Any]:
    path = FLOWS_DIR / f"{name.replace('-', '_')}.fdl"
    if not path.exists():
        raise FileNotFoundError(f"flow file not found for name {name!r}: {path}")
    with path.open() as f:
        return yaml.safe_load(f)


def _exec_steps(  # noqa: C901 — 顺序实现 FnF step types(task/flow/foreach/succeed/fail),拆开会失去线性可读性
    steps: list[dict[str, Any]], state: dict[str, Any], port_base: int = 9878
) -> dict[str, Any]:
    by_name = {s["name"]: s for s in steps if isinstance(s, dict)}
    i = 0
    while i < len(steps):
        step = steps[i]
        st_type = step.get("type")
        st_name = step.get("name", f"step_{i}")
        _log(f"▶ step={st_name} type={st_type}")

        if st_type == "succeed":
            # 输出最终 state 字段(根据 outputMappings 投影)
            final: dict[str, Any] = {}
            for m in step.get("outputMappings", []) or []:
                final[m["target"][2:]] = _resolve_source(m["source"], state)
            _log(f"✓ flow done; output keys = {list(final.keys())}")
            return final or state

        if st_type == "fail":
            err = state.get("error") or {}
            raise RuntimeError(f"flow aborted: code={err.get('code')} msg={err.get('message')}")

        if st_type == "task":
            arn = step.get("resourceArn", "")
            m_arn = RESOURCE_RE.search(arn)
            if not m_arn:
                raise ValueError(f"step {st_name}: bad resourceArn {arn!r}")
            fn = m_arn.group(1)
            handler = fn.replace("-", "_")
            event = _apply_input_mappings(step.get("inputMappings", []), state)
            timeout_s = int(step.get("timeoutSeconds", 600))
            _log(f"  → docker invoke handlers.{handler}:handler (timeout {timeout_s}s)")
            t0 = time.time()
            try:
                resp = _docker_invoke(handler, event, port=port_base, timeout_s=timeout_s)
            except Exception as e:
                _log(f"  ✗ invoke crashed: {e}")
                resp = {"status": "failed", "error": {"code": "INVOKE_CRASH", "message": str(e)}}
            elapsed = time.time() - t0
            status = resp.get("status")
            _log(f"  ← status={status} elapsed={elapsed:.1f}s")

            if status != "succeeded":
                # catch errors=["*"] → goto abort
                catches = step.get("catch", []) or []
                jumped = False
                for c in catches:
                    errs = c.get("errors") or []
                    if "*" in errs or (resp.get("error", {}).get("code") in errs):
                        goto = c.get("goto")
                        if goto and goto in by_name:
                            state["error"] = resp.get("error") or {"code": "UNKNOWN", "message": "no error info"}
                            i = steps.index(by_name[goto])
                            jumped = True
                            break
                if jumped:
                    continue
                raise RuntimeError(f"task {st_name} failed: {resp.get('error')}")

            _apply_output_mappings(step.get("outputMappings", []), resp, state)

        elif st_type == "flow":
            sub_name = _strip_template_vars(step.get("flowName", ""))
            sub_doc = _load_flow(sub_name)
            sub_state = _apply_input_mappings(step.get("inputMappings", []) or [], state)
            # 如果没指定 inputMappings,把当前 state 作为子流入参
            if not sub_state:
                sub_state = dict(state)
            _log(f"  ↪ sub-flow {sub_name}")
            sub_out = _exec_steps(sub_doc.get("steps", []), sub_state, port_base=port_base + 1)
            _apply_output_mappings(step.get("outputMappings", []), sub_out, state)

        elif st_type == "foreach":
            it = step["iterationMapping"]
            collection = _resolve_path(it["collection"], state) or []
            item_target = it["item"]  # e.g. "$.toml"
            item_key = item_target[2:]
            inner_steps = step.get("steps", [])
            for idx, item in enumerate(collection):
                _log(f"  ↻ foreach iter {idx + 1}/{len(collection)}")
                sub_state = dict(state)
                sub_state[item_key] = item
                _exec_steps(inner_steps, sub_state, port_base=port_base + 1)

        else:
            _log(f"  ! unknown step type {st_type}, skipping")

        i += 1
    return state


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: run_flow_local.py <flow.fdl> <input.json>", file=sys.stderr)
        return 2
    fdl_path = Path(sys.argv[1])
    input_path = Path(sys.argv[2])
    doc = yaml.safe_load(fdl_path.read_text())
    state = json.loads(input_path.read_text())
    _log(f"=== flow {doc.get('name')} from {fdl_path.name} ===")
    out = _exec_steps(doc.get("steps", []), state)
    print("\n=== final state ===")
    print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
