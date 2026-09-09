import path from 'node:path';
import { test, expect } from '@playwright/test';
import { assertNotRealProfile, isInside, realChromeUserDataDir } from './profile-guard';

/**
 * 실제 Chrome 프로필 차단 가드 테스트 (브라우저 미기동).
 * Python 쪽 tests/test_real_profile_guard.py 와 같은 정책을 Node 쪽에서도 보장한다.
 */
test.describe('실제 프로필 가드', () => {
  const REAL = '/Users/tester/Library/Application Support/Google/Chrome';

  test('OS별 실제 프로필 경로를 추정한다', () => {
    expect(realChromeUserDataDir('darwin')).toContain('Library/Application Support/Google/Chrome');
    expect(realChromeUserDataDir('linux')).toContain('.config/google-chrome');
    expect(realChromeUserDataDir('win32')).toContain(path.join('Google', 'Chrome', 'User Data'));
  });

  test('실제 프로필 경로면 차단한다', () => {
    expect(() => assertNotRealProfile(REAL, { realDir: REAL })).toThrow(/차단/);
  });

  test('실제 프로필의 하위 경로도 차단한다', () => {
    const sub = path.join(REAL, 'Default');
    expect(() => assertNotRealProfile(sub, { realDir: REAL })).toThrow(/차단/);
  });

  test('전용 프로필은 통과한다', () => {
    const dedicated = path.join(process.cwd(), '.pw-profile');
    expect(() => assertNotRealProfile(dedicated, { realDir: REAL })).not.toThrow();
  });

  test('명시 옵트인하면 통과한다', () => {
    expect(() => assertNotRealProfile(REAL, { realDir: REAL, allow: true })).not.toThrow();
  });

  test('isInside 는 형제 경로를 하위로 오인하지 않는다', () => {
    expect(isInside('/a/b', '/a')).toBe(true);
    expect(isInside('/a', '/a')).toBe(true);
    expect(isInside('/ab', '/a')).toBe(false);   // 접두사만 같은 형제 경로
    expect(isInside('/c', '/a')).toBe(false);
  });
});
