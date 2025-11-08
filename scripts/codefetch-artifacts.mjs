// path: scripts/codefetch-artifacts.mjs
#!/usr/bin/env node
import { spawnSync } from 'node:child_process';
import path from 'node:path';

const argv = process.argv.slice(2);
let out = 'artifacts_codebase.md';
let dirs = [];

for (let i = 0; i < argv.length; i++) {
  const a = argv[i];
  if (a === '--out' && argv[i + 1]) { out = argv[++i]; continue; }
  if (a.startsWith('--out=')) { out = a.split('=')[1]; continue; }
  if (a === '--dir' && argv[i + 1]) { dirs.push(argv[++i]); continue; }
  if (a.startsWith('--dir=')) { dirs.push(a.split('=')[1]); continue; }
  if (a === '--dirs' && argv[i + 1]) { dirs.push(...argv[++i].split(',')); continue; }
  if (a.startsWith('--dirs=')) { dirs.push(...a.split('=')[1].split(',')); continue; }
  if (!a.startsWith('--')) { dirs.push(a); continue; } // positional
}

const include = (dirs.length ? dirs : ['']).flatMap(d => ['--include-dir', d ? path.posix.join('artifacts', d) : 'artifacts']);

const r = spawnSync('pnpm', ['exec', 'codefetch', ...include, '--exclude-dirs', '__pycache__', '-o', out], { stdio: 'inherit' });
process.exit(r.status ?? 0);
