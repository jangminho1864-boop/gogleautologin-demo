"""
최초 1회 수동 로그인 헬퍼
=========================

자동화 전용 프로필에 구글 로그인을 '사람이 직접' 한 번 해두기 위한 스크립트.
이후 main.py 는 이 프로필의 세션을 재사용하므로, 다시 비밀번호를 입력할 필요가 없다.

사용법
------
    python setup_profile.py

브라우저가 뜨면 평소처럼 구글에 로그인(2단계 인증 포함)한 뒤,
터미널에서 Enter 를 누르면 세션이 프로필에 저장된 채로 종료된다.
"""

from __future__ import annotations

import logging

from src import GoogleSession, Settings

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")


def main() -> None:
    settings = Settings.from_env()
    settings.headless = False  # 수동 로그인은 반드시 화면 표시 모드.

    print("=" * 60)
    print(" 자동화 전용 프로필에 구글 로그인을 진행합니다.")
    print(f" 프로필 경로: {settings.user_data_dir}")
    print("=" * 60)

    session = GoogleSession(settings)
    driver = session.start()
    driver.get("https://accounts.google.com/")

    input(
        "\n브라우저에서 구글 로그인을 완료한 뒤(여러 계정 추가 가능),\n"
        "이 터미널에서 Enter 를 누르세요... "
    )
    session.quit()
    print("\n완료! 세션이 프로필에 저장되었습니다. 이제 main.py 를 실행하세요.")


if __name__ == "__main__":
    main()
