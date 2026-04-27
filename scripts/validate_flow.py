#!/usr/bin/env python3
"""Static validation for FnF FDL files.

Runs BEFORE `s deploy` so authors get fast feedback on typos and broken refs.

Checks:
  1. YAML loadable
  2. required top-level keys: version, type, name, steps
  3. every task's resourceArn points to a known function name (loaded from s.yaml)
  4. every `goto` target is a step that exists in the flow
  5. every flow type=flow node references a real flow by name

Usage:
  uv run python scripts/validate_flow.py                 # defaults to flows/*.fdl
  uv run python scripts/validate_flow.py path/to/a.fdl   # specific file(s)

Exit 0 if clean, 1 if any file has errors.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
FLOWS_DIR = ROOT / "flows"


def _load_s_yaml() -> dict[str, Any]:
    with (ROOT / "s.yaml").open() as f:
        return yaml.safe_load(f)


def _strip_vars(s: str) -> str:
    return re.sub(r"\$\{[^}]+\}", "", s).strip()


def _fc_functions(s_yaml: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for _res_name, res in (s_yaml.get("resources") or {}).items():
        if not isinstance(res, dict):
            continue
        if res.get("component") != "fc3":
            continue
        props = res.get("props", {})
        fn = props.get("functionName") or props.get("function", {}).get("functionName", "")
        base = _strip_vars(str(fn))
        if base:
            names.add(base)
    return names


def _flow_names(s_yaml: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for _res_name, res in (s_yaml.get("resources") or {}).items():
        if not isinstance(res, dict):
            continue
        if res.get("component") != "fnf":
            continue
        fn = res.get("props", {}).get("name", "")
        base = _strip_vars(str(fn))
        if base:
            names.add(base)
    for path in FLOWS_DIR.glob("*.fdl"):
        try:
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            continue
        if isinstance(doc, dict) and doc.get("type") == "flow" and doc.get("name"):
            names.add(str(doc["name"]))
    return names


def _collect_step_names(doc: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for step in doc.get("steps", []) or []:
        if isinstance(step, dict) and step.get("name"):
            names.add(str(step["name"]))
    return names


def _check_step(
    step: dict[str, Any],
    *,
    filename: str,
    fc_functions: set[str],
    flow_names: set[str],
    step_names: set[str],
) -> list[str]:
    errs: list[str] = []
    step_type = step.get("type")
    name = step.get("name", "?")

    if step_type == "task":
        arn = str(step.get("resourceArn", ""))
        match = re.search(r"functions/([A-Za-z0-9_-]+)", arn)
        if match and match.group(1) not in fc_functions:
            errs.append(f"{filename}#{name}: unknown function {match.group(1)!r}")

    if step_type == "flow":
        fname = _strip_vars(str(step.get("flowName", "")))
        if fname and fname not in flow_names:
            errs.append(f"{filename}#{name}: unknown sub-flow {fname!r}")

    for c in step.get("catch", []) or []:
        if not isinstance(c, dict):
            continue
        goto = c.get("goto")
        if goto and str(goto) not in step_names:
            errs.append(f"{filename}#{name}: catch goto {goto!r} not a step name")

    return errs


def validate_file(path: Path, fc_functions: set[str], flow_names: set[str]) -> list[str]:
    try:
        with path.open() as f:
            doc = yaml.safe_load(f)
    except yaml.YAMLError as e:
        return [f"{path.name}: YAML error: {e}"]

    if not isinstance(doc, dict):
        return [f"{path.name}: top-level must be a mapping"]

    errs: list[str] = [
        f"{path.name}: missing top-level '{key}'" for key in ("version", "type", "name", "steps") if key not in doc
    ]

    step_names = _collect_step_names(doc)
    for step in doc.get("steps", []) or []:
        if not isinstance(step, dict):
            continue
        errs.extend(
            _check_step(
                step,
                filename=path.name,
                fc_functions=fc_functions,
                flow_names=flow_names,
                step_names=step_names,
            )
        )

    return errs


def main() -> int:
    s_yaml = _load_s_yaml()
    fc_functions = _fc_functions(s_yaml)
    flow_names = _flow_names(s_yaml)

    paths = [Path(p) for p in sys.argv[1:]] or sorted(FLOWS_DIR.glob("*.fdl"))
    all_errs: list[str] = []
    for p in paths:
        all_errs.extend(validate_file(p, fc_functions, flow_names))

    if all_errs:
        for e in all_errs:
            print(f"[flow-lint] {e}", file=sys.stderr)
        return 1
    print(f"[flow-lint] OK ({len(paths)} files, {len(fc_functions)} functions, {len(flow_names)} flows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
