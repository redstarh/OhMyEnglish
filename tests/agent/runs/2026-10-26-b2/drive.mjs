// 회차 2026-10-26-b2 — 시나리오 실행기. 사용: node drive.mjs <S1|S2|...>
// 판정은 DOM 값·API 응답으로 한다. 스크린샷은 보조 증거다.
import { writeFileSync } from "node:fs";
import { connect, pageTarget, sleep, EV } from "./cdp.mjs";

const APP = "http://localhost:3000";
const API = "http://localhost:8002";
const page = await pageTarget();
const c = await connect(page.webSocketDebuggerUrl);
await c.send("Page.enable");
await c.send("Runtime.enable");
const out = {};
const t0 = Date.now();
const note = (k, v) => {
  out[k] = v;
  console.log(k, typeof v === "string" ? v : JSON.stringify(v));
};

async function ev(expression) {
  const r = await c.send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true, userGesture: true });
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description ?? r.exceptionDetails.text);
  return r.result.value;
}
async function waitFor(expression, timeout = 15000, step = 50) {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    try {
      if (await ev(expression)) return Date.now() - start;
    } catch {}
    await sleep(step);
  }
  throw new Error(`timeout: ${expression}`);
}
async function nav(url, readyExpr) {
  await c.send("Page.navigate", { url });
  await waitFor(`location.href === ${JSON.stringify(url)} && document.readyState !== "loading"`);
  if (readyExpr) await waitFor(readyExpr);
  await fakeMic();
}
async function reload(readyExpr) {
  await ev("window.__reloadMark = 1");
  await c.send("Page.reload", { ignoreCache: false });
  await waitFor(`!window.__reloadMark && document.readyState !== "loading"`);
  if (readyExpr) await waitFor(readyExpr);
  await fakeMic();
}
// ⚠️ 환경 대체(FAKE_MIC=1): 이 실행 환경의 Chrome 은 오디오 getUserMedia 가 끝나지 않는다
// (evidence/audio-env-blocked.txt). 앱 코드는 그대로 두고 «브라우저의 마이크 장치»만 Web Audio 합성
// 스트림으로 바꿔 끼운다 — --use-fake-device-for-media-stream 과 같은 층의 대체다.
async function fakeMic() {
  // 단계 관측을 폴링(20ms)이 아니라 MutationObserver 로 한다 — 503 이 수 ms 만에 와서 judge 가
  // 폴링 사이에 지나갔다(회차 b2 S4 1차). DOM 에 커밋된 변화는 모두 잡힌다.
  await ev(`(() => { if (window.__mo) return; window.__phaseMO = []; let last = null;
    window.__mo = new MutationObserver(() => { const el = document.querySelector('[data-testid=course-phase]');
      const p = el ? el.dataset.phase : 'none'; if (p !== last) { last = p; window.__phaseMO.push({ t: Math.round(performance.now()), phase: p,
        num: document.querySelector('[data-testid=course-sentence-number]')?.textContent }); } });
    window.__mo.observe(document.body, { subtree: true, childList: true, attributes: true, characterData: true }); })()`);
  if (!process.env.FAKE_MIC) return;
  await ev(`(() => { if (window.__fakeMic) return; window.__fakeMic = true;
    navigator.mediaDevices.getUserMedia = async () => { await new Promise(r => setTimeout(r, ${Number(process.env.FAKE_MIC_DELAY || 0)})); const ac = new AudioContext(); const o = ac.createOscillator();
      const d = ac.createMediaStreamDestination(); o.connect(d); o.start();
      for (const t of d.stream.getTracks()) window.__tracks.push(t); window.__gumCalls = (window.__gumCalls||0)+1; return d.stream; }; })()`);
}
async function shot(name) {
  const r = await c.send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true });
  writeFileSync(`${EV}/${name}.png`, Buffer.from(r.data, "base64"));
}
const btn = (text) =>
  `[...document.querySelectorAll('button')].find(b => b.textContent.trim() === ${JSON.stringify(text)})`;
// ⚠️ 하이드레이션 전 클릭은 무시된다(회차 b2 S1 1차에서 실측) — React 핸들러가 붙은 뒤에 누른다.
const click = async (text) => {
  await waitFor(`(() => { const b = ${btn(text)}; return !!b && Object.keys(b).some(k => k.startsWith('__reactProps')); })()`, 15000, 10);
  return ev(`(() => { const b = ${btn(text)}; b.click(); return true; })()`);
};
const state = () =>
  ev(`({
    unit: document.querySelector('[data-testid=course-unit]')?.textContent,
    num: document.querySelector('[data-testid=course-sentence-number]')?.textContent,
    sentence: document.querySelector('[data-testid=course-sentence]')?.textContent,
    phase: document.querySelector('[data-testid=course-phase]')?.dataset.phase ?? null,
    notice: document.querySelector('[data-testid=course-notice]')?.textContent ?? null,
    prevDisabled: ${btn("← 이전")}?.disabled,
    auto: ${btn("자동")}?.getAttribute('aria-pressed'),
    manual: ${btn("수동")}?.getAttribute('aria-pressed'),
    mode: localStorage.getItem('omy.course.mode'),
  })`);
const DAY2_READY = `!!document.querySelector('[data-testid=course-sentence]')`;
const api = async (path) => (await fetch(`${API}${path}`)).json();

const scenario = process.argv[2];
try {
  if (scenario === "S1") {
    await nav(`${APP}/course`, `!!document.querySelector('[data-testid=course-day-6]')`);
    note("dom", await ev(`({
      days: document.querySelectorAll('[data-testid^=course-day-]').length,
      dayHeads: [...document.querySelectorAll('[data-testid^=course-day-]')].map(d => d.querySelector('span').textContent),
      cycleText: [...document.querySelectorAll('span')].filter(s => s.textContent.trim() === '1회차').length,
      heatCells: document.querySelectorAll('[data-testid=course-heatmap] [data-attempts]').length,
      heatCellsAll: document.querySelectorAll('[data-attempts]').length,
      resume: [...document.querySelectorAll('a,button')].filter(e => e.textContent.trim() === '이어서 학습 ▶').length,
      resumeHref: [...document.querySelectorAll('a')].filter(e => e.textContent.trim() === '이어서 학습 ▶').map(a => a.getAttribute('href')),
    })`));
    await shot("S1-course");
    await nav(`${APP}/`, `!!(${btn("문법 코스")})`);
    await click("문법 코스");
    note("afterClickWaitMs", await waitFor(`location.pathname === '/course' && !!document.querySelector('[data-testid=course-day-1]')`));
    note("pathname", await ev("location.pathname"));
    await shot("S1-from-home");
  } else if (scenario === "S2") {
    await nav(`${APP}/course/2`, DAY2_READY);
    const dayApi = await api("/api/course/days/2");
    writeFileSync(`${EV}/S2-api-day2.json`, JSON.stringify(dayApi, null, 1));
    const s = await state();
    note("state", s);
    note("apiFirst", { unit: dayApi.units[0].unit, topic: dayApi.units[0].topic, text: dayApi.units[0].sentences[0].text, progress: dayApi.progress });
    note("sentenceMatches", s.sentence === dayApi.units[0].sentences[0].text);
    await shot("S2-initial");
    await click("수동");
    note("afterManualClick", await state());
    await reload(DAY2_READY);
    note("afterReload", await state());
    await shot("S2-manual-after-reload");
  } else if (scenario === "S3") {
    await ev("window.__reloadMark = 1");
    note("ms_markSet", Date.now() - t0);
    await c.send("Page.reload", {});
    note("ms_reloadAck", Date.now() - t0);
    await waitFor(`!window.__reloadMark && document.readyState !== "loading"`);
    note("ms_freshDoc", Date.now() - t0);
    await waitFor(DAY2_READY);
    note("ms_ready", Date.now() - t0);
    await fakeMic();
    note("ms_fakeMic", Date.now() - t0);
    note("before", await state());
    note("ms_beforeClick", Date.now() - t0);
    await ev("window.__phases.length = 0");
    await click("시작");
    const tStart = Date.now();
    await waitFor(`document.querySelector('[data-testid=course-phase]')?.dataset.phase === 'done'`, 30000);
    note("doneAfterMs", Date.now() - tStart);
    const atDone = await state();
    note("atDone", atDone);
    await shot("S3-done");
    await sleep(3500);
    note("after3_5s", await state());
    note("phases", await ev("window.__phases"));
    note("phasesMO", await ev("window.__phaseMO"));
  } else if (scenario === "S4") {
    await click("자동");
    await reload(DAY2_READY);
    note("before", await state());
    await ev("window.__phases.length = 0");
    await click("시작");
    // 두 번째 문장의 listen 과 세 번째 문장의 listen 까지 본다.
    await waitFor(`document.querySelector('[data-testid=course-sentence-number]')?.textContent === '문장 3 / 5' && document.querySelector('[data-testid=course-phase]')?.dataset.phase === 'listen'`, 60000);
    await shot("S4-third-listen");
    await click("수동"); // 다음 판정 뒤에 멈추게
    await waitFor(`document.querySelector('[data-testid=course-phase]')?.dataset.phase === 'done'`, 30000);
    await sleep(2500);
    note("end", await state());
    note("phases", await ev("window.__phases"));
    note("phasesMO", await ev("window.__phaseMO"));
    note("voices", await ev("speechSynthesis.getVoices().map(v => v.name + '|' + v.lang + '|' + v.localService)"));
  } else if (scenario === "S5") {
    await reload(DAY2_READY);
    note("start", await state());
    let guard = 0;
    while (!(await state()).prevDisabled && guard++ < 30) {
      await click("← 이전");
      await sleep(150);
    }
    note("atDayStart", await state());
    for (let i = 1; i <= 5; i++) {
      await click("다음 문장 →");
      await sleep(200);
      note(`next${i}`, await state());
    }
    await shot("S5-after-5-next");
    await click("← 이전");
    await sleep(200);
    note("prev1", await state());
    await shot("S5-after-prev");
  } else if (scenario === "S6") {
    note("beforeWait", await state());
    await sleep(6500);
    const p = (await api("/api/course/days/2")).progress;
    note("apiProgress", p);
    await reload(DAY2_READY);
    await sleep(500);
    note("afterReload", await state());
    await shot("S6-after-reload");
  } else if (scenario === "S8") {
    await nav(`${APP}/course`, `!!document.querySelector('[data-testid=course-day-6]')`);
    note("day6", await ev(`(() => { const d = document.querySelector('[data-testid=course-day-6]');
      const spans = d.querySelectorAll('span'); const bar = d.querySelector('div > div > div');
      const bars = [...d.querySelectorAll('div')].filter(x => x.style.width);
      return { head: spans[0].textContent, status: spans[1].textContent, barWidth: bars.map(b => b.style.width), resume: d.textContent.includes('이어서 학습') }; })()`));
    note("kstNowBrowser", await ev(`new Intl.DateTimeFormat('en-CA', {timeZone: 'Asia/Seoul'}).format(new Date())`));
    note("utcNowBrowser", new Date().toISOString());
    await shot("S8-course");
  } else if (scenario === "S9") {
    const navAt = Date.now();
    await c.send("Page.navigate", { url: `${APP}/course/2` });
    await waitFor(`location.pathname === '/course/2' && !!(${btn("시작")})`, 15000, 10);
    const readyMs = Date.now() - navAt;
    note("docAgeAtReady", await ev("Math.round(performance.now())"));
    await fakeMic();
    await click("시작");
    note("clickedStartAfterNavMs", Date.now() - navAt);
    note("buttonReadyAfterNavMs", readyMs);
    await sleep(12000);
    note("after12s", await state());
    note("phasesMO", await ev("window.__phaseMO"));
    note("player", await ev(`({ iframe: !!document.querySelector('[data-testid=course-player] iframe'), src: document.querySelector('[data-testid=course-player] iframe')?.src ?? null, YT: typeof window.YT, ytLoaded: !!(window.YT && window.YT.loaded) })`));
    await shot("S9-after");
  } else if (scenario === "S10") {
    const variant = process.argv[3] ?? "wait";
    await nav(`${APP}/course/2`, DAY2_READY);
    await ev("window.__tracks.length = 0");
    await click("시작");
    if (variant === "wait") await waitFor("window.__tracks.length > 0 && document.querySelector('[data-testid=course-phase]')?.dataset.phase === 'listen'", 10000);
    note("tracksBeforeLeave", await ev("window.__tracks.map(t => t.kind + ':' + t.readyState + ':' + t.label)"));
    await waitFor(`(() => { const a = [...document.querySelectorAll('a')].find(a => a.textContent.trim() === '← 학습 목록'); return !!a && Object.keys(a).some(k => k.startsWith('__reactProps')); })()`);
    await ev(`[...document.querySelectorAll('a')].find(a => a.textContent.trim() === '← 학습 목록').click()`);
    await waitFor(`location.pathname === '/course' && !!document.querySelector('[data-testid=course-day-1]')`);
    await sleep(2000);
    note("pathname", await ev("location.pathname"));
    note("tracksAfterLeave", await ev("window.__tracks.map(t => t.kind + ':' + t.readyState + ':' + t.label)"));
    if (process.env.FAKE_MIC_DELAY) await sleep(Number(process.env.FAKE_MIC_DELAY));
    note("tracksAfterDelay", await ev("window.__tracks.map(t => t.kind + ':' + t.readyState + ':' + t.label)"));
    note("gumCalls", await ev("window.__gumCalls ?? 0"));
    note("liveTracks", await ev("window.__tracks.filter(t => t.readyState === 'live').length"));
    note("speaking", await ev("speechSynthesis.speaking"));
  } else if (scenario === "RESET_MODE") {
    await nav(`${APP}/course/2`, DAY2_READY);
    await click("자동");
    await reload(DAY2_READY);
    note("final", await state());
  } else {
    throw new Error(`unknown scenario ${scenario}`);
  }
  note("elapsedMs", Date.now() - t0);
} catch (e) {
  note("ERROR", String(e?.stack ?? e));
  try {
    await shot(`${scenario}-error`);
  } catch {}
} finally {
  writeFileSync(`${EV}/${scenario}${process.argv[3] ? "-" + process.argv[3] : ""}.json`, JSON.stringify(out, null, 1));
  c.close();
}
