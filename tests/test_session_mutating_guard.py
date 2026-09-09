"""구글 '세션 변경' 엔드포인트 차단 테스트 (Chrome 미구동, 가짜 드라이버 사용).

AddSession / AccountChooser 는 브라우저의 멀티로그인 쿠키를 재작성하는
엔드포인트다. 실제 프로필에서 호출되면 로그인된 계정이 전부 로그아웃될 수
있으므로, on_real_profile=True 일 때는 호출 자체가 일어나면 안 된다.
"""

from __future__ import annotations

import pytest

from src.config import Settings
from src.exceptions import GoogleAutomationError
from src.google_session import GoogleSession


class FakeDriver:
    """네트워크 없이 driver.get 호출만 기록하는 스텁."""

    def __init__(self) -> None:
        self.visited: list[str] = []
        self.current_url = "https://accounts.google.com/AccountChooser"
        self.page_source = "<html>someone@gmail.com</html>"

    def get(self, url: str) -> None:
        self.visited.append(url)

    def find_elements(self, *a, **kw):
        return []


def _session(on_real_profile: bool) -> tuple[GoogleSession, FakeDriver]:
    gs = GoogleSession(Settings(on_real_profile=on_real_profile))
    drv = FakeDriver()
    gs.driver = drv  # type: ignore[assignment]
    return gs, drv


# --- 실제 프로필: 호출 자체가 차단되어야 한다 ---------------------------------

def test_account_chooser_not_visited_on_real_profile():
    gs, drv = _session(on_real_profile=True)

    assert gs.read_logged_out_email(1) is None
    assert drv.visited == []  # 어떤 URL도 방문하지 않아야 한다


def test_add_session_blocked_on_real_profile():
    gs, drv = _session(on_real_profile=True)

    with pytest.raises(GoogleAutomationError, match="AddSession"):
        gs.open_login_page(1)
    assert drv.visited == []


# --- 복제/전용 프로필: 기존 동작 유지 ------------------------------------------

def test_account_chooser_used_on_safe_profile():
    gs, drv = _session(on_real_profile=False)

    email = gs.read_logged_out_email(1)

    assert any("AccountChooser" in u for u in drv.visited)
    assert email == "someone@gmail.com"


def test_add_session_allowed_on_safe_profile():
    gs, drv = _session(on_real_profile=False)

    gs.open_login_page(2)

    assert any("AddSession?authuser=2" in u for u in drv.visited)


def test_default_settings_are_safe():
    """기본값은 '실제 프로필 아님'이어야 한다(명시적으로 켤 때만 위험 경로)."""
    assert Settings().on_real_profile is False
