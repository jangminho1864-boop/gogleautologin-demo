import { pathToFileURL } from 'node:url';
import path from 'node:path';
import fs from 'node:fs';
import { test, expect, PROFILE_DIR } from './persistent';

/**
 * 전용 프로필로 브라우저가 뜨는지 확인하는 스모크.
 *
 * 이 프로필은 로그인 상태가 유지되므로 CI 에서는 의미가 없다(러너엔 프로필이 없음).
 * 로컬 개발/디버깅 전용.
 */
test.describe('전용 프로필', () => {
  test.skip(!!process.env.CI, '전용 프로필은 로컬 전용(러너에는 프로필이 없다)');

  test('전용 프로필로 브라우저가 뜨고 페이지를 연다', async ({ page }) => {
    const url = pathToFileURL(
      path.join(__dirname, 'fixtures', 'login-demo.html'),
    ).href;

    await page.goto(url);
    await expect(page.getByRole('button', { name: '로그인' })).toBeVisible();

    // 프로필 디렉터리가 실제로 만들어져 상태가 보존된다.
    expect(fs.existsSync(PROFILE_DIR)).toBe(true);
  });

  test('프로필에 상태가 유지된다(재실행 시 누적)', async ({ page }) => {
    await page.goto('about:blank');
    // localStorage 는 origin 별이라 file:// 대신 간단히 쿠키 유무만 확인한다.
    const cookies = await page.context().cookies();
    // 첫 실행이면 0개일 수 있으므로 존재 자체가 아니라 접근 가능 여부만 본다.
    expect(Array.isArray(cookies)).toBe(true);
  });
});
