/**
 * 실제 Chrome 프로필 사용 차단 가드 (Playwright 쪽).
 *
 * Python 쪽(main.py)에는 동일한 가드가 있는데 Node 쪽에는 없어서,
 * PW_PROFILE_DIR 로 실제 프로필을 지정하면 그대로 실행되는 구멍이 있었다.
 * 실제 프로필을 자동화로 띄우면 구글이 세션을 무효화해 로그인된 계정이
 * 전부 로그아웃될 수 있으므로, 명시적 옵트인 없이는 막는다.
 */
import os from 'node:os';
import path from 'node:path';

/** 현재 OS 에서 실제 Chrome 의 'User Data' 디렉터리를 추정한다. */
export function realChromeUserDataDir(platform: NodeJS.Platform = process.platform): string {
  const home = os.homedir();
  if (platform === 'win32') {
    const local = process.env.LOCALAPPDATA ?? path.join(home, 'AppData', 'Local');
    return path.join(local, 'Google', 'Chrome', 'User Data');
  }
  if (platform === 'darwin') {
    return path.join(home, 'Library', 'Application Support', 'Google', 'Chrome');
  }
  return path.join(home, '.config', 'google-chrome');
}

/** dir 이 base 와 같거나 그 하위 경로인지. */
export function isInside(dir: string, base: string): boolean {
  const rel = path.relative(path.resolve(base), path.resolve(dir));
  return rel === '' || (!rel.startsWith('..') && !path.isAbsolute(rel));
}

/**
 * 실제 Chrome 프로필이면 예외를 던진다.
 * PW_ALLOW_REAL_PROFILE=1 로 명시 옵트인하면 통과시킨다(Python 의 --use-real-profile 대응).
 */
export function assertNotRealProfile(
  dir: string,
  opts: { allow?: boolean; realDir?: string } = {},
): void {
  const allow = opts.allow ?? process.env.PW_ALLOW_REAL_PROFILE === '1';
  if (allow) return;

  const real = opts.realDir ?? realChromeUserDataDir();
  if (isInside(dir, real)) {
    throw new Error(
      `실제 Chrome 프로필로의 실행은 차단되어 있습니다: ${dir}\n` +
        '  자동화로 실제 프로필을 띄우면 구글이 세션을 무효화해\n' +
        '  로그인된 계정이 전부 로그아웃될 수 있습니다.\n' +
        '  자동화 전용 프로필(.pw-profile)을 쓰거나, 위험을 감수한다면\n' +
        '  PW_ALLOW_REAL_PROFILE=1 을 명시하세요.',
    );
  }
}
