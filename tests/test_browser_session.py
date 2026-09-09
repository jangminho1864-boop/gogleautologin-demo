"""BrowserSession(사이트 비종속 기반 클래스) 단위 테스트 (Chrome 미구동)."""

from __future__ import annotations

import pytest

from src import BrowserSession, GoogleSession
from src.config import Settings


def _settings(tmp_path, **kw) -> Settings:
    return Settings(user_data_dir=tmp_path / "ud", profile_directory="Default", **kw)


def test_google_session_is_a_browser_session():
    """구글 전용 로직은 범용 계층 위에 얹혀 있어야 한다."""
    assert issubclass(GoogleSession, BrowserSession)


def test_require_driver_before_start(tmp_path):
    bs = BrowserSession(_settings(tmp_path))
    with pytest.raises(RuntimeError, match="시작되지 않았습니다"):
        bs._require_driver()


def test_start_twice_is_rejected(tmp_path):
    """같은 프로필로 두 번 띄우면 잠금 충돌로 죽으므로 미리 막아야 한다."""
    bs = BrowserSession(_settings(tmp_path))
    bs.driver = object()  # type: ignore[assignment]  # 기동된 것처럼 위장
    with pytest.raises(RuntimeError, match="이미 시작된 세션"):
        bs.start()


def test_quit_is_safe_when_not_started(tmp_path):
    BrowserSession(_settings(tmp_path)).quit()  # 예외 없이 no-op


# --- Chrome 옵션 빌드 (프로세스 기동 없음) ------------------------------------

def _args(session: BrowserSession) -> list[str]:
    return session.build_options().arguments


def test_options_include_profile_paths(tmp_path):
    args = _args(BrowserSession(_settings(tmp_path)))
    assert any(str(tmp_path / "ud") in a for a in args)
    assert any("--profile-directory=Default" in a for a in args)


def test_headless_flag_follows_settings(tmp_path):
    assert not any("--headless" in a for a in _args(BrowserSession(_settings(tmp_path))))
    on = _args(BrowserSession(_settings(tmp_path, headless=True)))
    assert any("--headless=new" in a for a in on)


def test_extra_args_from_env(tmp_path, monkeypatch):
    """CI 러너용 플래그를 환경변수로 주입할 수 있어야 한다."""
    monkeypatch.setenv("GLA_CHROME_EXTRA_ARGS", "--no-sandbox --disable-dev-shm-usage")
    args = _args(BrowserSession(_settings(tmp_path)))
    assert "--no-sandbox" in args
    assert "--disable-dev-shm-usage" in args


def test_no_extra_args_by_default(tmp_path, monkeypatch):
    monkeypatch.delenv("GLA_CHROME_EXTRA_ARGS", raising=False)
    assert "--no-sandbox" not in _args(BrowserSession(_settings(tmp_path)))


def test_subclass_can_extend_options(tmp_path):
    """다른 사이트 자동화가 옵션을 확장할 수 있어야 한다."""

    class MySite(BrowserSession):
        def build_options(self):
            options = super().build_options()
            options.add_argument("--lang=ko-KR")
            return options

    assert "--lang=ko-KR" in _args(MySite(_settings(tmp_path)))
