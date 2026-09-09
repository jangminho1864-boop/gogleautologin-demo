import { test, expect } from '@playwright/test';
import { pathToFileURL } from 'node:url';
import path from 'node:path';

/**
 * 로그인 흐름 자동화 템플릿.
 *
 * 흐름: 실행 → 로그인 버튼 → 아이디 입력 → 다음 → 비밀번호 입력 → 로그인 → 결과 검증
 *
 * 대상은 로컬 fixture 페이지라 네트워크·외부 계정에 의존하지 않는다(결정적/CI 안전).
 * 실제 사이트를 자동화할 때는 PAGE_URL 과 셀렉터만 바꾸면 된다.
 */
const PAGE_URL = pathToFileURL(
  path.join(__dirname, 'fixtures', 'login-demo.html'),
).href;

test.describe('로그인 흐름', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(PAGE_URL);
  });

  test('로그인 버튼 → 아이디 → 다음 → 비밀번호 → 로그인 성공', async ({ page }) => {
    await page.getByRole('button', { name: '로그인' }).click();

    const username = page.getByLabel('아이디');
    await expect(username).toBeFocused(); // 클릭 후 입력창에 커서가 놓여야 한다
    await username.fill('demo-user');

    await page.getByRole('button', { name: '다음' }).click();

    const password = page.getByLabel('비밀번호');
    await expect(password).toBeFocused();
    await password.fill('demo-pass');

    await page.getByRole('button', { name: '로그인' }).click();

    await expect(page.locator('#result')).toHaveText('로그인 성공');
    await expect(page.locator('body')).toHaveAttribute('data-logged-in', 'true');
  });

  test('아이디를 비우면 다음 단계로 넘어가지 않는다', async ({ page }) => {
    await page.getByRole('button', { name: '로그인' }).click();
    await page.getByRole('button', { name: '다음' }).click();

    await expect(page.locator('#result')).toHaveText('아이디를 입력하세요');
    await expect(page.getByLabel('비밀번호')).toBeHidden();
  });

  test('비밀번호를 비우면 로그인되지 않는다', async ({ page }) => {
    await page.getByRole('button', { name: '로그인' }).click();
    await page.getByLabel('아이디').fill('demo-user');
    await page.getByRole('button', { name: '다음' }).click();
    await page.getByRole('button', { name: '로그인' }).click();

    await expect(page.locator('#result')).toHaveText('비밀번호를 입력하세요');
    await expect(page.locator('body')).not.toHaveAttribute('data-logged-in', 'true');
  });
});
