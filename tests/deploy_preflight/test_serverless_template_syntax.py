from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
SERVERLESS_TEMPLATES = [
    ROOT / "s.yaml",
    ROOT / "s.realtime-cron.yaml",
]
FDL_TEMPLATES = sorted((ROOT / "flows").glob("*.fdl"))


def _load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_serverless_templates_use_v3_env_function_syntax() -> None:
    old_env_syntax = re.compile(r"\$\{env\.[^}]+}")

    offenders = []
    for template in SERVERLESS_TEMPLATES:
        text = template.read_text(encoding="utf-8")
        for match in old_env_syntax.finditer(text):
            offenders.append(f"{template.relative_to(ROOT)}: {match.group(0)}")

    assert not offenders, (
        "Serverless Devs v3 does not resolve old ${env.NAME|default} syntax; "
        "use ${env('NAME', 'default')} instead:\n" + "\n".join(offenders)
    )


def test_included_fdl_files_do_not_use_runtime_template_variables() -> None:
    unsupported = re.compile(r"\$\{(?:context|env)\.[^}]+}")

    offenders = []
    for template in FDL_TEMPLATES:
        text = template.read_text(encoding="utf-8")
        for match in unsupported.finditer(text):
            offenders.append(f"{template.relative_to(ROOT)}: {match.group(0)}")

    assert not offenders, (
        "FDL files are included through s.yaml ${file(...)} and are parsed by "
        "Serverless Devs before FnF sees them; render deployment values with "
        "${vars.*} instead:\n" + "\n".join(offenders)
    )


def test_v3_serverless_template_does_not_embed_fnf_component() -> None:
    resources = _load_yaml(ROOT / "s.yaml").get("resources") or {}
    offenders = [
        name
        for name, resource in resources.items()
        if isinstance(resource, dict) and resource.get("component") == "fnf"
    ]

    assert not offenders, (
        "Serverless Devs v3.1.10 does not resolve component: fnf in s.yaml; "
        "deploy FnF through tests/deploy_preflight/09_deploy_flow.sh instead:\n" + "\n".join(offenders)
    )


def test_fc3_resources_use_flat_props_schema() -> None:
    offenders = []
    for template in SERVERLESS_TEMPLATES:
        resources = _load_yaml(template).get("resources") or {}
        for name, resource in resources.items():
            if not isinstance(resource, dict) or resource.get("component") != "fc3":
                continue
            props = resource.get("props") or {}
            if isinstance(props, dict) and "function" in props:
                offenders.append(f"{template.relative_to(ROOT)}: {name}")

    assert not offenders, (
        "fc3@0.1.17 expects functionName/runtime/customContainerConfig directly "
        "under props, not props.function:\n" + "\n".join(offenders)
    )
