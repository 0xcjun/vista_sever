"""Smoke tests fixtures — talk to real Aliyun FC (requires ak/sk + deployed env)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess

import pytest

ENV_OPTIONS = ("dev", "prod")


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--env",
        choices=list(ENV_OPTIONS),
        default="dev",
        help="Target environment for smoke tests",
    )


@pytest.fixture(scope="session")
def smoke_env(request: pytest.FixtureRequest) -> str:
    if shutil.which("s") is None:
        pytest.skip("serverless-devs (`s`) CLI not installed")
    return str(request.config.getoption("--env"))


@pytest.fixture
def fc_invoke(smoke_env: str):
    def _invoke(function_name: str, event: dict, *, timeout: int = 120) -> dict:
        region = os.environ.get("FC_REGION", "cn-hangzhou")
        access = smoke_env
        proc = subprocess.run(
            [
                "s",
                "cli",
                "fc3",
                "invoke",
                "--region",
                region,
                "--function-name",
                function_name,
                "-e",
                json.dumps(event),
                "--access",
                access,
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        for line in proc.stdout.splitlines():
            s = line.strip()
            if s.startswith("{"):
                try:
                    return json.loads(s)
                except json.JSONDecodeError:
                    continue
        raise RuntimeError(f"no JSON found in invoke output:\n{proc.stdout}")

    return _invoke
