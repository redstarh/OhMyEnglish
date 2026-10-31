// 회차 b8 — 자동 모드에서 문장 1 → 2 를 실제 전사로 넘기고, 문장 3 의 녹음 창이 끝나기 전에 떠난다(POST 2회).
// 사용: node auto2.mjs <label>   입력 음성: /private/tmp/_b8-auto-s1s2.wav (문장 1 은 2.7초 · 문장 2 는 14.4초)
import { open, APP, api, saver, sleep } from "./lib.mjs";
const label = process.argv[2];
const { note, save } = saver(`AUTO-${label}`);
const p = await open();
const phaseIs = (ph) => `document.querySelector('[data-testid=course-phase]')?.dataset.phase === '${ph}'`;
const numIs = (n) => `document.querySelector('[data-testid=course-sentence-number]')?.textContent === '문장 ${n} / 5'`;
try {
  await p.nav(`${APP}/course/1`, p.READY);
  if ((await p.state()).mode !== "manual") await p.click("수동");
  for (let g = 0; g < 10 && (await p.state()).num !== "문장 1 / 5"; g++) { await p.click("← 이전"); await sleep(250); }
  note("before", await p.state());
  note("apiBefore", (await api("/api/course/days/1")).units[0].sentences.map((s) => [s.key, s.attempts]));
  await p.ev(`(() => { window.__mo2 = []; let last = null; new MutationObserver(() => {
    const ph = document.querySelector('[data-testid=course-phase]')?.dataset.phase ?? 'none';
    const n = document.querySelector('[data-testid=course-notice]')?.textContent ?? '';
    const num = document.querySelector('[data-testid=course-sentence-number]')?.textContent ?? '';
    const tr = document.querySelector('[data-testid=course-transcript]')?.textContent ?? null;
    const k = [ph, n, num, tr].join('|'); if (k !== last) { last = k; window.__mo2.push([Math.round(performance.now()), ph, num, n, tr]); } })
    .observe(document.body, { subtree: true, childList: true, attributes: true, characterData: true }); })()`);
  await p.click("자동");
  const hasStart = await p.ev(`!!${p.btn("시작")}`);
  note("startButtonInAuto", hasStart);
  if (hasStart) await p.click("시작");
  await p.waitFor(`${numIs(1)} && ${phaseIs("done")}`, 40000, 10);
  await sleep(200);
  note("s1Done", await p.state());
  await p.shot(`AUTO-${label}-s1-done`);
  await p.waitFor(`${numIs(2)} && ${phaseIs("listen")}`, 20000, 5);
  note("s2Listen", await p.state());
  await p.waitFor(`${numIs(2)} && ${phaseIs("repeat")}`, 20000, 5);
  note("s2Repeat", await p.state());
  await p.waitFor(`${numIs(2)} && ${phaseIs("done")}`, 40000, 10);
  await sleep(200);
  note("s2Done", await p.state());
  await p.shot(`AUTO-${label}-s2-done`);
  await p.waitFor(`${numIs(3)} && ${phaseIs("listen")}`, 20000, 5);
  note("s3Listen", await p.state());
  await p.waitFor(`${numIs(3)} && ${phaseIs("repeat")}`, 20000, 5);
  note("s3RepeatAtLeave", await p.state());
  note("mo2", await p.ev("window.__mo2"));
  note("phases", await p.ev("window.__phases"));
  note("gum", await p.ev("window.__gum"));
  note("speech", await p.ev("(() => { const out = []; let cur = null; for (const [t, v] of window.__env) { if (v > 20) { if (!cur || t - cur[1] > 300) { cur = [t, t]; out.push(cur); } else cur[1] = t; } } return out; })()"));
  await p.c.send("Page.navigate", { url: `${APP}/course` }); // 문장 3 의 POST 전에 떠남
  await sleep(1500);
} catch (e) { note("ERROR", String(e?.stack ?? e)); try { note("stateAtError", await p.state()); } catch {} }
finally {
  await sleep(300);
  note("apiAfter", (await api("/api/course/days/1")).units[0].sentences.map((s) => [s.key, s.attempts]));
  save(); p.c.close();
}
