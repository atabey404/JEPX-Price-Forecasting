import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { fileURLToPath } from 'node:url';

const path = relative => fileURLToPath(new URL(relative, import.meta.url));
const base = process.env.KAIRO_PAGES_BASE || '/JEPX-Price-Forecasting/';
if (!/^\/(?:[a-zA-Z0-9._-]+\/)*$/.test(base)) {
  throw new Error('KAIRO_PAGES_BASE must be a path with leading and trailing slashes');
}

export default defineConfig({
  root: path('./pages'),
  base,
  publicDir: path('./public'),
  plugins: [react()],
  define: { 'process.env.NEXT_PUBLIC_KAIRO_BASE_PATH': JSON.stringify(base) },
  css: { postcss: path('./') },
  build: {
    outDir: path('./dist-pages'),
    emptyOutDir: true,
    assetsDir: 'kairo-assets',
    rolldownOptions: {
      input: {
        home: path('./pages/index.html'),
        workspace: path('./pages/workspace/index.html'),
      },
    },
  },
});
