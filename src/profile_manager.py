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
from pathlib import Path

from .config import Settings
from .exceptions import ProfileLockedError

logger = logging.getLogger(__name__)

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
                    f"실행 중인 Chrome을 모두 종료한 뒤 다시 시도하세요."
                )
