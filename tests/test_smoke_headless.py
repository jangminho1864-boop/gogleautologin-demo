"""헤드리스 Chrome 기동 스모크 (Google 미접속).

프로젝트 코드(GoogleSession.start)가 이 기기/러너에서 실제로 Chrome을
띄우고 정상 종료하는지만 검증한다. 임시 프로필을 쓰므로 로그인 계정은 0개이며,
google.com 등 외부 사이트에는 접속하지 않는다.

CI에서 Chrome이 없거나 기동 실패하면 스킵(xfail 아님)해 파이프라인을 막지 않는다.
`smoke` 마커로 선택 실행 가능: pytest -m smoke
"""

from __future__ import annotations

import pytest
from selenium.common.exceptions import WebDriverException

from src import GoogleSession, Settings


@pytest.mark.smoke
def test_headless_chrome_boots(tmp_path) -> None:
    settings = Settings(
        user_data_dir=tmp_path / "ud",
        profile_directory="Default",
        headless=True,
        account_probe_limit=1,
    )
    gs = GoogleSession(settings)
    try:
        driver = gs.start()  # start()는 1회만 호출한다(중복 호출 시 프로필 잠금 충돌).
        assert driver is not None
        # data: URL 로만 왕복 — 외부 네트워크/구글 미접속
        driver.get("data:text/html,<title>ok</title>")
        assert "ok" in driver.title
    except WebDriverException as exc:
        pytest.skip(f"이 환경에서 Chrome 기동 불가(러너에 Chrome 없음 등): {exc}")
    finally:
        gs.quit()
