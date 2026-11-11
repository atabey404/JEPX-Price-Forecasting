import { cpSync, mkdirSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const build = new URL('../dist-pages/', import.meta.url);
const destination = new URL('../../docs/', import.meta.url);
for (const name of ['index.html', 'workspace', 'kairo-assets', 'data']) {
  const target = fileURLToPath(new URL(name, destination));
  mkdirSync(fileURLToPath(destination), { recursive: true });
  cpSync(fileURLToPath(new URL(name, build)), target, { recursive: true });
}
writeFileSync(new URL('.nojekyll', destination), '');
