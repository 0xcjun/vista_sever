"""Static checks on the Dockerfile.

Aliyun FC custom-container will happily run as root; we assert otherwise so a
regression doesn't silently roll back the non-root posture in a future edit.
"""

from __future__ import annotations

from pathlib import Path

DOCKERFILE = Path(__file__).resolve().parents[2] / "Dockerfile"


def test_dockerfile_declares_non_root_user() -> None:
    content = DOCKERFILE.read_text(encoding="utf-8")
    assert "USER vista" in content, "runtime stage must switch away from root"


def test_dockerfile_creates_dedicated_user_before_user_directive() -> None:
    content = DOCKERFILE.read_text(encoding="utf-8")
    # Order matters: useradd must appear before USER so the user exists.
    useradd_idx = content.find("useradd")
    user_idx = content.find("\nUSER ")
    assert useradd_idx != -1, "expected useradd line"
    assert user_idx != -1, "expected USER directive"
    assert useradd_idx < user_idx, "useradd must run before USER directive"


def test_dockerfile_sets_tmp_root_on_writable_path() -> None:
    content = DOCKERFILE.read_text(encoding="utf-8")
    # Non-root user can't write to /tmp if it's restricted; we point VISTA_FC_TMP_ROOT
    # at a directory we chown'd to the vista user.
    assert "VISTA_FC_TMP_ROOT=/tmp/vista-fc" in content
    assert "chown -R vista:vista" in content
