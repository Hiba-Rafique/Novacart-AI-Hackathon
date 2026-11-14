from pathlib import Path

from policyguard.config import _find_repo_root


def test_repo_root_supports_bundled_container_layout(tmp_path: Path) -> None:
    (tmp_path / "policies").mkdir()
    module = tmp_path / "src" / "policyguard" / "config.py"

    assert _find_repo_root(module) == tmp_path


def test_repo_root_supports_local_monorepo_layout(tmp_path: Path) -> None:
    (tmp_path / "policies").mkdir()
    module = tmp_path / "apps" / "api" / "src" / "policyguard" / "config.py"

    assert _find_repo_root(module) == tmp_path
