// measures.json 요약: node runs/2026-11-14-b18/screens/summarize.mjs [장면…] → evidence/summary.txt 도 씀
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
const HERE = dirname(fileURLToPath(import.meta.url));
const R = JSON.parse(readFileSync(join(HERE, "evidence", "measures.json"), "utf8"));
const only = process.argv.slice(2);
const out = [];
for (const [scene, byW] of Object.entries(R)) {
  if (only.length && !only.includes(scene)) continue;
  for (const [w, steps] of Object.entries(byW)) {
    if (!Array.isArray(steps)) {
      if ((Array.isArray(steps) && steps.length) || (typeof steps === "string") || (Array.isArray(steps) === false && steps && steps.length)) out.push(`${scene} ${w}: ${JSON.stringify(steps)}`);
      continue;
    }
    for (const s of steps) {
      const m = s.m;
      const { n, desc, file, at, m: _m, ...extra } = s;
      out.push(`## ${scene} ${w} #${n} ${desc} · ${m.url} · body ${m.bodyScrollWidth}/${m.innerWidth} · scrollY ${m.scrollY}` + (m.hero ? ` · hero ${m.hero.h}(${m.heroMode})` : "") + (m.progress ? ` · progress ${m.progress.h}` : "") + (m.courseCard ? ` · card ${m.courseCard.h}` : "") + (m.koPressed ? ` · KO ${m.koPressed}` : ""));
      if (Object.keys(extra).length) out.push(`  extra ${JSON.stringify(extra)}`);
      out.push(`  texts ${JSON.stringify(m.texts)}`);
      if (m.fonts && Object.values(m.fonts).some(Boolean)) out.push(`  fonts ${JSON.stringify(m.fonts)}`);
      if (m.clipped.length) out.push(`  clipped ${JSON.stringify(m.clipped)}`);
      if (m.offRight.length) out.push(`  offRight ${JSON.stringify(m.offRight)}`);
      if (m.wideMedia.length) out.push(`  wideMedia ${JSON.stringify(m.wideMedia)}`);
      if (m.korean.length) out.push(`  korean ${JSON.stringify(m.korean)}`);
      const lab = [...new Set(m.labels.map((l) => `${l.fontSize}/${l.fontWeight}/${l.letterSpacing}`))];
      out.push(`  labels ${m.labels.length} 종류 ${JSON.stringify(lab)} :: ${m.labels.map((l) => l.text).join(" | ")}`);
      out.push(`  buttons ${JSON.stringify(m.buttons)}`);
    }
  }
}
const txt = out.join("\n");
writeFileSync(join(HERE, "evidence", only.length ? `summary-${only.join("_")}.txt` : "summary.txt"), txt);
console.log(txt);
