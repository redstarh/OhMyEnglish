import { open, APP } from "./lib.mjs";
import { writeFileSync } from "node:fs";
const p = await open();
await p.nav(`${APP}/course/5`, p.READY);
const r = await p.ev(`(async () => { const srcs = performance.getEntriesByType('resource').map(e => e.name).filter(n => n.includes('/_next/static/') && n.endsWith('.js'));
  for (const s of srcs) { const t = await (await fetch(s)).text(); const i = t.indexOf('TASK-289'); if (i >= 0) { const j = t.indexOf('seekTo(startRef.current', i - 400); return { src: s.split('/').pop(), snippet: t.slice(j, j + 160) }; } } return { found: false, n: srcs.length }; })()`);
writeFileSync("evidence/codecheck.json", JSON.stringify(r, null, 1)); console.log(JSON.stringify(r)); p.c.close();
