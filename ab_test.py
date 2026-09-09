"""
A/B 계정 전환 방식 비교 벤치마크
================================

두 가지 '실행 직후 계정 전환' 방식을 동일 잣대(소요 시간 / 계정 반영 성공)로 측정한다.

- A안: 단일 프로필 + 시작 URL `?authuser=N`
        하나의 프로필을 띄운 뒤 google.com/?authuser=N 으로 전환(구글 페이지 1회 로드).
- B안: 계정별 분리된 크롬 프로필(`--profile-directory`)
        계정마다 별도 프로필을 즉시 시작(페이지 로드 없이 프로필 자체가 계정에 고정).

사용법
------
    # A안만 (이미 멀티 계정 로그인된 단일 프로필)
    python ab_test.py --mode a --user-data-dir .chrome-profile --authusers 0,1,2,3

    # B안용 프로필 셋업(계정별 1회 수동 로그인) — 브라우저가 뜨면 로그인 후 닫기
    python ab_test.py --setup-b "Profile 1" --user-data-dir .ab-profiles

    # B안만 (분리 프로필들)
    python ab_test.py --mode b --user-data-dir .ab-profiles

    # A/B 동시 비교
    python ab_test.py --mode both --user-data-dir .chrome-profile
"""
from __future__ import annotations

import argparse
import re
import subprocess
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def _base_options(user_data_dir: Path, profile_directory: str) -> Options:
    o = Options()
    o.add_argument(f"--user-data-dir={user_data_dir.resolve()}")
    o.add_argument(f"--profile-directory={profile_directory}")
    o.add_argument("--no-first-run")
    o.add_argument("--no-default-browser-check")
    return o


def _active_email(driver) -> str | None:
    m = _EMAIL_RE.search(driver.page_source or "")
    return m.group(0) if m else None


def _detect_chrome() -> str | None:
    for p in (
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ):
        if Path(p).exists():
            return p
    return None


def measure_a(user_data_dir: Path, authusers: list[int]) -> list[dict]:
    """A안: 단일 프로필 + 시작 URL ?authuser=N 전환 시간 측정."""
    print("\n[ A안: 단일 프로필 + 시작 URL ?authuser=N ]")
    rows: list[dict] = []
    o = _base_options(user_data_dir, "Default")
    driver = webdriver.Chrome(options=o)
    driver.set_page_load_timeout(30)
    try:
        for au in authusers:
            t0 = time.time()
            driver.get(f"https://www.google.com/?authuser={au}")
            WebDriverWait(driver, 15).until(
                lambda d: "google.com" in (d.current_url or "")
            )
            email = _active_email(driver)
            dt = time.time() - t0
            rows.append({"approach": "A", "key": f"authuser={au}", "email": email, "sec": round(dt, 2)})
            print(f"  authuser={au:<2} -> {email or '-':30s} {dt:5.2f}s")
    finally:
        driver.quit()
    return rows


def measure_b(user_data_dir: Path, profile_dirs: list[str]) -> list[dict]:
    """B안: 분리 프로필별 실행→계정 반영까지 시간 측정."""
    print("\n[ B안: 계정별 분리 프로필(--profile-directory) ]")
    rows: list[dict] = []
    for pd in profile_dirs:
        o = _base_options(user_data_dir, pd)
        t0 = time.time()
        driver = webdriver.Chrome(options=o)
        driver.set_page_load_timeout(30)
        try:
            # 프로필 자체가 계정에 고정. 확인을 위해 google.com 1회 로드.
            driver.get("https://www.google.com/")
            WebDriverWait(driver, 15).until(
                lambda d: "google.com" in (d.current_url or "")
            )
            email = _active_email(driver)
            dt = time.time() - t0
            rows.append({"approach": "B", "key": pd, "email": email, "sec": round(dt, 2)})
            print(f"  {pd:<12} -> {email or '-':30s} {dt:5.2f}s (실행+반영)")
        finally:
            driver.quit()
    return rows


def setup_b(user_data_dir: Path, profile_directory: str) -> None:
    """B안용 분리 프로필에 수동 로그인할 수 있도록 실제 크롬을 띄운다."""
    chrome = _detect_chrome()
    if not chrome:
        print("Chrome 실행파일을 찾지 못했습니다.")
        return
    user_data_dir.mkdir(parents=True, exist_ok=True)
    subprocess.Popen([
        chrome,
        f"--user-data-dir={user_data_dir.resolve()}",
        f"--profile-directory={profile_directory}",
        "--no-first-run",
        "--no-default-browser-check",
        "https://accounts.google.com/AddSession",
    ])
    print(f"프로필 '{profile_directory}' 로 크롬을 띄웠습니다. 로그인 후 창을 닫으세요.")
    print(f"경로: {user_data_dir.resolve() / profile_directory}")


def _discover_profiles(user_data_dir: Path) -> list[str]:
    if not user_data_dir.exists():
        return []
    found = []
    for p in sorted(user_data_dir.iterdir()):
        if p.is_dir() and (p.name == "Default" or p.name.startswith("Profile ")):
            found.append(p.name)
    return found


def _summary(rows: list[dict]) -> None:
    if not rows:
        return
    print("\n========== 비교 요약 ==========")
    print(f"{'방식':<4}{'대상':<14}{'계정':<30}{'시간(s)':>8}")
    for r in rows:
        print(f"{r['approach']:<4}{r['key']:<14}{r['email'] or '-':<30}{r['sec']:>8}")
    for ap in ("A", "B"):
        sub = [r["sec"] for r in rows if r["approach"] == ap]
        if sub:
            print(f"  → {ap}안 평균 {sum(sub)/len(sub):.2f}s (n={len(sub)})")


def main() -> int:
    ap = argparse.ArgumentParser(description="A/B 계정 전환 방식 비교 벤치마크")
    ap.add_argument("--mode", choices=["a", "b", "both"], default="both")
    ap.add_argument("--user-data-dir", default=".chrome-profile")
    ap.add_argument("--authusers", default="0,1,2,3", help="A안 측정할 authuser 목록(쉼표)")
    ap.add_argument("--profiles", default=None, help="B안 프로필 목록(쉼표). 미지정 시 자동 탐지")
    ap.add_argument("--setup-b", default=None, help="B안 프로필 수동 로그인 셋업(프로필명)")
    args = ap.parse_args()

    udir = Path(args.user_data_dir).expanduser()

    if args.setup_b:
        setup_b(udir, args.setup_b)
        return 0

    rows: list[dict] = []
    if args.mode in ("a", "both"):
        authusers = [int(x) for x in args.authusers.split(",") if x.strip() != ""]
        rows += measure_a(udir, authusers)

    if args.mode in ("b", "both"):
        profiles = (
            [p.strip() for p in args.profiles.split(",")]
            if args.profiles else _discover_profiles(udir)
        )
        if len(profiles) <= 1:
            print("\n[ B안 ] 분리 프로필이 부족합니다. 먼저 셋업하세요:")
            print('  python ab_test.py --setup-b "Profile 1" --user-data-dir .ab-profiles')
            print('  python ab_test.py --setup-b "Profile 2" --user-data-dir .ab-profiles')
        else:
            rows += measure_b(udir, profiles)

    _summary(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
