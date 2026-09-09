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
├── requirements.txt
├── src/
│   ├── config.py           # 설정 + OS별 실제 크롬 경로 탐지
│   ├── profile_manager.py  # 프로필 잠금 감지 / 경로 준비 / 프로필 복제
│   ├── browser_session.py  # 범용: 브라우저 기동·종료·대기·캡처 (사이트 비종속)
│   ├── google_session.py   # 구글 전용: 계정 선택·로그인 검증·계정 탐색
│   └── exceptions.py
├── tests/                  # 단위 테스트 + 헤드리스 스모크 (Python)
└── tests-e2e/              # Playwright E2E (사이트 자동화 개발/디버깅용, Node)
```

## 설치

```bash
pip install -r requirements.txt
# Selenium 4.6+ 는 드라이버를 자동 관리하므로 별도 ChromeDriver 설치 불필요.
```

## 사용법

> ⚠️ **실제(라이브) Chrome 프로필로는 실행되지 않는다.** 자동화로 실제 프로필을
> 띄우면 구글이 세션을 무효화해 **로그인된 계정이 전부 로그아웃**될 수 있어,
> 명시적 옵트인 없이는 차단된다(종료코드 4).

```bash
# [권장] 실제 프로필을 복제해 안전하게 실행 — 원본은 건드리지 않는다
python main.py --clone-real-profile --list
python main.py --clone-real-profile --authuser 1

# 전용 프로필 사용
python main.py --user-data-dir ".chrome-profile" --list

# [위험] 실제 프로필 직접 사용 — 로그아웃 위험을 감수할 때만
python main.py --use-real-profile --list

python main.py --headless     # 화면 없이 실행
python main.py --profile "Profile 1"   # 다른 프로필 폴더 사용

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

> 실행 정책: 실제 프로필은 옵트인 없이는 **차단**된다. 프로필이 잠겨 있거나
> 로그인된 계정이 없으면 **재시도 없이 즉시 종료**한다.
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
- `BrowserSession`(범용) / `GoogleSession`(사이트 전용) 분리로 **다른 사이트로 확장 가능한 구조**.

## 한계 / 다음 단계 (2차 개발 후보)

- 2단계 인증(2FA)은 최초 수동 로그인에서 한 번만 통과하면 이후 세션 재사용으로 커버됨.
- 운영 환경이라면 세션 만료 자동 감지·재로그인 트리거, 헤드리스 안정화, 컨테이너화 고려.
- 정식 데이터 연동이 목적이면 UI 자동화 대신 **OAuth 2.0 / Google API** 로 전환하는
  것이 가장 견고함.

## Playwright E2E (사이트 자동화 개발용)

Python(Selenium) 본체와 독립적인 Node 레이어. 새 사이트 자동화를 만들 때
셀렉터를 찾고 흐름을 검증하는 용도다.

```bash
npm install
npx playwright install chromium

npm run test:slow      # 실제 Chrome 창 + 느린 동작 (눈으로 확인)
npm run test:headed    # 실제 Chrome 창, 정상 속도
npm run test:ui        # UI 모드(스냅샷·타임라인). 별도 브라우저 창은 뜨지 않는다
npm run test:debug     # 단계별 일시정지 디버거
npm run codegen        # 동작 녹화 -> 코드 생성
```

### 브라우저 정책

| 환경 | 브라우저 | 표시 |
|------|---------|------|
| 로컬 | 실제 Google Chrome (`channel: 'chrome'`) | 창 보임 |
| CI | 번들 Chromium | 헤드리스 |

### 로그인이 필요한 사이트 — 전용 프로필

기본 테스트는 매번 **빈 프로필**로 뜬다(재현성 목적). 로그인이 필요하면
**자동화 전용 프로필**에 한 번만 로그인해두고 재사용한다.

```bash
npm run profile:login -- https://로그인할사이트/login   # 최초 1회 수동 로그인
npm run profile:reset                                  # 프로필 초기화
```

이후 스펙에서 `./persistent` 픽스처를 쓰면 로그인 상태가 유지된다.

```ts
import { test, expect } from './persistent';
```

> ⚠️ **사용자의 실제 Chrome 프로필은 쓰지 않는다.** 실제 프로필을 자동화로 띄우면
> 구글이 세션을 무효화해 로그인된 계정이 전부 로그아웃될 수 있다.
> `.pw-profile/` 은 쿠키를 포함하므로 커밋 금지(`.gitignore` 처리됨).
