"""
[보너스] Playwright 버전
=========================

동일한 '프로필/세션 재사용' 전략을 Playwright 의 persistent context 로 구현한 예시.
Selenium 버전과 원리는 같다: 비밀번호를 입력하지 않고, 이미 로그인된 프로필을 띄운다.

설치/사용
---------
    pip install playwright
    playwright install chromium      # 또는 channel="chrome" 로 설치된 크롬 사용

    python playwright_variant.py --authuser 0
"""

from __future__ import annotations

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright

SIGNIN_MARKERS = ("accounts.google.com", "ServiceLogin", "signin", "AccountChooser")


def run(user_data_dir: Path, authuser: int, headless: bool) -> int:
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=headless,
            channel="chrome",  # 시스템에 설치된 Chrome 사용(없으면 이 줄 제거)
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(f"https://mail.google.com/mail/u/{authuser}/", wait_until="load")

        url = page.url
        logged_in = not any(m in url for m in SIGNIN_MARKERS)
        print(f"authuser={authuser}  logged_in={logged_in}\nURL: {url}")

        if logged_in:
            page.screenshot(path=f"demo_pw_authuser_{authuser}.png")
            print(f"스크린샷 저장: demo_pw_authuser_{authuser}.png")

        ctx.close()
        return 0 if logged_in else 3


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--authuser", type=int, default=0)
    ap.add_argument("--headless", action="store_true")
    ap.add_argument("--profile-dir", default=str(Path.cwd() / ".pw-profile"))
    args = ap.parse_args()
    return run(Path(args.profile_dir), args.authuser, args.headless)


if __name__ == "__main__":
    raise SystemExit(main())
