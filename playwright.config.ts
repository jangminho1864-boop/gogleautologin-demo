import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright E2E 설정 (사이트 자동화 개발/디버깅용).
 *
 * 이 레이어는 Python(Selenium) 본체와 독립적이다. 새 사이트 자동화를 만들 때
 * UI/헤드드 모드로 셀렉터를 찾고 흐름을 검증한 뒤, 확정된 로직을
 * src/ 의 BrowserSession 하위 클래스로 옮기는 용도다.
 *
 * 브라우저 정책
 * -------------
 * - 로컬: 실제 Google Chrome(channel: 'chrome') 을 **창이 보이는** 상태로 띄운다.
 * - CI  : 번들 Chromium 을 헤드리스로 (설치 빠르고 러너에 Chrome 불필요).
 *
 * 참고: `--ui` 모드는 별도 브라우저 창을 띄우지 않고 UI 앱 안에서 DOM 스냅샷을
 * 보여주는 것이 정상 동작이다. 실제 브라우저 창을 보려면 `--headed` 를 쓴다.
 */
const isCI = !!process.env.CI;

export default defineConfig({
  testDir: './tests-e2e',
  fullyParallel: true,
  forbidOnly: isCI,
  retries: isCI ? 2 : 0,
  workers: isCI ? 1 : undefined,
  reporter: isCI ? [['list'], ['html', { open: 'never' }]] : 'html',

  use: {
    // 실패 시에만 증빙을 남긴다(용량/PII 관리).
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    actionTimeout: 10_000,

    // 로컬에서는 창이 보이게(헤드드) 실행해 동작을 눈으로 확인한다.
    headless: isCI,
    // 동작이 너무 빨라 안 보이면 PW_SLOWMO=300 처럼 지정한다(ms).
    launchOptions: { slowMo: Number(process.env.PW_SLOWMO ?? 0) },
  },

  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        // 로컬은 실제 설치된 Google Chrome, CI 는 번들 Chromium.
        ...(isCI ? {} : { channel: 'chrome' }),
      },
    },
  ],
});
