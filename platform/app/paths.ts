const base = process.env.NEXT_PUBLIC_KAIRO_BASE_PATH || '/';

export function sitePath(path = '') {
  return base + path.replace(/^\//, '');
}
