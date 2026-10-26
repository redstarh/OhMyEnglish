// 회차 b2 — D2 판별 절차: YouTube 임베드 문서만 막아 플레이어가 onReady 에 이르지 못하게 한 뒤
// 로드 직후 「시작」을 누르고 저장 타이머가 두 번 돌 때까지(12초) 오류를 센다.
import { writeFileSync } from "node:fs";
import { connect, pageTarget, sleep, EV } from "./cdp.mjs";
const c = await connect((await pageTarget()).webSocketDebuggerUrl);
await c.send("Page.enable");
await c.send("Network.enable");
await c.send("Runtime.enable");
const errors = [];
c.on((m) => {
  if (m.method === "Runtime.exceptionThrown") errors.push(m.params.exceptionDetails.exception?.description ?? m.params.exceptionDetails.text);
  if (m.method === "Runtime.consoleAPICalled" && m.params.type === "error") errors.push(m.params.args.map((a) => a.value ?? a.description).join(" "));
});
// 페이지 세션의 setBlockedURLs 는 교차 출처 iframe 문서에 걸리지 않았다(1차 실측) — 브라우저 수준 Fetch 로 막는다.
const ver = await (await fetch("http://127.0.0.1:9333/json/version")).json();
const b = await connect(ver.webSocketDebuggerUrl);
let failed = 0;
b.on((m) => { if (m.method === "Fetch.requestPaused") { failed++; b.send("Fetch.failRequest", { requestId: m.params.requestId, errorReason: "BlockedByClient" }); } });
await b.send("Fetch.enable", { patterns: [{ urlPattern: "*youtube.com/embed/*" }] });
const ev = async (e, gesture = false) => { try { return (await c.send("Runtime.evaluate", { expression: e, returnByValue: true, userGesture: gesture, awaitPromise: true })).result.value; } catch (x) { return String(x); } };
const out = {};
const navAt = Date.now();
await c.send("Page.navigate", { url: "http://localhost:3000/course/2" });
for (let i = 0; i < 300; i++) {
  const ok = await ev(`(() => { const b=[...document.querySelectorAll('button')].find(b=>b.textContent.trim()==='시작'); return !!b && Object.keys(b).some(k=>k.startsWith('__reactProps')); })()`);
  if (ok === true) break;
  await sleep(10);
}
await ev(`(() => { if (window.__fakeMic) return; window.__fakeMic = true; navigator.mediaDevices.getUserMedia = async () => { const ac = new AudioContext(); const o = ac.createOscillator(); const d = ac.createMediaStreamDestination(); o.connect(d); o.start(); return d.stream; }; })()`);
await ev(`[...document.querySelectorAll('button')].find(b=>b.textContent.trim()==='시작').click()`, true);
out.clickAfterNavMs = Date.now() - navAt;
await sleep(12000);
out.player = await ev(`(() => { const f = document.querySelector('[data-testid=course-player] iframe'); let p = null; try { p = f && YT.get ? YT.get(f.id) : null; } catch {}
  return { iframe: !!f, api: !!(window.YT && YT.loaded), playerHasGetCurrentTime: !!(p && typeof p.getCurrentTime === 'function'), notice: document.querySelector('[data-testid=course-notice]')?.textContent ?? null, phase: document.querySelector('[data-testid=course-phase]')?.dataset.phase ?? null }; })()`);
out.errors = errors;
out.getCurrentTimeErrors = errors.filter((e) => /getCurrentTime/.test(e)).length;
await b.send("Fetch.disable"); out.embedRequestsFailed = failed; b.close();
console.log(JSON.stringify(out, null, 1));
writeFileSync(`${EV}/S9-d2-blocked-embed.json`, JSON.stringify(out, null, 1));
c.close();
