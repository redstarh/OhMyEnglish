// 따라 하기 한 번 (수동 모드 · Day 1 · 지정 문장). 사용: node attempt.mjs <label> <probe|real> [sentenceIndex]
// probe: 녹음 창이 끝나기 0.5초 전에 문서를 떠나 POST(=Nova 호출)를 내지 않고, 입력 세기로 문장이 창 안에 들어오는지만 본다.
// real : 판정까지 기다려 화면·응답·횟수를 기록하고, 새로 고침 뒤 횟수 유지를 본다.
import { open, APP, api, saver, sleep } from "./lib.mjs";
const [label, mode] = [process.argv[2], process.argv[3]];
const idx = Number(process.argv[4] ?? 4);
const { note, save } = saver(`ATTEMPT-${label}`);
const p = await open();
const phaseIs = (ph) => `document.querySelector('[data-testid=course-phase]')?.dataset.phase === '${ph}'`;
async function windowInfo() {
  const phases = await p.ev("window.__phases");
  const rep = phases.find((x) => x.phase === "repeat"); const jud = phases.find((x) => x.phase === "judge");
  const env = await p.ev("window.__env");
  const loud = env.filter((x) => x[1] > 20);
  const gum = await p.ev("window.__gum");
  return { gum, repeatAt: rep?.t, judgeAt: jud?.t ?? null, speechFirst: loud[0]?.[0] ?? null, speechLast: loud.at(-1)?.[0] ?? null,
    speechInWindowFromRepeatMs: rep && loud[0] ? [loud[0][0] - rep.t, loud.at(-1)[0] - rep.t] : null };
}
try {
  await p.nav(`${APP}/course/1`, p.READY);
  if ((await p.state()).mode !== "manual") await p.click("수동");
  for (let g = 0; g < 10 && (await p.state()).num !== `문장 ${idx} / 5`; g++) { const n = Number((await p.state()).num.match(/\d+/)[0]); await p.click(n > idx ? "← 이전" : "다음 문장 →"); await sleep(250); }
  const before = await p.state();
  note("before", before);
  const apiBefore = (await api("/api/course/days/1")).units[0].sentences[idx - 1];
  note("apiBefore", apiBefore);
  await p.ev(`(() => { window.__mo2 = []; let last = null; new MutationObserver(() => { const el = document.querySelector('[data-testid=course-phase]'); const ph = el ? el.dataset.phase : 'none';
    const n = document.querySelector('[data-testid=course-notice]')?.textContent ?? ''; const k = ph + '|' + n; if (k !== last) { last = k; window.__mo2.push([Math.round(performance.now()), ph, n]); } })
    .observe(document.body, { subtree: true, childList: true, attributes: true, characterData: true }); })()`);
  note("initPresent", await p.ev("({ phases: Array.isArray(window.__phases), gum: Array.isArray(window.__gum) })"));
  await p.click("시작");
  await p.waitFor(phaseIs("repeat"), 20000, 5);
  const label2 = await p.ev("document.querySelector('[data-testid=course-phase]').textContent");
  const windowMs = Math.round(Number(label2.match(/([\d.]+)초/)[1]) * 1000);
  note("windowMs", windowMs);
  if (mode === "probe") {
    await sleep(windowMs - 500);
    note("window", await windowInfo());
    await p.c.send("Page.navigate", { url: "http://localhost:3000/course" });
  } else {
    await p.waitFor(phaseIs("done"), 40000, 10);
    note("window", await windowInfo());
    const ph = await p.ev("window.__phases");
    const j = ph.find((x) => x.phase === "judge"), d = ph.find((x) => x.phase === "done");
    note("mo2", await p.ev("window.__mo2"));
    note("judgeToDoneMs", d && j ? d.t - j.t : null);
    await sleep(300);
    const after = await p.state();
    note("after", after);
    await p.shot(`ATTEMPT-${label}`);
    const apiAfter = (await api("/api/course/days/1")).units[0].sentences[idx - 1];
    note("apiAfter", apiAfter);
    await p.reload(p.READY);
    await sleep(300);
    for (let g = 0; g < 10 && (await p.state()).num !== `문장 ${idx} / 5`; g++) { const n = Number((await p.state()).num.match(/\d+/)[0]); await p.click(n > idx ? "← 이전" : "다음 문장 →"); await sleep(250); }
    note("afterReload", await p.state());
  }
} catch (e) { note("ERROR", String(e?.stack ?? e)); try { note("mo2", await p.ev("window.__mo2")); note("stateAtError", await p.state()); } catch {} }
finally { save(); p.c.close(); }
