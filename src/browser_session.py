"""
브라우저 세션 (사이트 비종속)
=============================

Chrome 프로필을 사용해 WebDriver 를 띄우고 종료하는 **범용** 계층.
특정 사이트(구글 등)에 대한 지식은 여기에 두지 않는다.

사이트별 자동화는 이 클래스를 상속해서 구현한다::

    class MySiteSession(BrowserSession):
        def do_something(self) -> None:
            driver = self._require_driver()
            driver.get("https://example.com/")
            self._wait_url_contains(driver, "example.com", 10)

이렇게 분리하면 사이트별 로직이 서로 격리되어, 한 사이트의 위험한 동작이
다른 사이트 자동화에 섞이지 않는다.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait

from .config import Settings
from .profile_manager import ProfileManager

if TYPE_CHECKING:
    # typing.Self 는 3.11+ 이므로 Python 3.9 에서는 typing_extensions 를 쓴다.
    # 단 typing_extensions 는 런타임 의존성이 아니므로 TYPE_CHECKING 으로 가둔다
    # (`from __future__ import annotations` 덕분에 애노테이션은 지연 평가된다).
    from typing_extensions import Self

logger = logging.getLogger(__name__)


class BrowserSession:
    """Chrome 프로필 기반 브라우저 세션의 공통 기반 클래스."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()
        self.profiles = ProfileManager(self.settings)
        self.driver: webdriver.Chrome | None = None

    # --- 컨텍스트 매니저 -------------------------------------------------
    def __enter__(self) -> Self:
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.quit()

    # --- 라이프사이클 ----------------------------------------------------
    def build_options(self) -> Options:
        """Chrome 실행 옵션을 만든다. 하위 클래스에서 확장할 수 있다."""
        options = Options()
        options.add_argument(f"--user-data-dir={self.settings.user_data_dir}")
        options.add_argument(f"--profile-directory={self.settings.profile_directory}")
        if self.settings.headless:
            options.add_argument("--headless=new")
        # 주의: excludeSwitches/useAutomationExtension 실험 옵션은 일부 실제 프로필에서
        # DevToolsActivePort 구동 실패를 유발해 넣지 않는다.
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")

        # CI/컨테이너 헤드리스 환경 보정: 러너에서 헤드리스 Chrome이
        # /dev/shm(64MB)·샌드박스 문제로 'session not created'로 죽는 것을 막는다.
        # GLA_CHROME_EXTRA_ARGS 에 공백 구분으로 지정
        # (예: "--no-sandbox --disable-dev-shm-usage").
        extra = os.environ.get("GLA_CHROME_EXTRA_ARGS", "").strip()
        if extra:
            for arg in extra.split():
                options.add_argument(arg)
        return options

    def start(self) -> webdriver.Chrome:
        """프로필을 검증하고 Chrome WebDriver 를 띄운다.

        start() 는 한 번만 호출한다. 같은 프로필로 두 번 띄우면 프로필 잠금이
        충돌해 'Chrome instance exited' 로 실패한다.
        """
        if self.driver is not None:
            raise RuntimeError(
                "이미 시작된 세션입니다. start() 를 두 번 호출하면 같은 프로필로 "
                "Chrome 이 이중 기동되어 실패합니다."
            )
        self.profiles.ensure_ready()

        # Selenium 4.6+ 는 Selenium Manager가 드라이버를 자동 관리(별도 설치 불필요).
        self.driver = webdriver.Chrome(options=self.build_options())
        self.driver.set_page_load_timeout(self.settings.page_load_timeout)
        logger.info("Chrome 세션 시작 (headless=%s)", self.settings.headless)
        return self.driver

    def quit(self) -> None:
        if self.driver is not None:
            self.driver.quit()
            self.driver = None
            logger.info("Chrome 세션 종료")

    # --- 공통 유틸 -------------------------------------------------------
    def _require_driver(self) -> webdriver.Chrome:
        if self.driver is None:
            raise RuntimeError("세션이 시작되지 않았습니다. start() 를 먼저 호출하세요.")
        return self.driver

    @staticmethod
    def _wait_url_contains(driver: webdriver.Chrome, needle: str, timeout: int) -> None:
        """현재 URL 에 needle 이 포함될 때까지 대기한다.

        until 의 람다 인자 대신 바깥의 driver 를 참조한다(같은 객체). selenium 4.41+
        에서 WebDriverWait 가 제네릭이 되면서 람다 인자가 미해결 TypeVar 로 추론돼
        mypy 가 current_url 접근을 인식하지 못하기 때문이다.
        """
        WebDriverWait(driver, timeout).until(
            lambda _: needle in (driver.current_url or "")
        )

    def screenshot(self, path: str) -> str:
        """현재 화면을 캡처해 저장한다."""
        driver = self._require_driver()
        driver.save_screenshot(path)
        logger.info("스크린샷 저장: %s", path)
        return path
