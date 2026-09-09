import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright E2E 설정 (사이트 자동화 개발/디버깅용).
 *
 * 이 레이어는 Python(Selenium) 본체와 독립적이다. 새 사이트 자동화를 만들 때
 * `npm run test:ui` 로 셀렉터를 찾고 흐름을 검증한 뒤, 확정된 로직을
 * src/ 의 BrowserSession 하위 클래스로 옮기는 용도다.
 */
export default defineConfig({
  testDir: './tests-e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'html',

  use: {
    // 실패 시에만 증빙을 남긴다(용량/PII 관리).
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    actionTimeout: 10_000,
  },

  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
});
