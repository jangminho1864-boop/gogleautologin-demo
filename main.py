"""
데모 실행 엔트리포인트
======================

프로필에 저장된 구글 계정 목록을 탐색하고, 원하는 계정으로 자동 진입한 뒤
로그인 상태를 검증하고 증빙 스크린샷을 남긴다.

사용법
------
    # 1) 최초 1회: 전용 프로필에 로그인
    python setup_profile.py

    # 2) 데모 실행
    python main.py                # 첫 번째 계정(authuser=0)으로 진입
    python main.py --authuser 1   # 두 번째 계정으로 진입
    python main.py --list         # 로그인된 계정 목록만 출력

실제 Chrome 프로필을 복제해 쓰고 싶다면:
    python main.py --clone-real --profile "Default"
"""

from __future__ import annotations

import argparse
import logging
import sys

from src import GoogleSession, NotLoggedInError, ProfileLockedError, Settings
from src.profile_manager import ProfileManager

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger("main")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="구글 로그인 자동화 데모 (세션 재사용 방식)")
    p.add_argument("--authuser", type=int, default=0, help="진입할 계정 인덱스 (기본 0)")
    p.add_argument("--list", action="store_true", help="로그인된 계정 목록만 출력")
    p.add_argument("--headless", action="store_true", help="헤드리스 모드로 실행")
    p.add_argument("--clone-real", action="store_true",
                   help="실제 Chrome 프로필을 복제해 사용")
    p.add_argument("--profile", default="Default", help="복제할 프로필 폴더명")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    settings = Settings.from_env()
    settings.headless = args.headless or settings.headless
    settings.profile_directory = args.profile

    if args.clone_real:
        logger.info("실제 Chrome 프로필 복제 중...")
        ProfileManager.clone_real_profile(
            target_user_data_dir=settings.user_data_dir,
            profile_directory=args.profile,
        )

    try:
        with GoogleSession(settings) as gs:
            # 1) 계정 목록 탐색
            accounts = gs.discover_accounts()
            print("\n[ 프로필 내 구글 계정 목록 ]")
            for a in accounts:
                state = "로그인됨" if a.logged_in else "비어있음/미로그인"
                email = a.email or "-"
                print(f"  authuser={a.authuser}  {state:14s}  {email}")

            if args.list:
                return 0

            # 2) 지정 계정으로 진입 + 검증
            url = gs.open_account(authuser=args.authuser)
            print(f"\n진입 성공 → {url}")

            # 3) 증빙 스크린샷
            shot = gs.screenshot(f"demo_authuser_{args.authuser}.png")
            print(f"스크린샷 저장: {shot}")

    except ProfileLockedError as e:
        logger.error("프로필 잠금: %s", e)
        return 2
    except NotLoggedInError as e:
        logger.error("미로그인: %s", e)
        print("\n먼저 `python setup_profile.py` 로 로그인하세요.")
        return 3

    return 0


if __name__ == "__main__":
    sys.exit(main())
