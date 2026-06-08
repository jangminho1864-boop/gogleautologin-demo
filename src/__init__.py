"""google-login-automation 패키지 공개 API."""

from .config import Settings, detect_chrome_user_data_dir
from .exceptions import (
    GoogleAutomationError,
    NotLoggedInError,
    ProfileLockedError,
)
from .google_session import AccountInfo, GoogleSession
from .profile_manager import ProfileManager

__all__ = [
    "Settings",
    "detect_chrome_user_data_dir",
    "GoogleSession",
    "AccountInfo",
    "ProfileManager",
    "GoogleAutomationError",
    "NotLoggedInError",
    "ProfileLockedError",
]
