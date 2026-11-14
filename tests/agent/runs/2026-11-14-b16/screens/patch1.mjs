// shoot.mjs 를 고침(내 폴더 안): 마이크 권한 이름 · 결과 장면의 세션 ID · 기록 줄 클릭 단계
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
const f = join(dirname(fileURLToPath(import.meta.url)), "shoot.mjs");
let s = readFileSync(f, "utf8");
const rep = (a, b) => {
  if (!s.includes(a)) throw new Error("not found: " + a.slice(0, 60));
  s = s.split(a).join(b);
};
rep(`{ name: "audioCapture" }`, `{ name: "microphone" }`);
rep(
  `    await shot(page, "history", w, 1, "Your progress → History — /history");`,
  `    await shot(page, "history", w, 1, "Your progress → History — /history");
    const row = page.getByText("2026-11-01", { exact: false }).first();
    const before = page.url();
    await row.click().catch(() => {});
    await sleep(2000);
    await shot(page, "history", w, 2, "공부한 날(2026-11-01) 줄을 누름", { moved: page.url() !== before, url: new URL(page.url()).pathname, rowTag: await row.evaluate((e) => e.tagName + (e.closest("a,button") ? "/clickable" : "/plain")).catch(() => null) });`,
);
rep(
  `    await page.goto(APP + "/history", { waitUntil: "domcontentloaded" });
    await sleep(3000);
    let href`,
  `    const FIXED = "/results/7a18a111-2a62-4697-9ad8-a4b668fc0807";
    await page.goto(APP + FIXED, { waitUntil: "domcontentloaded" });
    await sleep(5000);
    await shot(page, "results", w, 2, "격리 DB 완료 세션(발화 26건) 결과 화면", { href: FIXED });
    await page.goto(APP + "/history", { waitUntil: "domcontentloaded" });
    await sleep(3000);
    let href`,
);
writeFileSync(f, s);
console.log("patched");
