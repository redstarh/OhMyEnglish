// 회차 b7 — 자동 모드에서 전사기 503 을 1회 받은 뒤 흐름이 어떻게 되는지 본다.
// 첫 문장의 판정 POST 1회 뒤, 다음 문장의 녹음 창이 끝나기 전에 문서를 떠나 두 번째 POST 를 내지 않는다.
import { open, APP, api, saver, sleep } from "./lib.mjs";
const label = process.argv[2]; const idx = Number(process.argv[3] ?? 4);
const { note, save } = saver(`AUTO-${label}`);
const p = await open();
const phaseIs = (ph) => `document.querySelector('[data-testid=course-phase]')?.dataset.phase === '${ph}'`;
try {
  await p.nav(`${APP}/course/1`, p.READY);
  if ((await p.state()).mode !== "manual") await p.click("수동");
  for (let g = 0; g < 10 && (await p.state()).num !== `문장 ${idx} / 5`; g++) { const n = Number((await p.state()).num.match(/\d+/)[0]); await p.click(n > idx ? "← 이전" : "다음 문장 →"); await sleep(250); }
  await p.click("자동");
  note("before", await p.state());
  note("apiBefore", (await api("/api/course/days/1")).units[0].sentences.map((s) => [s.key, s.attempts]));
  await p.ev(`(() => { window.__mo2 = []; let last = null; new MutationObserver(() => { const el = document.querySelector('[data-testid=course-phase]'); const ph = el ? el.dataset.phase : 'none';
    const n = document.querySelector('[data-testid=course-notice]')?.textContent ?? ''; const num = document.querySelector('[data-testid=course-sentence-number]')?.textContent ?? '';
    const bar = document.querySelector('.omy-course-wait'); const k = ph + '|' + n + '|' + num + '|' + (bar ? bar.style.animationDuration : '-'); if (k !== last) { last = k; window.__mo2.push([Math.round(performance.now()), ph, num, n, bar ? bar.style.animationDuration : null]); } })
    .observe(document.body, { subtree: true, childList: true, attributes: true, characterData: true }); })()`);
  // 자동 모드가 「시작」 없이 도는지, 시작 버튼이 필요한지 둘 다 다룬다
  const hasStart = await p.ev(`!!${p.btn("시작")}`);
  note("startButtonInAuto", hasStart);
  if (hasStart) await p.click("시작");
  await p.waitFor(phaseIs("repeat"), 20000, 5);
  note("barAtRepeat", await p.ev(`(() => { const b = document.querySelector('.omy-course-wait'); return b ? { dur: b.style.animationDuration, anim: getComputedStyle(b).animationName, w: b.getBoundingClientRect().width, pw: b.parentElement.getBoundingClientRect().width } : null; })()`));
  await sleep(1000);
  note("barAt1s", await p.ev(`(() => { const b = document.querySelector('.omy-course-wait'); return b ? { w: b.getBoundingClientRect().width, pw: b.parentElement.getBoundingClientRect().width } : null; })()`));
  await p.waitFor(phaseIs("judge"), 20000, 5);
  // 다음 문장으로 넘어가 그 문장의 repeat 에 들어갈 때까지 기다린다
  const nextNum = `문장 ${idx + 1} / 5`;
  await p.waitFor(`document.querySelector('[data-testid=course-sentence-number]')?.textContent === ${JSON.stringify(nextNum)} && ${phaseIs("repeat")}`, 40000, 10);
  await sleep(500);
  note("stateInNextRepeat", await p.state());
  note("mo2", await p.ev("window.__mo2"));
  await p.c.send("Page.navigate", { url: `${APP}/course` }); // 두 번째 POST 전에 떠남
  await sleep(1500);
} catch (e) { note("ERROR", String(e?.stack ?? e)); try { note("mo2", await p.ev("window.__mo2")); note("stateAtError", await p.state()); } catch {} }
finally { await sleep(500); note("apiAfter", (await api("/api/course/days/1")).units[0].sentences.map((s) => [s.key, s.attempts])); save(); p.c.close(); }
