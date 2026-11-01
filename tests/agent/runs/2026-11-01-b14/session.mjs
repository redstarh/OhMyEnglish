// 회차 b14 — 실제 Nova 대화 세션 1개를 열고 서버 프레임·화면 알림을 기록한 뒤, 끝나면 결과 화면을 봄.
// 사용: node session.mjs <라벨> [최대 초]
// ⛔ 시간 안에 끝나지 않으면 「End lesson」 버튼으로 닫음(유료 세션을 열어 두지 않기 위함). 그 경우 음성 종료는 실패로 기록됨.
import { appendFileSync, writeFileSync } from "node:fs";
import { open, APP, API, EV, saver, sleep } from "./lib.mjs";
const label = process.argv[2], maxSec = Number(process.argv[3] ?? 200);
const { note, save } = saver(`SESSION-${label}`);
const FR = `${EV}/frames-${label}.jsonl`;
const t0 = Date.now();
const rel = () => +((Date.now() - t0) / 1000).toFixed(2);
const p = await open({ width: 1400, height: 1000 });
let sessionId = null, ended = false, audioIn = 0, audioOut = 0, shotN = 0;
const pendingShots = [], shotNotes = [];
const NOTICES = `[...document.querySelectorAll('[data-testid=session-panel] p[aria-live]')].map(e => e.textContent.trim())`;
p.c.on((d) => {
  if (d.method !== "Network.webSocketFrameReceived" && d.method !== "Network.webSocketFrameSent") return;
  const dir = d.method.endsWith("Received") ? "in" : "out";
  const raw = d.params.response.payloadData;
  let m; try { m = JSON.parse(raw); } catch { if (dir === "out") audioOut++; return; }
  if (m.type === "audio") { dir === "in" ? audioIn++ : audioOut++; return; }
  const row = { t: rel(), wall: new Date().toISOString(), dir, ...m };
  if (typeof row.data === "string" && row.data.length > 200) row.data = `<${row.data.length}자>`;
  appendFileSync(FR, JSON.stringify(row) + "\n");
  if (m.type === "session_started") sessionId = m.session_id;
  if (m.type === "session_ended" || m.type === "session_failed") ended = true;
  if (m.type === "voice_command" || m.type === "voice_command_ignored") pendingShots.push(`${m.type}-${m.command}-${m.stage ?? "x"}`);
});
await p.c.send("Network.enable");
try {
  await p.nav(`${APP}/`);
  // 덮개 안의 알림 글자를 변화마다 시각과 함께 남김
  await p.ev(`(() => { window.__t0 = performance.now(); window.__notes = []; let last = '';
    new MutationObserver(() => { const ov = document.querySelector('[data-testid=session-panel]'); if (!ov) return;
      const ps = [...ov.querySelectorAll('p[aria-live]')].map(e => e.textContent.trim()).filter(Boolean);
      const k = ps.join(' | '); if (k !== last) { last = k; window.__notes.push([Math.round(performance.now() - window.__t0), k]); } })
      .observe(document.documentElement, { subtree: true, childList: true, characterData: true }); })()`);
  note("clickAt", rel()); note("click", await p.click(process.env.ENTRY ?? "practice-free_talk", 20000));
  while (!ended && rel() < maxSec) {
    await sleep(250);
    while (pendingShots.length) { const n = pendingShots.shift(); await sleep(600); await p.shot(`SESSION-${label}-${++shotN}-${n}`); shotNotes.push([rel(), n, await p.ev(NOTICES)]); }
    if (await p.ev("location.pathname.startsWith('/results/')")) break;
  }
  note("endedByServer", ended); note("stopAt", rel());
  if (!ended) {
    note("timeoutFallback", "End lesson 버튼으로 닫음"); note("noticesBeforeButton", await p.ev(NOTICES));
    await p.shot(`SESSION-${label}-timeout`);
    await p.ev(`(() => { const b = [...document.querySelectorAll('[data-testid=session-panel] button')].find(b => /End lesson/.test(b.textContent)); if (b) { b.click(); return true; } return false; })()`);
    const st = Date.now(); while (!ended && Date.now() - st < 20000) await sleep(250);
    note("endedAfterButton", ended);
  }
  note("sessionId", sessionId); note("shotNotes", shotNotes);
  note("overlayNotes", await p.ev("window.__notes ?? null").catch(() => null));
  await p.waitFor(`location.pathname.startsWith('/results/') || !!document.querySelector('[data-testid=session-failed]')`, 20000).catch((e) => note("noResultsNav", String(e)));
  note("path", await p.ev("location.pathname"));
  // 요약 미표시 재현: 자동으로 넘어간 결과 화면을 새로 고치지 않고 50초 동안 보며 「Today's lesson」 등장 시각과 API 의 요약 유무를 함께 적음
  const watch = []; const ws0 = Date.now();
  while (sessionId && Date.now() - ws0 < Number(process.env.WATCHMS ?? 50000)) {
    const onPage = await p.ev("(document.querySelector('main')?.innerText ?? '').includes(\"Today's lesson\")").catch(() => null);
    const a = await (await fetch(`${API}/api/sessions/${sessionId}/results`)).json().catch(() => ({}));
    watch.push([Math.round((Date.now() - ws0) / 1000), onPage, a.summary != null, a.status]);
    await sleep(2500);
  }
  note("summaryWatchNoReload", watch);
  await p.shot(`SESSION-${label}-results-noreload`);
  // 분석이 끝날 때까지 API 를 직접 폴링함 (최대 240초)
  let res = null; const st = Date.now();
  while (sessionId && Date.now() - st < Number(process.env.WAITMS ?? 240000)) {
    const r = await fetch(`${API}/api/sessions/${sessionId}/results`); res = { status: r.status, body: await r.json().catch(() => null) };
    if (res.body && !res.body.awaiting_analysis && ["final", "partial_failure", "failed"].includes(res.body.status)) break;
    await sleep(3000);
  }
  note("analysisWaitSec", Math.round((Date.now() - st) / 1000));
  writeFileSync(`${EV}/results-api-${label}.json`, JSON.stringify(res, null, 1));
  note("resultsStatus", res?.body?.status);
  if (sessionId) {
    await p.nav(`${APP}/results/${sessionId}`);
    await sleep(6000);
    note("resultsText", (await p.ev("document.querySelector('main')?.innerText ?? document.body.innerText")).slice(0, 6000));
    note("resultsHangul", await p.hangul());
    await p.shot(`RESULTS-${label}`);
  }
} catch (e) { note("ERROR", String(e?.stack ?? e)); }
finally { note("audioFramesIn", audioIn); note("audioFramesOut", audioOut); note("logs", p.logs.filter((l) => !/DevTools|HMR|Fast Refresh/.test(l.text)).slice(0, 80)); save(); p.c.close(); }
