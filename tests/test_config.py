"""Settings / 프로필 경로 탐지 단위 테스트 (OS별 분기, Google 미접속)."""

from __future__ import annotations

from pathlib import Path

import pytest

from src import config
from src.config import Settings, detect_chrome_user_data_dir


@pytest.mark.parametrize(
    "platform, subpath",
    [
        ("darwin", "Library/Application Support/Google/Chrome"),
        ("linux", ".config/google-chrome"),
    ],
)
def test_detect_path_per_os(monkeypatch, tmp_path, platform, subpath) -> None:
    expected = tmp_path / subpath
    expected.mkdir(parents=True)
    monkeypatch.setattr(config.sys, "platform", platform)
    monkeypatch.setattr(config.Path, "home", classmethod(lambda cls: tmp_path))

    assert detect_chrome_user_data_dir() == expected


def test_detect_returns_none_when_missing(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(config.sys, "platform", "darwin")
    monkeypatch.setattr(config.Path, "home", classmethod(lambda cls: tmp_path))

    assert detect_chrome_user_data_dir() is None


def test_settings_from_env_overrides(monkeypatch) -> None:
    monkeypatch.setenv("GLA_USER_DATA_DIR", "/tmp/ud")
    monkeypatch.setenv("GLA_PROFILE_DIRECTORY", "Profile 1")
    monkeypatch.setenv("GLA_HEADLESS", "true")
    monkeypatch.setenv("GLA_PROBE_LIMIT", "3")

    s = Settings.from_env()

    assert s.user_data_dir == Path("/tmp/ud")
    assert s.profile_directory == "Profile 1"
    assert s.headless is True
    assert s.account_probe_limit == 3


def test_settings_defaults() -> None:
    s = Settings()
    assert s.profile_directory == "Default"
    assert s.headless is False
    assert s.account_probe_limit == 5
