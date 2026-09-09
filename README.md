# 구글 로그인 자동화 (Selenium / Playwright)

크롬 프로필에 저장된 **구글 계정 세션을 재사용**해, 비밀번호 자동 입력 없이
원하는 계정으로 자동 로그인·진입하는 자동화 프로젝트.

## 왜 이 방식인가 (설계 핵심)

구글은 봇 탐지가 강력해서, Selenium/Playwright로 로그인 화면에 ID·비밀번호를
자동 입력하면 대부분 **"이 브라우저 또는 앱은 보안 요건을 충족하지 않을 수 있습니다"**
로 차단된다. 이 차단은 *비밀번호를 입력하는 로그인 행위* 단계에서 발생한다.

본 프로젝트는 그 단계를 **건너뛴다.** 이미 로그인된 Chrome 프로필을 그대로 띄우면
세션 쿠키가 유효하므로 로그인 과정 자체가 일어나지 않고, 따라서 봇 차단 로직도
만나지 않는다. 멀티 계정은 구글의 `authuser` 인덱스(`/mail/u/0/`, `/u/1/`...)로
선택한다.

## 구조

```
google-login-automation/
├── main.py                 # 데모 실행: 계정 탐색 → 진입 → 검증 → 스크린샷
├── setup_profile.py        # 최초 1회 수동 로그인 헬퍼
├── playwright_variant.py   # [보너스] 동일 전략의 Playwright 구현
├── requirements.txt
└── src/
    ├── config.py           # 설정 + OS별 실제 크롬 경로 탐지
    ├── profile_manager.py  # 프로필 잠금 감지 / 경로 준비
    ├── google_session.py   # 핵심: 세션 시작·계정 선택·로그인 검증·계정 탐색
    └── exceptions.py
```

## 설치

```bash
pip install -r requirements.txt
# Selenium 4.6+ 는 드라이버를 자동 관리하므로 별도 ChromeDriver 설치 불필요.
```

## 사용법

```bash
# main.py 는 실제 Chrome 프로필(C드라이브 User Data)을 직접 사용한다.
# 먼저 평소 쓰는 Chrome 을 모두 종료한 뒤 실행할 것.
python main.py                # authuser=0 계정으로 진입
python main.py --authuser 1   # 두 번째 계정
python main.py --list         # 로그인된 계정 목록만 출력
python main.py --headless     # 화면 없이 실행
python main.py --profile "Profile 1"   # 다른 프로필 폴더 사용

# 전용 프로필 사용(기본 프로필은 Chrome이 자동화를 차단하므로 권장 경로)
python main.py --user-data-dir ".chrome-profile"

# 시나리오 A: 로그인된 계정들 사이 세션 전환이 정상 반영되는지 검증
python main.py --user-data-dir ".chrome-profile" --verify-switch
# 전환 방식 선택: url(기본, 안정) / click(우상단 아바타 클릭 → 폴백 url)
python main.py --user-data-dir ".chrome-profile" --verify-switch --switch-mode click

# 시나리오 B: 로그아웃된 계정 로그인(수동 유도, @gmail.com 만 허용)
python main.py --user-data-dir ".chrome-profile" --login-logged-out

# 즉시 전환(1안): 실행 직후 Gmail 없이 N번 계정으로 전환(중립 엔드포인트, ~1초)
python main.py --user-data-dir ".chrome-profile" --switch-to 2
```

> **계정 정책**: 로그인 시나리오는 **`@gmail.com` 개인 계정만** 허용한다.
> 비-gmail(기업/Workspace 등) 계정은 보안 이슈로 진행하지 않고 제외한다.
> 로그인은 페이지만 자동으로 열고 **실제 입력은 사용자가 수동**으로 한다(봇 탐지 회피).

> 실행 정책: 실제 Chrome 프로필을 **우선** 사용하며, 프로필을 못 찾거나/잠겨
> 있거나/로그인된 계정이 없으면 **재시도 없이 즉시 종료**한다.
>
> `setup_profile.py` 는 자동화 전용 프로필에 직접 로그인해 두는 보조 헬퍼다(선택).

## 주의할 함정 3가지

1. **프로필 잠금** — 평소 쓰는 Chrome이 같은 프로필을 열어두면 자동화가 실행되지
   않는다. 실행 전 Chrome 을 모두 종료할 것.
   (`ProfileManager` 가 잠금을 사전 감지해 명확한 에러를 던진다.)
2. **계정 선택** — account chooser를 클릭으로 처리하면 재인증 프롬프트가 뜰 수 있어,
   URL의 `authuser` 인덱스로 지정하는 편이 안정적이다.
3. **세션 만료** — 세션은 영구적이지 않다. 며칠~몇 주 뒤 재로그인이 필요할 수 있어,
   `is_logged_in()` 으로 상태를 먼저 확인한다.

## 포트폴리오 어필 포인트

- "비밀번호를 매크로로 입력"이 아니라 **브라우저 세션/쿠키 재사용으로 인증 단계를
  우회 설계**했다 → 구글 봇 탐지 메커니즘을 이해했다는 시그널.
- `authuser` 기반 **멀티 계정 제어**, 프로필 **잠금 감지** 등 실무에서
  실제로 부딪히는 엣지케이스를 핸들링.
- 컨텍스트 매니저, 타입 힌트, 예외 계층, 로깅 등 **유지보수 가능한 코드 구조**.
- 동일 전략을 Selenium / Playwright 두 스택으로 구현해 **도구 비종속적 설계** 입증.

## 한계 / 다음 단계 (2차 개발 후보)

- 2단계 인증(2FA)은 최초 수동 로그인에서 한 번만 통과하면 이후 세션 재사용으로 커버됨.
- 운영 환경이라면 세션 만료 자동 감지·재로그인 트리거, 헤드리스 안정화, 컨테이너화 고려.
- 정식 데이터 연동이 목적이면 UI 자동화 대신 **OAuth 2.0 / Google API** 로 전환하는
  것이 가장 견고함.
```
