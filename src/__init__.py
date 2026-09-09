"""google-login-automation 패키지 공개 API."""

from .browser_session import BrowserSession
from .config import Settings, detect_chrome_user_data_dir
from .exceptions import (
    GoogleAutomationError,
    NotLoggedInError,
    ProfileLockedError,
)
from .google_session import AccountInfo, GoogleSession
from .profile_manager import ProfileManager, clone_profile

__all__ = [
    "AccountInfo",
    "BrowserSession",
    "GoogleAutomationError",
    "GoogleSession",
    "NotLoggedInError",
    "ProfileLockedError",
    "ProfileManager",
    "Settings",
    "clone_profile",
    "detect_chrome_user_data_dir",
]
