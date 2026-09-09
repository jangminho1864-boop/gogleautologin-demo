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
    python main.py --clone-real-profile          # [권장] 복제본으로 안전하게 실행
    python main.py --clone-real-profile --list   # 계정 목록만 출력
    python main.py --user-data-dir ./work-profile  # 전용 프로필 사용
    python main.py --authuser 1 --clone-real-profile  # 두 번째 계정으로 진입

⚠ 실제 프로필 직접 사용 금지
    실제(라이브) Chrome 프로필을 자동화로 구동하면 구글이 세션 바인딩 실패/자동화로
    판단해 **로그인된 계정이 전부 로그아웃**될 수 있다. 그래서 명시적 옵트인
    (--use-real-profile) 없이는 실제 프로필로 실행되지 않도록 막아 두었다.
    안전한 방법은 --clone-real-profile 로 복제본에서 구동하는 것이다.

주의: 프로필 복제/사용 전 실행 중인 Chrome을 모두 종료해야 한다(프로필 잠금).
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from selenium.common.exceptions import WebDriverException

from src import (
    clone_profile,
    GoogleSession,
    NotLoggedInError,
    ProfileLockedError,
    Settings,
    detect_chrome_user_data_dir,
)
from src.google_session import is_loginable_email

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger("main")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="구글 로그인 자동화 데모 (실제 프로필 세션 재사용)")
    p.add_argument("--authuser", type=int, default=0, help="진입할 계정 인덱스 (기본 0)")
    p.add_argument("--list", action="store_true", help="로그인된 계정 목록만 출력")
    p.add_argument("--headless", action="store_true", help="헤드리스 모드로 실행")
    p.add_argument("--profile", default="Default", help="사용할 프로필 폴더명")
    p.add_argument("--user-data-dir", default=None,
                   help="사용할 User Data 경로. 지정하면 실제 Chrome 대신 전용 프로필 사용")
    p.add_argument("--verify-switch", action="store_true",
                   help="로그인된 계정들 사이 세션 전환이 정상 반영되는지 검증")
    p.add_argument("--switch-mode", choices=["url", "click"], default="url",
                   help="계정 전환 방식: url(기본,안정) / click(우상단 아바타 클릭)")
    p.add_argument("--login-logged-out", action="store_true",
                   help="로그아웃된 계정 로그인 시나리오(수동 로그인 유도, @gmail.com 만 허용)")
    p.add_argument("--switch-to", type=int, default=None, metavar="N",
                   help="실행 직후 Gmail 없이 중립 엔드포인트로 N번 계정으로 즉시 전환")
    p.add_argument("--clone-real-profile", action="store_true",
                   help="[권장] 실제 프로필을 복제해 복제본으로 실행. 원본 세션을 건드리지 않는다")
    p.add_argument("--use-real-profile", action="store_true",
                   help="[위험] 실제 Chrome 프로필을 직접 구동. 구글이 세션을 무효화해 "
                        "로그인된 계정이 전부 로그아웃될 수 있다")
    return p.parse_args()


def _scenario_verify_switch(
    gs: GoogleSession, logged_in_users: list[int], switch_mode: str = "url"
) -> int:
    """로그인된 계정들 사이를 차례로 전환하며 전환이 정상 반영되는지 검증한다.

    각 authuser 로 전환했을 때 (1) 로그인 상태가 유지되고 (2) 활성 계정 이메일이
    서로 겹치지 않으면(=인덱스별로 다른 계정이 활성화되면) 전환이 정상 반영된 것으로 본다.
    """
    print(f"\n[ 세션 전환 반영 검증 (mode={switch_mode}) ]")
    seen_emails: dict[str, int] = {}
    all_ok = True
    for u in logged_in_users:
        info = gs.switch_account(u, mode=switch_mode)
        problems = []
        if not info.logged_in:
            problems.append("전환 후 미로그인")
        if info.email and info.email in seen_emails:
            problems.append(f"authuser={seen_emails[info.email]} 와 동일 계정(전환 미반영 의심)")
        if info.email:
            seen_emails[info.email] = u
        mark = "OK" if not problems else "FAIL: " + ", ".join(problems)
        print(f"  authuser={u}  email={info.email or '-':30s}  [{mark}]")
        if problems:
            all_ok = False

    if all_ok:
        print("\n결과: 모든 계정 전환이 정상 반영되었습니다. ✅")
        return 0
    print("\n결과: 일부 계정 전환이 정상 반영되지 않았습니다. ❌")
    return 5


def _scenario_login_logged_out(gs: GoogleSession, accounts: list) -> int:
    """로그아웃된 계정에 대해 수동 로그인을 유도한다(@gmail.com 만 허용).

    비-gmail(기업/Workspace 등) 계정은 보안 이슈로 진행하지 않고 제외한다.
    실제 비밀번호 입력은 사용자가 직접 수행한다(봇 탐지/보안 회피).
    """
    logged_out = [a for a in accounts if not a.logged_in]
    if not logged_out:
        print("\n로그아웃된 계정이 없습니다.")
        return 0

    print("\n[ 로그아웃 계정 로그인 시나리오 (@gmail.com 만 허용) ]")
    any_done = False
    for a in logged_out:
        # 로그아웃 슬롯은 이메일이 비어있을 수 있어, 계정 선택 화면에서 best-effort 로 읽는다.
        email = a.email or gs.read_logged_out_email(a.authuser)

        if not is_loginable_email(email):
            logger.warning(
                "authuser=%s (%s): @gmail.com 계정이 아니므로 보안상 로그인 제외",
                a.authuser, email or "도메인 미상",
            )
            continue

        url = gs.open_login_page(a.authuser)
        any_done = True
        print(f"\n  authuser={a.authuser} ({email}) 로그인 페이지 오픈 → {url}")
        input("  브라우저에서 로그인(2단계 인증 포함)을 완료한 뒤 Enter 를 누르세요... ")

        info = gs.switch_account(a.authuser)
        mark = "OK" if info.logged_in else "FAIL(여전히 미로그인)"
        print(f"  로그인 결과: authuser={a.authuser} logged_in={info.logged_in} [{mark}]")

    if not any_done:
        print("\n진행 가능한(@gmail.com) 로그아웃 계정이 없습니다.")
    return 0


def main() -> int:
    args = parse_args()

    settings = Settings.from_env()
    settings.headless = args.headless or settings.headless
    settings.profile_directory = args.profile

    # 프로필(User Data) 결정 우선순위:
    #   1) --user-data-dir 인자  2) GLA_USER_DATA_DIR 환경변수(Settings.from_env)
    #   3) 실제 Chrome User Data(C드라이브) 자동 탐지
    if args.user_data_dir:
        # 상대경로는 Chrome 구동(DevToolsActivePort) 실패를 유발하므로 절대경로로 변환.
        settings.user_data_dir = Path(args.user_data_dir).expanduser().resolve()
    elif "GLA_USER_DATA_DIR" not in os.environ:
        real_dir = detect_chrome_user_data_dir()
        if real_dir is None:
            logger.error("실제 Chrome User Data 디렉터리를 찾지 못했습니다. (Chrome 미설치?)")
            return 3

        # 안전 가드: 실제(라이브) 프로필을 자동화로 직접 구동하면 구글이 세션 바인딩
        # 실패/자동화로 판단해 **로그인된 계정이 전부 로그아웃**될 수 있다.
        # 따라서 명시적 옵트인 없이는 실제 프로필을 쓰지 않는다.
        if args.clone_real_profile:
            dest = (Path.cwd() / ".chrome-profile-clone").resolve()
            logger.info("실제 프로필 복제 중(캐시 제외)... %s", dest)
            settings.user_data_dir = clone_profile(real_dir, dest, args.profile)
        elif args.use_real_profile:
            logger.warning(
                "실제 Chrome 프로필을 직접 사용합니다: %s\n"
                "  ⚠ 구글이 세션을 무효화해 로그인된 계정이 전부 로그아웃될 수 있습니다.\n"
                "  ⚠ 안전하게 쓰려면 --clone-real-profile 을 사용하세요.",
                real_dir,
            )
            settings.user_data_dir = real_dir
        else:
            logger.error(
                "실제 Chrome 프로필로의 자동 실행은 차단되어 있습니다.\n"
                "  실제 프로필을 자동화로 띄우면 구글 세션이 무효화되어\n"
                "  로그인된 계정이 전부 로그아웃될 수 있습니다.\n"
                "  다음 중 하나를 선택하세요:\n"
                "    --clone-real-profile   복제본으로 안전하게 실행 (권장)\n"
                "    --user-data-dir PATH   전용 프로필 사용\n"
                "    --use-real-profile     위험을 감수하고 실제 프로필 사용"
            )
            return 4
    logger.info("프로필 사용: %s", settings.user_data_dir / args.profile)

    try:
        with GoogleSession(settings) as gs:
            # --- 1안: 실행 직후 즉시 전환(Gmail 미경유) ---
            #     계정 전체 탐색 없이 바로 N번 계정으로 전환만 수행한다.
            if args.switch_to is not None:
                info = gs.switch_at_launch(args.switch_to)
                mark = "OK" if info.logged_in else "FAIL(미로그인/미반영)"
                print(f"\n즉시 전환 → authuser={info.authuser}  "
                      f"email={info.email or '-'}  [{mark}]")
                return 0 if info.logged_in else 3

            # 1) 계정 목록 탐색
            accounts = gs.discover_accounts()
            print("\n[ 프로필 내 구글 계정 목록 ]")
            for a in accounts:
                state = "로그인됨" if a.logged_in else "비어있음/미로그인"
                email = a.email or "-"
                print(f"  authuser={a.authuser}  {state:14s}  {email}")

            logged_in_users = [a.authuser for a in accounts if a.logged_in]

            # --- 시나리오 A: 로그아웃 계정 로그인(수동 유도, @gmail.com 만 허용) ---
            if args.login_logged_out:
                return _scenario_login_logged_out(gs, accounts)

            # 로그인된 계정이 하나도 없으면 가차없이 종료.
            if not logged_in_users:
                logger.error("로그인된 구글 계정이 없습니다. 종료합니다.")
                return 3

            # --- 시나리오 B: 세션 전환 반영 검증 ---
            if args.verify_switch:
                return _scenario_verify_switch(gs, logged_in_users, args.switch_mode)

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
