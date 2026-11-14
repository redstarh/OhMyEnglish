// measures.json 을 요약함: node runs/2026-11-14-b16/screens/summarize.mjs [detail]
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
const HERE = dirname(fileURLToPath(import.meta.url));
const R = JSON.parse(readFileSync(join(HERE, "evidence", "measures.json"), "utf8"));
const uniq = (arr) => [...new Map(arr.map((x) => [JSON.stringify(x), x])).values()];
for (const [scene, byW] of Object.entries(R)) {
  for (const [w, steps] of Object.entries(byW)) {
    if (!Array.isArray(steps)) {
      if (String(w).startsWith("console") && steps.length) console.log(`${scene} ${w}: ${JSON.stringify(steps)}`);
      else if (String(w).startsWith("err")) console.log(`${scene} ${w}: ${steps}`);
      continue;
    }
    for (const s of steps) {
      const { m, ...rest } = s;
      const extra = Object.fromEntries(Object.entries(rest).filter(([k]) => !["n", "desc", "file"].includes(k)));
      console.log(`${scene} ${w} #${s.n} ${m.url} sw/cw=${m.scrollWidth}/${m.clientWidth} hero=${m.hero?.h ?? "-"}(${m.heroMode ?? "-"}) prog=${m.progress?.h ?? "-"} ${JSON.stringify(extra)}`);
      for (const c of m.clipped) console.log(`   CLIP ${JSON.stringify(c)}`);
      for (const c of m.offRight) console.log(`   OFF ${JSON.stringify(c)}`);
      for (const k of m.korean) console.log(`   KO ${JSON.stringify(k)}`);
    }
    const labels = uniq(steps.flatMap((s) => s.m.labels.map((l) => ({ t: l.text, fs: l.fontSize, fw: l.fontWeight, tid: l.tid }))));
    if (process.argv[2] === "detail") for (const l of labels) console.log(`   LABEL ${JSON.stringify(l)}`);
  }
}
