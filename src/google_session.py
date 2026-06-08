"""
구글 세션 모듈 (핵심 로직)
==========================

이미 로그인된 Chrome 프로필을 띄워, 비밀번호 입력 없이 구글 계정 세션을 재사용한다.
- authuser 인덱스로 여러 계정 중 원하는 계정 선택
- 로그인 여부를 URL 리다이렉트로 robust 하게 판별
- 프로필에 살아있는 계정 목록 자동 탐색
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .config import Settings
from .exceptions import NotLoggedInError
from .profile_manager import ProfileManager

logger = logging.getLogger(__name__)

# 로그인 안 된 상태에서 구글이 보내는 인증/계정선택/마케팅 페이지의 특징 문자열.
# 미로그인으로 mail.google.com 진입 시 구글은 accounts.google.com(로그인) 또는
# workspace.google.com/.../gmail(마케팅 랜딩)으로 리다이렉트한다.
_SIGNIN_MARKERS = (
    "accounts.google.com",
    "ServiceLogin",
    "signin",
    "AccountChooser",
    "workspace.google.com",
    "/intl/",
)


# 로그인 시나리오를 허용할 소비자(개인) 구글 계정 도메인.
# 그 외(@회사도메인 등 기업/Workspace 계정)는 보안 이슈로 로그인을 진행하지 않는다.
_CONSUMER_DOMAIN = "gmail.com"


def is_loginable_email(email: str | None) -> bool:
    """로그인 시나리오를 진행해도 되는 계정인지 판별한다.

    @gmail.com 개인 계정만 허용한다. 도메인을 알 수 없거나(@gmail.com 아님,
    기업/Workspace 포함) 비-gmail 이면 보안상 제외(False)한다.
    """
    if not email or "@" not in email:
        return False
    domain = email.rsplit("@", 1)[1].strip().lower()
    return domain == _CONSUMER_DOMAIN


@dataclass
class AccountInfo:
    """탐색된 계정 1건."""
    authuser: int
    email: str | None
    logged_in: bool


class GoogleSession:
    """프로필 기반 구글 세션 진입점.

    예시
    ----
    >>> with GoogleSession(Settings()) as gs:
    ...     accounts = gs.discover_accounts()
    ...     gs.open_account(authuser=0)
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()
        self.profiles = ProfileManager(self.settings)
        self.driver: webdriver.Chrome | None = None

    # --- 컨텍스트 매니저 -------------------------------------------------
    def __enter__(self) -> "GoogleSession":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.quit()

    # --- 라이프사이클 ----------------------------------------------------
    def start(self) -> webdriver.Chrome:
        """프로필을 검증하고 Chrome WebDriver를 띄운다."""
        self.profiles.ensure_ready()

        options = Options()
        options.add_argument(f"--user-data-dir={self.settings.user_data_dir}")
        options.add_argument(f"--profile-directory={self.settings.profile_directory}")
        if self.settings.headless:
            options.add_argument("--headless=new")
        # 자동화 배너/일부 탐지 신호 완화(세션 재사용 방식에서는 보조적).
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        # Selenium 4.6+ 는 Selenium Manager가 드라이버를 자동 관리(별도 설치 불필요).
        self.driver = webdriver.Chrome(options=options)
        self.driver.set_page_load_timeout(self.settings.page_load_timeout)
        logger.info("Chrome 세션 시작 (headless=%s)", self.settings.headless)
        return self.driver

    def quit(self) -> None:
        if self.driver is not None:
            self.driver.quit()
            self.driver = None
            logger.info("Chrome 세션 종료")

    # --- 핵심 동작 -------------------------------------------------------
    def _require_driver(self) -> webdriver.Chrome:
        if self.driver is None:
            raise RuntimeError("세션이 시작되지 않았습니다. start() 를 먼저 호출하세요.")
        return self.driver

    def is_logged_in(self, authuser: int = 0) -> bool:
        """해당 authuser 계정이 로그인 상태인지 판별한다.

        로그인 행위를 흉내내지 않고, mail.google.com 진입 후 구글이 로그인/계정선택
        페이지로 리다이렉트하는지를 신호로 사용한다(가장 안정적인 판별 방식).
        """
        driver = self._require_driver()
        try:
            driver.get(f"https://mail.google.com/mail/u/{authuser}/")
            WebDriverWait(driver, 10).until(
                lambda d: d.current_url and "google.com" in d.current_url
            )
        except Exception:  # noqa: BLE001 - 로드/렌더러 타임아웃 등은 미로그인으로 간주
            return False

        url = driver.current_url or ""
        # 로그인된 경우에만 mail.google.com 에 그대로 머문다.
        # 미로그인 시에는 accounts/workspace 등 다른 호스트로 리다이렉트된다.
        logged_in = "mail.google.com" in url and not any(
            marker in url for marker in _SIGNIN_MARKERS
        )
        logger.debug("authuser=%s logged_in=%s url=%s", authuser, logged_in, url)
        return logged_in

    def open_account(self, authuser: int = 0, wait_inbox: bool = True) -> str:
        """지정한 authuser 계정의 Gmail을 연다. 미로그인 시 예외.

        Returns
        -------
        진입 후의 current_url.
        """
        if not self.is_logged_in(authuser):
            raise NotLoggedInError(
                f"authuser={authuser} 계정이 로그인되어 있지 않습니다. "
                f"setup_profile.py 로 최초 1회 로그인하세요."
            )
        driver = self._require_driver()
        if wait_inbox:
            try:
                WebDriverWait(driver, self.settings.page_load_timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='main']"))
                )
            except Exception:  # noqa: BLE001
                logger.warning("받은편지함 메인 영역 대기 타임아웃 (계속 진행)")
        logger.info("계정 진입 완료: authuser=%s", authuser)
        return driver.current_url or ""

    def discover_accounts(self) -> list[AccountInfo]:
        """프로필에 살아있는 계정을 authuser 0..N 까지 훑어 목록화한다.

        '크롬에 있는 구글 계정 목록 활용' 요구사항을 구현하는 부분.
        """
        results: list[AccountInfo] = []
        for idx in range(self.settings.account_probe_limit):
            logged_in = self.is_logged_in(idx)
            email = self._read_active_email() if logged_in else None
            results.append(AccountInfo(authuser=idx, email=email, logged_in=logged_in))
            if not logged_in and idx > 0:
                # 보통 인덱스는 연속적이라, 첫 빈 슬롯에서 멈춰도 무방.
                break
        active = [a for a in results if a.logged_in]
        logger.info("계정 탐색 결과: %d개 로그인됨", len(active))
        return results

    def _read_active_email(self) -> str | None:
        """현재 페이지에서 로그인된 계정 이메일을 best-effort 로 추출."""
        driver = self._require_driver()
        try:
            # Gmail 우상단 계정 버튼의 aria-label 에 이메일이 포함되는 경우가 많다.
            el = driver.find_element(By.CSS_SELECTOR, "a[aria-label*='@']")
            label = el.get_attribute("aria-label") or ""
            for token in label.replace("(", " ").replace(")", " ").split():
                if "@" in token:
                    return token.strip()
        except Exception:  # noqa: BLE001 - 추출 실패는 치명적이지 않음
            return None
        return None

    def switch_account(self, authuser: int) -> AccountInfo:
        """해당 authuser 로 세션을 전환하고, 전환이 실제로 반영됐는지 확인해 반환한다.

        '이미 로그인된 계정 사이를 전환할 때 정상 반영되는지' 검증용. 전환 후의
        로그인 상태와 활성 계정 이메일을 읽어 AccountInfo 로 돌려준다.
        """
        logged_in = self.is_logged_in(authuser)  # mail.google.com/u/{idx}/ 로 이동
        email = self._read_active_email() if logged_in else None
        logger.info(
            "세션 전환: authuser=%s logged_in=%s email=%s",
            authuser, logged_in, email or "-",
        )
        return AccountInfo(authuser=authuser, email=email, logged_in=logged_in)

    def read_logged_out_email(self, authuser: int) -> str | None:
        """로그아웃된 슬롯의 이메일을 계정 선택(account chooser)에서 best-effort 로 읽는다.

        로그아웃 상태에서도 구글은 '이전에 사용한 계정' 목록에 이메일을 노출하는
        경우가 많다. 도메인 기반 예외처리(@gmail.com 만 허용)를 위해 사용한다.
        """
        driver = self._require_driver()
        try:
            driver.get("https://accounts.google.com/AccountChooser")
            WebDriverWait(driver, 10).until(
                lambda d: d.current_url and "google.com" in d.current_url
            )
            for el in driver.find_elements(By.CSS_SELECTOR, "*[data-email]"):
                val = el.get_attribute("data-email")
                if val and "@" in val:
                    return val.strip()
            # data-email 이 없으면 본문 텍스트에서 이메일 패턴을 best-effort 로 탐색.
            m = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", driver.page_source or "")
            return m.group(0) if m else None
        except Exception:  # noqa: BLE001 - 읽기 실패는 치명적이지 않음(미상으로 처리)
            return None

    def open_login_page(self, authuser: int = 0) -> str:
        """로그아웃된 계정을 '사람이 직접' 로그인할 수 있도록 로그인 페이지를 연다.

        비밀번호 자동 입력은 하지 않는다(구글 봇 탐지/보안 회피). 페이지만 띄우고
        실제 로그인(2단계 인증 포함)은 사용자가 수행한다.
        """
        driver = self._require_driver()
        driver.get(f"https://accounts.google.com/AddSession?authuser={authuser}")
        logger.info("로그인 페이지 오픈: authuser=%s", authuser)
        return driver.current_url or ""

    def screenshot(self, path: str) -> str:
        """현재 화면을 캡처해 저장(데모 증빙용)."""
        driver = self._require_driver()
        driver.save_screenshot(path)
        logger.info("스크린샷 저장: %s", path)
        return path
