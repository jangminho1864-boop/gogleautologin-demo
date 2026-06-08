"""
데모 실행 엔트리포인트
======================

실제 Chrome 프로필(C드라이브 User Data)을 직접 사용해 로그인 세션을 재사용한다.
프로필에 저장된 구글 계정 목록을 탐색하고, 원하는 계정으로 자동 진입한 뒤
로그인 상태를 검증하고 증빙 스크린샷을 남긴다.

동작 정책
---------
- 실제 Chrome 프로필을 **우선** 사용한다(쿠키가 그대로 살아있어 세션 재사용 가능).
- 프로필을 찾지 못하거나(미설치), 잠겨 있거나(Chrome 실행 중), 로그인된 계정이
  하나도 없으면 **재시도 없이 즉시 종료**한다.

사용법
------
    python main.py                # 첫 번째 계정(authuser=0)으로 진입
    python main.py --authuser 1   # 두 번째 계정으로 진입
    python main.py --list         # 로그인된 계정 목록만 출력
    python main.py --profile "Profile 1"   # 다른 프로필 폴더 사용

주의: 실제 Chrome 프로필은 Chrome이 실행 중이면 잠겨 있으므로, 먼저 Chrome을
모두 종료해야 한다.
"""

from __future__ import annotations

import argparse
import logging
import sys

from selenium.common.exceptions import WebDriverException

from src import (
    GoogleSession,
    NotLoggedInError,
    ProfileLockedError,
    Settings,
    detect_chrome_user_data_dir,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger("main")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="구글 로그인 자동화 데모 (실제 프로필 세션 재사용)")
    p.add_argument("--authuser", type=int, default=0, help="진입할 계정 인덱스 (기본 0)")
    p.add_argument("--list", action="store_true", help="로그인된 계정 목록만 출력")
    p.add_argument("--headless", action="store_true", help="헤드리스 모드로 실행")
    p.add_argument("--profile", default="Default", help="사용할 프로필 폴더명")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    # 실제 Chrome 프로필(C드라이브 User Data)을 우선 사용한다.
    real_dir = detect_chrome_user_data_dir()
    if real_dir is None:
        logger.error("실제 Chrome User Data 디렉터리를 찾지 못했습니다. (Chrome 미설치?)")
        return 3

    settings = Settings.from_env()
    settings.user_data_dir = real_dir
    settings.headless = args.headless or settings.headless
    settings.profile_directory = args.profile
    logger.info("실제 Chrome 프로필 사용: %s", real_dir / args.profile)

    try:
        with GoogleSession(settings) as gs:
            # 1) 계정 목록 탐색
            accounts = gs.discover_accounts()
            print("\n[ 프로필 내 구글 계정 목록 ]")
            for a in accounts:
                state = "로그인됨" if a.logged_in else "비어있음/미로그인"
                email = a.email or "-"
                print(f"  authuser={a.authuser}  {state:14s}  {email}")

            logged_in_users = [a.authuser for a in accounts if a.logged_in]

            # 로그인된 계정이 하나도 없으면 가차없이 종료.
            if not logged_in_users:
                logger.error("로그인된 구글 계정이 없습니다. 종료합니다.")
                return 3

            if args.list:
                return 0

            # 2) 로그아웃/미로그인 계정 예외처리:
            #    요청한 authuser가 로그인 상태가 아니면 진입을 건너뛰고,
            #    로그인된 계정 중 가장 앞선 것으로 자동 대체한다.
            target = args.authuser
            if target not in logged_in_users:
                fallback_user = logged_in_users[0]
                logger.warning(
                    "authuser=%s 계정은 로그아웃/미로그인 상태입니다. "
                    "테스트에서 제외하고 로그인된 authuser=%s 계정으로 진행합니다.",
                    target, fallback_user,
                )
                target = fallback_user

            # 3) 지정(또는 대체) 계정으로 진입 + 검증
            url = gs.open_account(authuser=target)
            print(f"\n진입 성공 → authuser={target} → {url}")

            # 4) 증빙 스크린샷
            shot = gs.screenshot(f"demo_authuser_{target}.png")
            print(f"스크린샷 저장: {shot}")

    except ProfileLockedError as e:
        logger.error("프로필 잠금: %s", e)
        print("\n실행 중인 Chrome을 모두 종료한 뒤 다시 시도하세요.")
        return 2
    except NotLoggedInError as e:
        logger.error("미로그인: %s", e)
        return 3
    except WebDriverException as e:
        # 실제 프로필로 Chrome 구동 실패(DevToolsActivePort 등) → 재시도 없이 종료.
        logger.error("Chrome 구동 실패: %s", str(e).splitlines()[0] if str(e) else e)
        print("\n실제 Chrome 프로필로 브라우저를 띄우지 못했습니다. "
              "실행 중인 Chrome을 모두 종료했는지 확인하세요. 종료합니다.")
        return 4

    return 0


if __name__ == "__main__":
    sys.exit(main())
