"""
프로필 관리 모듈
================

자동화에서 사용할 Chrome 프로필을 안전하게 다룬다.

세 가지 책임
------------
1) 잠금(lock) 감지: 실행 중인 Chrome이 같은 프로필을 점유하면 자동화가 실패하므로
   사전에 감지해 명확한 에러를 던진다.
2) 전용 프로필 준비: 데모/포트폴리오용으로 깨끗한 별도 프로필을 만든다.
3) 안전한 복제: 사용자의 실제 Chrome 프로필을 '읽기 전용처럼' 다루기 위해, 원본을
   건드리지 않는 작업용 복제본을 만든다(원본 잠금·손상 방지).
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from .config import Settings, detect_chrome_user_data_dir
from .exceptions import ProfileLockedError

logger = logging.getLogger(__name__)

# 복제 시 건너뛸 대용량/불필요 디렉터리. 세션 쿠키 재사용에는 필요 없다.
_CLONE_IGNORE = shutil.ignore_patterns(
    "Cache", "Code Cache", "GPUCache", "Service Worker", "GrShaderCache",
    "ShaderCache", "Crashpad", "*.log", "*-journal",
)

# Chrome이 프로필을 점유 중일 때 만들어 두는 잠금 흔적들(OS별 상이).
_LOCK_HINTS = ("SingletonLock", "SingletonCookie", "lockfile")


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
                    f"실행 중인 Chrome을 모두 종료한 뒤 다시 시도하거나, "
                    f"clone_real_profile() 로 복제본을 사용하세요."
                )

    @staticmethod
    def clone_real_profile(
        target_user_data_dir: Path,
        profile_directory: str = "Default",
        source_user_data_dir: Path | None = None,
    ) -> Path:
        """실제 Chrome 프로필을 작업용 디렉터리로 안전 복제한다.

        원본을 직접 띄우면 (1) 평소 Chrome과 잠금 충돌이 나고 (2) 손상 위험이 있다.
        그래서 필요한 부분(선택 프로필 폴더 + Local State)만 복제해 자동화 전용으로 쓴다.

        Parameters
        ----------
        target_user_data_dir : 복제본을 둘 User Data 경로
        profile_directory    : 복제할 프로필 폴더명('Default', 'Profile 1' ...)
        source_user_data_dir : 원본 User Data 경로. None이면 OS 기본 위치 자동 탐지.

        Returns
        -------
        복제된 target_user_data_dir 경로.
        """
        src_root = source_user_data_dir or detect_chrome_user_data_dir()
        if src_root is None or not src_root.exists():
            raise FileNotFoundError(
                "실제 Chrome User Data 디렉터리를 찾지 못했습니다. "
                "source_user_data_dir 를 직접 지정하세요."
            )

        src_profile = src_root / profile_directory
        if not src_profile.exists():
            raise FileNotFoundError(f"프로필 폴더가 없습니다: {src_profile}")

        target_user_data_dir.mkdir(parents=True, exist_ok=True)

        # Local State: 프로필 메타·암호화 키 참조가 들어 있어 세션 복원에 필요.
        local_state = src_root / "Local State"
        if local_state.exists():
            shutil.copy2(local_state, target_user_data_dir / "Local State")

        dst_profile = target_user_data_dir / profile_directory
        if dst_profile.exists():
            shutil.rmtree(dst_profile)
        shutil.copytree(src_profile, dst_profile, ignore=_CLONE_IGNORE)

        logger.info("프로필 복제 완료: %s -> %s", src_profile, dst_profile)
        return target_user_data_dir
