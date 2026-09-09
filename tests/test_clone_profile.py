"""clone_profile 단위 테스트 (실제 Chrome/구글 미사용, 가짜 프로필 트리로 검증)."""

from __future__ import annotations

import pytest

from src.profile_manager import clone_profile


def _fake_profile(root):
    """실제 Chrome User Data 구조를 흉내낸 트리를 만든다."""
    ud = root / "User Data"
    (ud / "Default" / "Cache").mkdir(parents=True)
    (ud / "Default" / "Network").mkdir(parents=True)
    (ud / "Local State").write_text("local-state")
    (ud / "Default" / "Cookies").write_text("cookie-db")
    (ud / "Default" / "Preferences").write_text("prefs")
    (ud / "Default" / "Cache" / "big.bin").write_text("x" * 1000)
    (ud / "Default" / "Network" / "Cookies").write_text("net-cookie")
    return ud


def test_clone_copies_session_files(tmp_path):
    src = _fake_profile(tmp_path)
    dest = tmp_path / "clone"

    clone_profile(src, dest, "Default")

    # 세션 재사용에 필요한 파일은 반드시 복사되어야 한다.
    assert (dest / "Local State").read_text() == "local-state"
    assert (dest / "Default" / "Cookies").read_text() == "cookie-db"
    assert (dest / "Default" / "Preferences").read_text() == "prefs"
    assert (dest / "Default" / "Network" / "Cookies").read_text() == "net-cookie"


def test_clone_excludes_cache(tmp_path):
    src = _fake_profile(tmp_path)
    dest = tmp_path / "clone"

    clone_profile(src, dest, "Default")

    # 캐시는 제외되어야 한다(용량 절감, 세션과 무관).
    assert not (dest / "Default" / "Cache").exists()


def test_clone_is_idempotent(tmp_path):
    src = _fake_profile(tmp_path)
    dest = tmp_path / "clone"

    clone_profile(src, dest, "Default")
    (dest / "Default" / "stale.txt").write_text("stale")
    clone_profile(src, dest, "Default")  # 재복제 시 이전 잔여물이 남지 않아야 한다

    assert not (dest / "Default" / "stale.txt").exists()
    assert (dest / "Default" / "Cookies").exists()


def test_clone_missing_source_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        clone_profile(tmp_path / "nope", tmp_path / "clone", "Default")


def test_clone_does_not_touch_source(tmp_path):
    """원본(실제 프로필)은 읽기만 하고 절대 변경되지 않아야 한다."""
    src = _fake_profile(tmp_path)
    before = sorted(p.relative_to(src).as_posix() for p in src.rglob("*"))

    clone_profile(src, tmp_path / "clone", "Default")

    after = sorted(p.relative_to(src).as_posix() for p in src.rglob("*"))
    assert before == after
    assert (src / "Default" / "Cookies").read_text() == "cookie-db"
