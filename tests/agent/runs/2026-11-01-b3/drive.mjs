// 회차 2026-11-01-b3 — 시나리오 실행기. 사용: node drive.mjs <S1|S2|...>
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
const DAY2_READY = `!!document.querySelector('[data-testid=course-sentence]') && !!(${btn("시작")} || ${btn("다시")})`;
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
  } else if (scenario === "SLOW") {
    // 느리게: 같은 문장을 보통(🔊 듣기)·느리게 각각 2번 읽게 하고 listen 시간을 MO 로 잰다. 수동 모드.
    const day = process.argv[3] ?? "2";
    await nav(`${APP}/course/${day}`, DAY2_READY);
    if ((await state()).manual !== "true") await click("수동");
    note("before", await state());
    const runs = [];
    for (const label of ["🔊 듣기", "느리게", "🔊 듣기", "느리게"]) {
      const n0 = await ev("window.__phaseMO.length");
      await click(label);
      await waitFor(`window.__phaseMO.slice(${n0}).some(p => p.phase === 'done')`, 40000, 20);
      const seq = await ev(`window.__phaseMO.slice(${n0})`);
      const L = seq.find((p) => p.phase === "listen"), Rp = seq.find((p) => p.phase === "repeat");
      const waitLabel = await ev(`document.querySelector('[data-testid=course-phase]')?.textContent`);
      runs.push({ label, listenMs: Rp && L ? Rp.t - L.t : null, seq, num: (await state()).num });
      await sleep(800);
    }
    note("runs", runs);
    note("sentence", (await state()).sentence);
    note("after", await state());
  } else if (scenario === "RETRY_MANUAL") {
    await nav(`${APP}/course/2`, DAY2_READY);
    if ((await state()).manual !== "true") await click("수동");
    const before = await state();
    note("before", before);
    let n0 = await ev("window.__phaseMO.length");
    await click("시작");
    await waitFor(`window.__phaseMO.slice(${n0}).some(p => p.phase === 'done')`, 40000, 20);
    await sleep(2500);
    note("afterFirst", await state());
    note("buttonLabelAtDone", await ev(`[...document.querySelectorAll('[data-testid=course-card] button')].map(b => b.textContent.trim())`));
    n0 = await ev("window.__phaseMO.length");
    await click("다시");
    await waitFor(`window.__phaseMO.slice(${n0}).some(p => p.phase === 'done')`, 40000, 20);
    note("retrySeq", await ev(`window.__phaseMO.slice(${n0})`));
    await sleep(2500);
    note("afterRetry", await state());
  } else if (scenario === "AUTO_RETRY") {
    // 자동 모드: 시작 → (s_k repeat 중) 다시 → s_k listen 부터 다시, 흐름 계속 → (s_k+1 repeat 중) 이전 → s_k 부터 다시, 흐름 계속.
    await nav(`${APP}/course/2`, DAY2_READY);
    if ((await state()).auto !== "true") await click("자동");
    const before = await state();
    note("before", before);
    const n0 = await ev("window.__phaseMO.length");
    const tmark = await ev("Math.round(performance.now())");
    const isPhase = (ph, num) => `document.querySelector('[data-testid=course-phase]')?.dataset.phase === '${ph}'` + (num ? ` && document.querySelector('[data-testid=course-sentence-number]')?.textContent === '${num}'` : "");
    await click("시작");
    await waitFor(isPhase("repeat"), 30000, 10);
    const k = (await state()).num;
    note("k", k);
    const tRetry = await ev("Math.round(performance.now())");
    await click("다시");
    note("tRetryClick", tRetry);
    // 다시 뒤 같은 문장 listen → repeat → done → 다음 문장 listen 이 와야 함
    await waitFor(`(() => { const s = window.__phaseMO.filter(p => p.t >= ${tRetry}); return s.some(p => p.phase === 'listen' && p.num !== ${JSON.stringify(k)}); })()`, 40000, 20);
    const k1 = (await state()).num;
    note("k1", k1);
    await waitFor(isPhase("repeat"), 30000, 10);
    const tPrev = await ev("Math.round(performance.now())");
    await click("← 이전");
    note("tPrevClick", tPrev);
    await waitFor(`(() => { const s = window.__phaseMO.filter(p => p.t >= ${tPrev}); const i = s.findIndex(p => p.phase === 'listen' && p.num === ${JSON.stringify(k)}); return i >= 0 && s.slice(i).some(p => p.phase === 'listen' && p.num === ${JSON.stringify(k1)}); })()`, 40000, 20);
    note("afterPrevContinued", await state());
    await click("수동");
    await waitFor(isPhase("done"), 30000, 10);
    await sleep(2500);
    note("end", await state());
    note("seq", await ev(`window.__phaseMO.filter(p => p.t >= ${tmark})`));
  } else if (scenario === "SPOKEN_REAL") {
    // 실제 경로(stub): 판정 응답이 503 이면 「내가 말한 문장」 이 없어야 하고 안내가 떠야 함.
    await nav(`${APP}/course/2`, DAY2_READY);
    if ((await state()).manual !== "true") await click("수동");
    const n0 = await ev("window.__phaseMO.length");
    await click("🔊 듣기");
    await waitFor(`window.__phaseMO.slice(${n0}).some(p => p.phase === 'done')`, 40000, 20);
    note("state", await state());
    note("spoken", await ev(`document.querySelector('[data-testid=course-spoken]')?.textContent ?? null`));
    note("attemptsLabel", await ev(`document.querySelector('[data-testid=course-attempts]')?.textContent`));
  } else if (scenario === "SPOKEN_SYNTH") {
    // ⚠️ 합성 응답: 판정 POST 응답만 CDP Fetch 로 바꿔 끼운다(본문은 백엔드 compare_readback 으로 만든 값).
    const body = process.env.SYNTH_BODY;
    await c.send("Fetch.enable", { patterns: [{ urlPattern: "*/api/course/sentences/*/attempts", requestStage: "Request" }] });
    const seen = [];
    c.on(async (m) => {
      if (m.method !== "Fetch.requestPaused") return;
      seen.push({ url: m.params.request.url, method: m.params.request.method });
      if (m.params.request.method !== "POST") return c.send("Fetch.continueRequest", { requestId: m.params.requestId });
      await c.send("Fetch.fulfillRequest", { requestId: m.params.requestId, responseCode: 200,
        responseHeaders: [{ name: "Content-Type", value: "application/json" }, { name: "Access-Control-Allow-Origin", value: "http://localhost:3000" }],
        body: Buffer.from(body).toString("base64") });
    });
    await nav(`${APP}/course/2`, DAY2_READY);
    if ((await state()).manual !== "true") await click("수동");
    note("before", await state());
    const n0 = await ev("window.__phaseMO.length");
    await click("🔊 듣기");
    await waitFor(`window.__phaseMO.slice(${n0}).some(p => p.phase === 'done')`, 40000, 20);
    await sleep(300);
    note("state", await state());
    note("intercepted", seen);
    note("spoken", await ev(`(() => { const s = document.querySelector('[data-testid=course-spoken]'); if (!s) return null;
      return { transcript: s.querySelector('[data-testid=course-transcript]')?.textContent,
        words: [...s.querySelectorAll('[data-verdict]')].map(w => ({ word: w.textContent, verdict: w.dataset.verdict, deco: getComputedStyle(w).textDecorationLine })),
        text: s.textContent }; })()`));
    note("attemptsLabel", await ev(`document.querySelector('[data-testid=course-attempts]')?.textContent`));
    await shot("SPOKEN_SYNTH");
    await c.send("Fetch.disable");
  } else if (scenario === "LAYOUT") {
    const day = process.argv[3] ?? "3";
    await nav(`${APP}/course/${day}`, DAY2_READY);
    await waitFor(`!!document.querySelector('[data-testid=course-player] iframe')`, 15000);
    note("layout", await ev(`(() => { const r = (s) => { const e = document.querySelector(s); if (!e) return null; const b = e.getBoundingClientRect(); return { top: Math.round(b.top), left: Math.round(b.left), w: Math.round(b.width), h: Math.round(b.height) }; };
      return { viewport: [innerWidth, innerHeight], player: r('[data-testid=course-player]'), card: r('[data-testid=course-card]'), unit: r('[data-testid=course-unit]'), sentence: r('[data-testid=course-sentence]'), iframeSrc: document.querySelector('[data-testid=course-player] iframe')?.src }; })()`));
    await shot(`LAYOUT-day${day}`);
  } else if (scenario === "RESUME_LIST") {
    // 목록: 진행 중 Day 의 상태 문구 · 강조 · 이어서 학습 → 그 자리
    const day = process.argv[3] ?? "2";
    await nav(`${APP}/course`, `!!document.querySelector('[data-testid=course-day-6]')`);
    await sleep(300);
    const api0 = await api("/api/course");
    note("apiCurrentDay", api0.current_day);
    note("apiCycle", api0.cycle);
    note("apiDays", api0.days.map((d) => ({ day: d.day, p: d.progress && { unit: d.progress.unit, si: d.progress.sentence_index, pos: d.progress.position_sec, cc: d.progress.completed_count, lcd: d.progress.last_completed_date, lca: d.progress.last_completed_at, upd: d.progress.updated_at } })));
    note("rows", await ev(`[...document.querySelectorAll('[data-testid^=course-day-]')].map(d => ({ id: d.dataset.testid, head: d.querySelector('span').textContent, status: d.querySelectorAll('span')[1].textContent, border: d.style.border, link: d.querySelector('a')?.textContent, href: d.querySelector('a')?.getAttribute('href'), bar: [...d.querySelectorAll('div')].map(x => x.style.width).filter(Boolean) }))`));
    note("cycleLabel", await ev(`[...document.querySelectorAll('h1 + span, span')].map(s => s.textContent).find(t => /^\\d+회차$/.test(t))`));
    await shot(`RESUME_LIST-${process.argv[4] ?? "x"}`);
    const label = process.argv[4] === "start" ? "시작하기" : "이어서 학습 ▶";
    if (process.argv[5] !== "noclick") {
      await waitFor(`(() => { const a = document.querySelector('[data-testid=course-day-${day}] a'); return !!a && a.textContent === ${JSON.stringify(label)} && Object.keys(a).some(k => k.startsWith('__reactProps')); })()`, 10000);
      await ev(`document.querySelector('[data-testid=course-day-${day}] a').click()`);
      await waitFor(`location.pathname === '/course/${day}' && !!document.querySelector('[data-testid=course-sentence]')`, 15000);
      await sleep(500);
      await fakeMic();
      note("opened", await state());
      note("pathname", await ev("location.pathname"));
    }
  } else if (scenario === "STEP_NEXT") {
    // 수동 모드로 「다음 문장 →」 을 N 번 누르고 그 자리에서 6초 머문다(5초 저장).
    const day = process.argv[3] ?? "2";
    const n = Number(process.argv[4] ?? "5");
    await nav(`${APP}/course/${day}`, DAY2_READY);
    if ((await state()).manual !== "true") await click("수동");
    note("start", await state());
    for (let i = 0; i < n; i++) { await click("다음 문장 →"); await sleep(150); }
    note("at", await state());
    await sleep(6000);
    note("apiProgress", (await api(`/api/course/days/${day}`)).progress);
  } else if (scenario === "DAY_END") {
    // 마지막 문장에서 시작을 눌러 Day 끝을 만든다. argv: day mode
    const day = process.argv[3];
    const want = process.argv[4];
    await nav(`${APP}/course/${day}`, DAY2_READY);
    if ((await state())[want] !== "true") await click(want === "auto" ? "자동" : "수동");
    note("before", await state());
    note("nextDisabled", await ev(`${btn("다음 문장 →")}?.disabled`));
    note("apiBefore", (await api(`/api/course/days/${day}`)).progress);
    const n0 = await ev("window.__phaseMO.length");
    await click("시작");
    note("clickWallUtc", new Date().toISOString());
    await waitFor(`window.__phaseMO.slice(${n0}).some(p => p.phase === 'done')`, 40000, 20);
    await sleep(want === "auto" ? 3500 : 4000);
    note("seq", await ev(`window.__phaseMO.slice(${n0})`));
    note("after", await state());
    note("afterWallUtc", new Date().toISOString());
    note("apiAfter", (await api(`/api/course/days/${day}`)).progress);
    if (want === "manual") {
      // 수동 모드 학습자가 할 수 있는 다음 행동: 다음 문장 → (disabled 인지) · 목록으로
      note("nextDisabledAtDone", await ev(`${btn("다음 문장 →")}?.disabled`));
    }
    await shot(`DAY_END-${day}-${want}`);
  } else if (scenario === "HEAT_SYNTH") {
    // ⚠️ 합성 응답: GET /api/course 응답의 heatmap·recent 만 바꿔 끼워 칸 색·표 렌더링을 본다.
    const patch = JSON.parse(process.env.HEAT_PATCH);
    await c.send("Fetch.enable", { patterns: [{ urlPattern: "*:8002/api/course", requestStage: "Response" }] });
    c.on(async (m) => {
      if (m.method !== "Fetch.requestPaused") return;
      const b = await c.send("Fetch.getResponseBody", { requestId: m.params.requestId });
      const j = JSON.parse(b.base64Encoded ? Buffer.from(b.body, "base64").toString() : b.body);
      for (const [d, a] of Object.entries(patch.heat)) { const cell = j.heatmap.find((x) => x.date === d); if (cell) cell.attempts = a; }
      j.recent = patch.recent;
      await c.send("Fetch.fulfillRequest", { requestId: m.params.requestId, responseCode: 200, responseHeaders: m.params.responseHeaders, body: Buffer.from(JSON.stringify(j)).toString("base64") });
    });
    await nav(`${APP}/course`, `!!document.querySelector('[data-testid=course-day-6]')`);
    await sleep(500);
    note("cells", await ev(`[...document.querySelectorAll('[data-testid=course-heatmap] [data-attempts]')].filter(i => i.dataset.attempts !== '0').map(i => ({ title: i.title, a: i.dataset.attempts, bg: getComputedStyle(i).backgroundColor }))`));
    note("zeroBg", await ev(`getComputedStyle(document.querySelector('[data-testid=course-heatmap] [data-attempts="0"]')).backgroundColor`));
    note("legend", await ev(`[...document.querySelector('[data-testid=course-heatmap]').nextElementSibling.querySelectorAll('i')].map(i => getComputedStyle(i).backgroundColor)`));
    note("table", await ev(`[...document.querySelectorAll('[data-testid=course-recent] tr')].map(r => [...r.children].map(c => c.textContent))`));
    await shot("HEAT_SYNTH");
    await c.send("Fetch.disable");
  } else if (scenario === "HEAT_REAL") {
    await nav(`${APP}/course`, `!!document.querySelector('[data-testid=course-day-6]')`);
    await sleep(500);
    const j = await api("/api/course");
    note("api", { cells: j.heatmap.length, first: j.heatmap[0], last: j.heatmap.at(-1), nonzero: j.heatmap.filter((x) => x.attempts > 0), recent: j.recent });
    note("dom", await ev(`({ cells: document.querySelectorAll('[data-testid=course-heatmap] [data-attempts]').length,
      nonzero: [...document.querySelectorAll('[data-testid=course-heatmap] [data-attempts]')].filter(i => i.dataset.attempts !== '0').length,
      lastTitle: [...document.querySelectorAll('[data-testid=course-heatmap] [data-attempts]')].at(-1)?.title,
      table: !!document.querySelector('[data-testid=course-recent]'),
      emptyNote: [...document.querySelectorAll('p')].map(p => p.textContent).find(t => t.includes('아직 따라 한')) ?? null })`));
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
