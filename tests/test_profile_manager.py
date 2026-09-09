"""ProfileManager 잠금 감지 / 경로 준비 단위 테스트 (Google 미접속)."""

from __future__ import annotations

import pytest

from src.config import Settings
from src.exceptions import ProfileLockedError
from src.profile_manager import _LOCK_HINTS, ProfileManager


def _mgr(tmp_path) -> ProfileManager:
    return ProfileManager(Settings(user_data_dir=tmp_path / "ud", profile_directory="Default"))


def test_ensure_ready_creates_dir(tmp_path) -> None:
    mgr = _mgr(tmp_path)
    result = mgr.ensure_ready()
    assert result.exists()
    assert result == tmp_path / "ud"


def test_profile_path_composition(tmp_path) -> None:
    mgr = _mgr(tmp_path)
    assert mgr.profile_path == tmp_path / "ud" / "Default"


@pytest.mark.parametrize("hint", _LOCK_HINTS)
def test_lock_detected(tmp_path, hint) -> None:
    mgr = _mgr(tmp_path)
    (tmp_path / "ud").mkdir(parents=True)
    (tmp_path / "ud" / hint).touch()

    with pytest.raises(ProfileLockedError):
        mgr.ensure_ready()
