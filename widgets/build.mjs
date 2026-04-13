import { build } from 'vite';
import fs from 'fs';
import path from 'path';

const input = process.env.INPUT;

if (!input) {
  // Build all widgets
  const srcDir = path.resolve('src');
  const dirs = fs.readdirSync(srcDir).filter(d =>
    fs.statSync(path.join(srcDir, d)).isDirectory() && d !== 'shared'
  );

  for (const dir of dirs) {
    const entry = path.join('src', dir, 'index.html');
    if (fs.existsSync(entry)) {
      console.log(`\n⚓ Building ${dir}...`);
      process.env.INPUT = entry;
      await build({ configFile: 'vite.config.ts' });

      // Rename output to widget name
      const outFile = path.resolve('dist', 'src', dir, 'index.html');
      const destFile = path.resolve('dist', `${dir}.html`);
      if (fs.existsSync(outFile)) {
        fs.copyFileSync(outFile, destFile);
        console.log(`  → dist/${dir}.html`);
      }
    }
  }

  // Clean up nested dirs
  const nestedSrc = path.resolve('dist', 'src');
  if (fs.existsSync(nestedSrc)) {
    fs.rmSync(nestedSrc, { recursive: true });
  }
} else {
  // Build single widget
  console.log(`⚓ Building ${input}...`);
  await build({ configFile: 'vite.config.ts' });
}
