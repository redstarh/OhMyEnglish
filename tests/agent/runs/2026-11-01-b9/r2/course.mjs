// 회차 b9 — 시나리오 7: 문법 코스 목록 · 수동 모드(시작·다시·다음·Day 마치기) · 자동 모드 한 흐름.
// 사용: node course.mjs <day>
import { open, APP, api, saver, sleep } from "./lib.mjs";
const day = Number(process.argv[2] ?? 6);
const { note, save } = saver(`COURSE-r2-day${day}`);
const p = await open();
const posts = [];
p.c.on((d) => {
  if (d.method === "Network.responseReceived" && /\/api\/course\//.test(d.params.response.url)) posts.push([Date.now(), d.params.type, d.params.response.status, d.params.response.url.replace("http://localhost:8002", "")]);
});
await p.c.send("Network.enable");
const T = (tid) => `document.querySelector('[data-testid=${tid}]')`;
const st = () => p.ev(`({ unit: ${T("course-unit")}?.textContent, num: ${T("course-sentence-number")}?.textContent, attempts: ${T("course-attempts")}?.textContent,
  phase: ${T("course-phase")}?.dataset.phase ?? null, phaseText: ${T("course-phase")}?.textContent ?? null, notice: ${T("course-notice")}?.textContent ?? null,
  sentence: ${T("course-sentence")}?.textContent, buttons: [...document.querySelectorAll('[data-testid^=course-]')].filter(e => e.tagName === 'BUTTON').map(e => e.dataset.testid + (e.disabled ? '(off)' : '')) })`);
const phaseIs = (ph) => `${T("course-phase")}?.dataset.phase === '${ph}'`;
try {
  // 목록
  await p.nav(`${APP}/course`);
  await p.waitFor(`!!document.querySelector('[data-testid=course-day-1]')`, 20000);
  await sleep(800);
  note("listText", (await p.ev("document.querySelector('main')?.innerText ?? document.body.innerText")).slice(0, 2500));
  note("listDays", await p.ev(`[...document.querySelectorAll('[data-testid^=course-day-]')].map(e => e.innerText.replace(/\\s+/g, ' '))`));
  note("listHangul", await p.hangul());
  const apiBefore = await api("/api/course");
  note("apiDayBefore", apiBefore.body.days.find((d) => d.day === day));

  // Day 화면 · 수동
  await p.nav(`${APP}/course/${day}`);
  await p.waitFor(`!!${T("course-sentence")} && !!${T("course-mode-manual")}`, 20000);
  await p.click("course-mode-manual");
  await sleep(300);
  // 첫 문장으로 되감기
  for (let g = 0; g < 400; g++) { const off = await p.ev(`${T("course-prev")}.disabled`); if (off) break; await p.click("course-prev"); await sleep(30); }
  note("manualStart", await st());
  note("dayHangul", await p.hangul());
  await p.click("course-start");
  const tRepeat = await p.waitFor(phaseIs("repeat"), 20000, 20);
  note("atRepeat", { ms: tRepeat, ...(await st()) });
  await p.waitFor(phaseIs("done"), 40000, 20);
  note("manualDone1", await st());
  await p.click("course-retry");
  await p.waitFor(phaseIs("listen") + " || " + phaseIs("repeat"), 5000, 20);
  await p.waitFor(phaseIs("done"), 40000, 20);
  note("manualDone2", await st());
  await p.click("course-next");
  await sleep(300);
  note("afterNext", await st());
  // 앞 문장으로 돌아가도 안내가 지워지는지(goTo 의 다른 입구)
  await p.click("course-start");
  await p.waitFor(phaseIs("done"), 40000, 20);
  note("manualDone3", await st());
  await p.click("course-prev");
  await sleep(300);
  note("afterPrev", await st());
  // 자동 모드 한 흐름: 첫 문장 → 판정 → 다음 문장으로 저절로 넘어가 listen/repeat 에 들어가는지
  await p.click("course-mode-auto");
  await sleep(300);
  for (let g = 0; g < 400; g++) { const off = await p.ev(`${T("course-prev")}.disabled`); if (off) break; await p.click("course-prev"); await sleep(30); }
  await p.ev("(() => { const ph = document.querySelector('[data-testid=course-phase]'); return true; })()");
  const before = await st(); note("autoBefore", before);
  await p.ev(`(() => { window.__mo = []; let last = ''; new MutationObserver(() => { const k = (${T("course-phase")}?.dataset.phase ?? 'none') + '|' + ${T("course-sentence-number")}?.textContent + '|' + (${T("course-notice")}?.textContent ?? '');
    if (k !== last) { last = k; window.__mo.push([Math.round(performance.now()), k]); } }).observe(document.body, { subtree: true, childList: true, attributes: true, characterData: true }); })()`);
  const startTid = (await p.ev(`!!${T("course-start")}`)) ? "course-start" : "course-retry";
  await p.click(startTid);
  await p.waitFor(`${T("course-sentence-number")}?.textContent !== ${JSON.stringify(before.num)} && (${phaseIs("repeat")})`, 60000, 20);
  note("autoSecondRepeat", await st());
  note("autoMo", await p.ev("window.__mo"));
  await p.nav(`${APP}/course`); // 다음 판정 POST 전에 떠남
  await sleep(1000);
  note("posts", posts);
  // 홈이 끝낸 Day 를 반영하는지
  await p.nav(`${APP}/`);
  await p.waitFor(`${T("home-course-progress")}?.dataset.state === 'ready'`, 20000);
  note("homeCourseAfter", await p.text("home-course-progress"));
} catch (e) { note("ERROR", String(e?.stack ?? e)); try { note("stateAtError", await st()); note("autoMo", await p.ev("window.__mo")); } catch {} note("posts", posts); }
finally { note("logs", p.logs.filter((l) => !/DevTools|HMR/.test(l.text))); save(); p.c.close(); }
