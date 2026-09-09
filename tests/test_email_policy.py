"""is_loginable_email 정책 단위 테스트 (Google 미접속, 순수 로직)."""

from __future__ import annotations

import pytest

from src.google_session import is_loginable_email


@pytest.mark.parametrize(
    "email",
    [
        "user@gmail.com",
        "USER@Gmail.com",     # 대소문자 무시
        "a.b+tag@gmail.com ",  # 후행 공백 허용
    ],
)
def test_gmail_accounts_allowed(email: str) -> None:
    assert is_loginable_email(email) is True


@pytest.mark.parametrize(
    "email",
    [
        None,
        "",
        "not-an-email",
        "user@googlemail.com",   # 별칭 도메인은 정책상 제외
        "user@company.com",      # Workspace/기업
        "user@gmail.co",
        "@gmail.com",
    ],
)
def test_non_gmail_rejected(email) -> None:
    assert is_loginable_email(email) is False
