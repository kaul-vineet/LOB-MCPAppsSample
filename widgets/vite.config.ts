import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { viteSingleFile } from 'vite-plugin-singlefile';

const INPUT = process.env.INPUT;

export default defineConfig({
  plugins: [
    react(),
    viteSingleFile(),
    // Strip crossorigin attribute (sandboxed iframes have null origin)
    {
      name: 'strip-crossorigin',
      transformIndexHtml(html) {
        return html.replace(/\s+crossorigin/g, '');
      },
    },
  ],
  build: {
    sourcemap: false,
    cssMinify: true,
    minify: 'esbuild',
    rollupOptions: {
      input: INPUT,
    },
    outDir: 'dist',
    emptyOutDir: false,
  },
});
