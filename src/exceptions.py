"""프로젝트 전용 예외 정의."""

from __future__ import annotations


class GoogleAutomationError(Exception):
    """본 패키지의 모든 예외의 기반 클래스."""


class ProfileLockedError(GoogleAutomationError):
    """대상 프로필이 다른 Chrome 인스턴스에 의해 잠겨 있을 때.

    평소 사용하는 Chrome이 같은 프로필을 열어둔 채로 자동화를 실행하면 발생한다.
    실제 Chrome을 모두 종료하거나, 전용/복제 프로필을 사용하면 해결된다.
    """


class NotLoggedInError(GoogleAutomationError):
    """대상 프로필/계정이 로그인되어 있지 않을 때.

    setup_profile.py 로 최초 1회 수동 로그인을 마쳐야 한다.
    """
