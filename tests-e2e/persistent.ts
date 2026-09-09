/**
 * 전용 프로필(persistent context) 테스트 픽스처.
 *
 * 기본 Playwright 테스트는 매번 **빈 프로필**로 브라우저를 띄운다(재현성 목적).
 * 로그인이 필요한 사이트를 자동화할 때는 그때마다 로그인할 수 없으므로,
 * **자동화 전용 프로필**을 하나 만들어 한 번만 로그인해두고 계속 재사용한다.
 *
 * 사용자의 실제 Chrome 프로필은 절대 쓰지 않는다. 실제 프로필을 자동화로 띄우면
 * 구글이 세션을 무효화해 로그인된 계정이 전부 로그아웃될 수 있다.
 *
 * 최초 1회 로그인:
 *     npm run profile:login -- https://로그인할사이트/login
 *
 * 사용:
 *     import { test, expect } from './persistent';
 */
import path from 'node:path';
import { test as base, chromium, type BrowserContext, type Page } from '@playwright/test';

/** 자동화 전용 프로필 경로. .gitignore 로 커밋이 차단되어 있다(쿠키 포함). */
export const PROFILE_DIR =
  process.env.PW_PROFILE_DIR ?? path.join(process.cwd(), '.pw-profile');

const isCI = !!process.env.CI;

export const test = base.extend<{ context: BrowserContext; page: Page }>({
  context: async ({}, use) => {
    const context = await chromium.launchPersistentContext(PROFILE_DIR, {
      headless: isCI,
      // 로컬은 실제 Google Chrome(북마크/UI 가 익숙한 그 크롬), CI 는 번들 Chromium.
      ...(isCI ? {} : { channel: 'chrome' }),
      slowMo: Number(process.env.PW_SLOWMO ?? 0),
    });
    await use(context);
    await context.close();
  },

  page: async ({ context }, use) => {
    const page = context.pages()[0] ?? (await context.newPage());
    await use(page);
  },
});

export { expect } from '@playwright/test';
