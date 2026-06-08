"""
설정 모듈
==========

자동화에 사용할 Chrome 프로필 경로, 계정 인덱스 등 환경 설정을 한곳에서 관리한다.

설계 의도
---------
구글 로그인 자동화에서 "비밀번호 자동 입력" 방식은 구글의 봇 탐지("이 브라우저 또는
앱은 보안 요건을 충족하지 않을 수 있습니다")에 막힌다. 본 프로젝트는 그 단계를 피하기
위해 **이미 로그인된 Chrome 프로필의 세션 쿠키를 재사용**한다. 따라서 핵심 설정은
"어느 프로필을 띄울 것인가"이다.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path


def detect_chrome_user_data_dir() -> Path | None:
    """현재 OS에서 실제 Chrome의 'User Data' 디렉터리를 추정해 반환한다.

    이 디렉터리 안에 'Default', 'Profile 1' 등 프로필별 폴더가 있고,
    각 프로필의 로그인 세션(쿠키)이 저장되어 있다.
    """
    home = Path.home()
    if sys.platform.startswith("win"):
        local = os.environ.get("LOCALAPPDATA")
        base = Path(local) if local else home / "AppData" / "Local"
        candidate = base / "Google" / "Chrome" / "User Data"
    elif sys.platform == "darwin":
        candidate = home / "Library" / "Application Support" / "Google" / "Chrome"
    else:  # linux 등
        candidate = home / ".config" / "google-chrome"

    return candidate if candidate.exists() else None


@dataclass
class Settings:
    """자동화 실행 설정.

    Attributes
    ----------
    user_data_dir:
        Chrome를 띄울 때 사용할 'User Data' 디렉터리.
        기본값은 프로젝트 내부의 전용 작업 폴더(.chrome-profile)이며, 실제 Chrome
        프로필을 그대로 쓰고 싶다면 detect_chrome_user_data_dir() 결과를 넣거나
        clone 기능으로 복제본을 만들어 지정한다.
    profile_directory:
        User Data 안에서 사용할 프로필 폴더명. 'Default', 'Profile 1' 등.
    headless:
        화면 없이 실행할지 여부. 구글 세션 재사용은 headful(False)에서 더 안정적이다.
    account_probe_limit:
        멀티 계정 탐색 시 authuser 인덱스를 0..N까지 몇 개나 확인할지.
    page_load_timeout:
        페이지 로드 대기 최대 초.
    """

    user_data_dir: Path = field(
        default_factory=lambda: Path.cwd() / ".chrome-profile"
    )
    profile_directory: str = "Default"
    headless: bool = False
    account_probe_limit: int = 5
    page_load_timeout: int = 30

    # 환경변수로 덮어쓸 수 있게 한다(클로드 코드/CI 환경에서 유용).
    @classmethod
    def from_env(cls) -> "Settings":
        s = cls()
        if v := os.environ.get("GLA_USER_DATA_DIR"):
            s.user_data_dir = Path(v).expanduser()
        if v := os.environ.get("GLA_PROFILE_DIRECTORY"):
            s.profile_directory = v
        if v := os.environ.get("GLA_HEADLESS"):
            s.headless = v.strip().lower() in {"1", "true", "yes", "on"}
        if v := os.environ.get("GLA_PROBE_LIMIT"):
            s.account_probe_limit = int(v)
        return s
