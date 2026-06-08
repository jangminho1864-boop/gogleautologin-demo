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

from src import (
    GoogleSession,
    NotLoggedInError,
    ProfileLockedError,
    Settings,
    detect_chrome_user_data_dir,
)
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


def _run_once(settings: Settings, args: argparse.Namespace) -> tuple[bool, bool]:
    """전용 프로필로 세션을 1회 실행한다.

    Returns
    -------
    (has_login, completed)
        has_login : 프로필에 로그인된 계정이 하나라도 있었는지 여부.
        completed : 요구한 작업(목록 출력 또는 계정 진입+스크린샷)을 끝냈는지 여부.
    """
    with GoogleSession(settings) as gs:
        # 1) 계정 목록 탐색
        accounts = gs.discover_accounts()
        print("\n[ 프로필 내 구글 계정 목록 ]")
        for a in accounts:
            state = "로그인됨" if a.logged_in else "비어있음/미로그인"
            email = a.email or "-"
            print(f"  authuser={a.authuser}  {state:14s}  {email}")

        has_login = any(a.logged_in for a in accounts)

        if args.list:
            return has_login, True

        if not has_login:
            # 로그인된 계정이 없으면 진입을 시도하지 않고 폴백 신호를 돌려준다.
            return False, False

        # 2) 지정 계정으로 진입 + 검증
        url = gs.open_account(authuser=args.authuser)
        print(f"\n진입 성공 → {url}")

        # 3) 증빙 스크린샷
        shot = gs.screenshot(f"demo_authuser_{args.authuser}.png")
        print(f"스크린샷 저장: {shot}")
        return True, True


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
        # 1차 시도: 전용 프로필(예: D드라이브 .chrome-profile)로 실행.
        has_login, completed = _run_once(settings, args)

        # 폴백: 전용 프로필에 로그인된 계정이 없고, 아직 실제 프로필을 복제하지
        #        않았다면 → 실제 Chrome 프로필(예: C드라이브 User Data)에 계정
        #        정보가 있는지 확인하고, 있으면 복제해서 다시 시도한다.
        if not has_login and not completed and not args.clone_real:
            real_dir = detect_chrome_user_data_dir()
            if real_dir is None:
                logger.warning(
                    "전용 프로필에 로그인된 계정이 없고, 실제 Chrome 프로필도 "
                    "찾지 못했습니다."
                )
                print("\n먼저 `python setup_profile.py` 로 로그인하세요.")
                return 3

            logger.info(
                "전용 프로필에 로그인된 계정이 없어 실제 Chrome 프로필을 확인합니다: %s",
                real_dir / args.profile,
            )
            try:
                ProfileManager.clone_real_profile(
                    target_user_data_dir=settings.user_data_dir,
                    profile_directory=args.profile,
                    source_user_data_dir=real_dir,
                )
            except FileNotFoundError as e:
                logger.error("실제 프로필 복제 실패: %s", e)
                print("\n먼저 `python setup_profile.py` 로 로그인하세요.")
                return 3

            logger.info("실제 프로필 복제 완료 → 재시도합니다.")
            has_login, completed = _run_once(settings, args)

        if not completed:
            logger.error("로그인된 구글 계정을 찾지 못했습니다.")
            print(
                "\n전용 프로필과 실제 Chrome 프로필 모두에서 로그인된 계정을 "
                "찾지 못했습니다.\n먼저 `python setup_profile.py` 로 로그인하세요."
            )
            return 3

    except ProfileLockedError as e:
        logger.error("프로필 잠금: %s", e)
        print(
            "\n실행 중인 Chrome을 모두 종료한 뒤 다시 시도하세요 "
            "(실제 프로필 복제 시 Chrome이 켜져 있으면 잠깁니다)."
        )
        return 2
    except NotLoggedInError as e:
        logger.error("미로그인: %s", e)
        print("\n먼저 `python setup_profile.py` 로 로그인하세요.")
        return 3

    return 0


if __name__ == "__main__":
    sys.exit(main())
