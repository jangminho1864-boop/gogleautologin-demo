"""실제 프로필 보호 가드 테스트.

실제 라이브 Chrome 프로필로 자동화를 돌리면 구글이 세션을 무효화해 로그인된
계정이 전부 로그아웃될 수 있다. 옵트인 없이는 그 경로로 진입하지 못해야 한다.

이 테스트는 Chrome 을 띄우지 않는다: 가드가 GoogleSession 생성 이전에
차단하는지를 검증하며, 만약 세션을 만들려 하면 즉시 실패시킨다.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

import main as main_mod


@pytest.fixture
def fake_real_profile(monkeypatch, tmp_path):
    """실제 Chrome 프로필이 존재하는 것처럼 위장하고, 세션 생성은 금지한다."""
    real = tmp_path / "RealChrome"
    (real / "Default").mkdir(parents=True)
    (real / "Local State").write_text("local-state")
    (real / "Default" / "Cookies").write_text("cookie-db")
    monkeypatch.setattr(main_mod, "detect_chrome_user_data_dir", lambda: real)
    monkeypatch.delenv("GLA_USER_DATA_DIR", raising=False)

    def _boom(*a, **kw):
        raise AssertionError("가드를 통과해 Chrome 세션을 생성하려 했습니다")

    monkeypatch.setattr(main_mod, "GoogleSession", _boom)
    return real


def _run(monkeypatch, argv):
    monkeypatch.setattr(sys, "argv", ["main.py", *argv])
    return main_mod.main()


def test_blocks_real_profile_without_optin(monkeypatch, fake_real_profile):
    """옵트인 플래그가 없으면 차단하고 종료코드 4를 반환해야 한다."""
    assert _run(monkeypatch, ["--list"]) == 4


def test_clone_flag_does_not_use_real_profile(monkeypatch, fake_real_profile, tmp_path):
    """--clone-real-profile 은 복제본을 만들고 원본을 그대로 둬야 한다."""
    monkeypatch.chdir(tmp_path)
    with pytest.raises(AssertionError):  # 복제까지 간 뒤 세션 생성 시도에서 멈춘다
        _run(monkeypatch, ["--list", "--clone-real-profile"])

    clone = Path(tmp_path) / ".chrome-profile-clone"
    assert (clone / "Default" / "Cookies").read_text() == "cookie-db"
    # 원본은 손대지 않았는지 확인
    assert (fake_real_profile / "Default" / "Cookies").read_text() == "cookie-db"


def test_explicit_optin_reaches_session(monkeypatch, fake_real_profile):
    """--use-real-profile 을 준 경우에만 실제 프로필 경로로 진행한다."""
    with pytest.raises(AssertionError):
        _run(monkeypatch, ["--list", "--use-real-profile"])


def test_user_data_dir_bypasses_guard(monkeypatch, tmp_path):
    """전용 프로필(--user-data-dir)은 가드와 무관하게 통과해야 한다."""
    monkeypatch.delenv("GLA_USER_DATA_DIR", raising=False)

    def _boom(*a, **kw):
        raise AssertionError("reached-session")

    monkeypatch.setattr(main_mod, "GoogleSession", _boom)
    with pytest.raises(AssertionError, match="reached-session"):
        _run(monkeypatch, ["--list", "--user-data-dir", str(tmp_path / "ud")])
