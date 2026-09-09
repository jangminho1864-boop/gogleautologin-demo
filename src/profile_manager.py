"""
프로필 관리 모듈
================

자동화에서 사용할 Chrome 프로필을 안전하게 다룬다.

두 가지 책임
------------
1) 잠금(lock) 감지: 실행 중인 Chrome이 같은 프로필을 점유하면 자동화가 실패하므로
   사전에 감지해 명확한 에러를 던진다.
2) 프로필 경로 준비: 프로필 디렉터리를 사용할 수 있는 상태로 만든다.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from .config import Settings
from .exceptions import ProfileLockedError

logger = logging.getLogger(__name__)

# Chrome이 프로필을 점유 중일 때 만들어 두는 잠금 흔적들(OS별 상이).
_LOCK_HINTS = ("SingletonLock", "SingletonCookie", "lockfile")

# 복제 시 제외할 디렉터리(캐시류). 세션 재사용에 불필요하고 용량만 크다.
_CLONE_EXCLUDE = (
    "Cache", "Code Cache", "GPUCache", "DawnCache", "GraphiteDawnCache",
    "GrShaderCache", "ShaderCache", "Service Worker", "Application Cache",
    "Crashpad", "Local Traces", "component_crx_cache", "extensions_crx_cache",
)


def clone_profile(
    src_user_data: Path,
    dest_user_data: Path,
    profile_directory: str = "Default",
) -> Path:
    """실제 Chrome 프로필을 복제해 '안전한' 작업용 User Data 를 만든다.

    실제(라이브) 프로필을 자동화로 직접 구동하면 구글이 세션 바인딩 실패/자동화
    탐지로 판단해 **로그인된 계정이 전부 로그아웃**될 수 있다. 복제본에서 구동하면
    원본 세션은 건드리지 않는다.

    쿠키 복호화 키가 담긴 User Data 루트의 'Local State' 도 함께 복사해야
    복제본에서 세션이 살아있다.
    """
    src_profile = src_user_data / profile_directory
    if not src_profile.exists():
        raise FileNotFoundError(f"원본 프로필을 찾지 못했습니다: {src_profile}")

    if dest_user_data.exists():
        shutil.rmtree(dest_user_data, ignore_errors=True)
    dest_user_data.mkdir(parents=True, exist_ok=True)

    local_state = src_user_data / "Local State"
    if local_state.exists():
        shutil.copy2(local_state, dest_user_data / "Local State")

    try:
        shutil.copytree(
            src_profile,
            dest_user_data / profile_directory,
            ignore=shutil.ignore_patterns(*_CLONE_EXCLUDE),
            dirs_exist_ok=True,
            symlinks=True,
            ignore_dangling_symlinks=True,
        )
    except shutil.Error as exc:  # 일부 파일 복사 실패는 치명적이지 않다(캐시/소켓 등).
        logger.warning("복제 중 일부 파일을 건너뛰었습니다: %s", exc)

    logger.info("프로필 복제 완료: %s -> %s", src_profile, dest_user_data / profile_directory)
    return dest_user_data


class ProfileManager:
    """프로필 경로 준비 및 검증 담당."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def user_data_dir(self) -> Path:
        return self.settings.user_data_dir

    @property
    def profile_path(self) -> Path:
        """실제 프로필 폴더(User Data/<profile_directory>) 경로."""
        return self.user_data_dir / self.settings.profile_directory

    def ensure_ready(self) -> Path:
        """프로필을 사용할 수 있는 상태로 만들고 경로를 반환한다.

        - 디렉터리가 없으면 생성한다(전용 프로필 신규 케이스).
        - 잠겨 있으면 ProfileLockedError 를 던진다.
        """
        self.user_data_dir.mkdir(parents=True, exist_ok=True)
        self._assert_not_locked()
        logger.info("프로필 준비 완료: %s", self.profile_path)
        return self.user_data_dir

    def _assert_not_locked(self) -> None:
        for hint in _LOCK_HINTS:
            if (self.user_data_dir / hint).exists():
                raise ProfileLockedError(
                    f"프로필이 사용 중인 것으로 보입니다('{hint}' 감지). "
                    f"실행 중인 Chrome을 모두 종료한 뒤 다시 시도하세요."
                )
