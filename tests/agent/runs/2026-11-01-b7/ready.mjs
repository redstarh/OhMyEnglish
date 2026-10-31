// 회차 b7 — 플레이어 준비 전 「시작」. 임베드 문서 요청을 HOLD ms 붙잡았다가 풀어, 연습 도중에 플레이어가 준비되게 한다.
// 사용: node ready.mjs <day> <label> [holdMs] [leave]   수동 모드 · 판정 POST 1회. leave 면 repeat 중 영상 상태를 보고 창이 끝나기 전에 떠나 POST 0.
import { open, APP, api, saver, sleep, PORT } from "./lib.mjs";
import { connect } from "./cdp.mjs";
const [DAY, LABEL] = [process.argv[2], process.argv[3]]; const HOLD = Number(process.argv[4] ?? 6000);
const { note, save } = saver(`READY-${LABEL}`);
const p = await open();
const errors = [];
p.c.on((m) => { if (m.method === "Runtime.exceptionThrown") errors.push(m.params.exceptionDetails.exception?.description ?? m.params.exceptionDetails.text); });
const ver = await (await fetch(`http://127.0.0.1:${PORT}/json/version`)).json();
const b = await connect(ver.webSocketDebuggerUrl);
const held = [];
b.on((m) => { if (m.method === "Fetch.requestPaused") { const at = Date.now(); held.push({ url: m.params.request.url.slice(0, 80), at }); setTimeout(() => b.send("Fetch.continueRequest", { requestId: m.params.requestId }).then(() => held.find((h) => h.at === at).releasedAfterMs = Date.now() - at), HOLD); } });
const phaseIs = (ph) => `document.querySelector('[data-testid=course-phase]')?.dataset.phase === '${ph}'`;
async function vstate() {
  const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
  const f = list.filter((t) => t.type === "iframe" && t.url.includes("youtube.com/embed")).at(-1);
  if (!f) return { iframeTarget: false };
  const fc = await connect(f.webSocketDebuggerUrl);
  const r = await Promise.race([fc.send("Runtime.evaluate", { returnByValue: true, expression: `(() => { const v = document.querySelector('video'); const mp = document.querySelector('#movie_player');
    return { t: v ? Math.round(v.currentTime * 100) / 100 : null, paused: v?.paused ?? null, state: mp?.getPlayerState?.() ?? null }; })()` }), sleep(3000).then(() => null)]);
  fc.close(); return r?.result.value ?? { evalTimeout: true };
}
try {
  // 모드를 먼저 수동으로 맞춘다(임베드를 붙잡지 않은 상태에서)
  await p.nav(`${APP}/course/${DAY}`, p.READY);
  if ((await p.state()).mode !== "manual") await p.click("수동");
  note("savedBefore", (await api(`/api/course/days/${DAY}`)).progress);
  await p.nav(`${APP}/course`);
  await b.send("Fetch.enable", { patterns: [{ urlPattern: "*youtube.com/embed/*" }] });
  const t0 = Date.now();
  await p.nav(`${APP}/course/${DAY}`);
  await p.click("시작");
  note("clickAfterNavMs", Date.now() - t0);
  note("playerReadyAtClick", await p.ev(`(() => { const f = document.querySelector('[data-testid=course-player] iframe'); let pl = null; try { pl = f && window.YT && YT.get ? YT.get(f.id) : null; } catch {} return { iframe: !!f, ready: !!(pl && typeof pl.getPlayerState === 'function') }; })()`));
  await p.ev(`(() => { window.__mo2 = []; let last = null; new MutationObserver(() => { const el = document.querySelector('[data-testid=course-phase]'); const ph = el ? el.dataset.phase : 'none';
    const n = document.querySelector('[data-testid=course-notice]')?.textContent ?? ''; const k = ph + '|' + n; if (k !== last) { last = k; window.__mo2.push([Math.round(performance.now()), ph, n]); } })
    .observe(document.body, { subtree: true, childList: true, attributes: true, characterData: true }); })()`);
  if (process.argv[5] === "leave") {
    await p.waitFor(phaseIs("repeat"), 20000, 5);
    const vr = []; for (let i = 0; i < 2; i++) { vr.push({ atMs: Date.now() - t0, phase: await p.ev("document.querySelector('[data-testid=course-phase]')?.dataset.phase"), ...(await vstate()) }); await sleep(600); }
    note("videoDuringRepeat", vr); note("held", held); note("mo2", await p.ev("window.__mo2"));
    await p.c.send("Page.navigate", { url: `${APP}/course` }); await sleep(1500);
    note("savedAfterLeave", (await api(`/api/course/days/${DAY}`)).progress);
    throw new Error("leave-done");
  }
  await p.waitFor(phaseIs("done"), 45000, 10);
  note("doneAfterNavMs", Date.now() - t0);
  note("mo2", await p.ev("window.__mo2"));
  note("phases", await p.ev("window.__phases"));
  note("held", held);
  note("stateAtDone", await p.state());
  const vs = [];
  for (let i = 0; i < 3; i++) { vs.push({ atMs: Date.now() - t0, ...(await vstate()) }); await sleep(2000); }
  note("videoAfterDone", vs);
  await sleep(5500);
  note("savedAfter", (await api(`/api/course/days/${DAY}`)).progress);
  await p.shot(`READY-${LABEL}`);
} catch (e) { note("ERROR", String(e?.stack ?? e)); try { note("mo2", await p.ev("window.__mo2")); note("held", held); } catch {} }
finally { note("exceptions", errors); try { await b.send("Fetch.disable"); } catch {} b.close(); save(); p.c.close(); }
