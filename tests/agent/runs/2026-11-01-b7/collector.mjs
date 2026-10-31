// 회차 2026-11-01-b7 — 상시 수집기. 사용: TAG=<라벨> node collector.mjs
// ⑴ 콘솔·예외·네트워크 실패 → evidence/console-<TAG>.jsonl
// ⑵ 시도 POST 와 그 응답 본문 → evidence/attempts.jsonl (Nova 호출 계수의 정본)
// ⑶ 새 문서마다 관측 스크립트: 단계 기록 · getUserMedia 결과 스트림의 입력 세기(20ms 간격 RMS).
//    getUserMedia 는 원래 함수를 그대로 부르고 결과 스트림에 분석기를 하나 더 붙일 뿐이다(앱 동작 불변).
import { appendFileSync, writeFileSync } from "node:fs";
import { connect, pageTarget, EV } from "./cdp.mjs";
const TAG = process.env.TAG ?? "x";
const OUT = `${EV}/console-${TAG}.jsonl`;
const ATT = `${EV}/attempts.jsonl`;
const INIT = `
(() => {
  window.__phases = []; window.__tracks = []; window.__env = []; window.__gum = [];
  let last = "";
  setInterval(() => {
    const ph = document.querySelector('[data-testid=course-phase]');
    const num = document.querySelector('[data-testid=course-sentence-number]');
    const sig = [ph ? ph.dataset.phase : "none", num ? num.textContent : ""].join("|");
    if (sig !== last) { last = sig; window.__phases.push({ t: Math.round(performance.now()), wall: Date.now(), phase: ph ? ph.dataset.phase : "none", num: num ? num.textContent : "" }); }
  }, 10);
  const md = navigator.mediaDevices;
  if (md && md.getUserMedia) {
    const orig = md.getUserMedia.bind(md);
    md.getUserMedia = async (c) => {
      const t0 = performance.now();
      const s = await orig(c);
      window.__gum.push({ called: Math.round(t0), resolved: Math.round(performance.now()), label: s.getAudioTracks()[0]?.label });
      for (const tr of s.getTracks()) window.__tracks.push(tr);
      try {
        const ac = new AudioContext(); const an = ac.createAnalyser(); an.fftSize = 512;
        ac.createMediaStreamSource(s).connect(an); const buf = new Float32Array(512);
        setInterval(() => { an.getFloatTimeDomainData(buf); let e = 0; for (const v of buf) e += v * v;
          if (window.__env.length < 20000) window.__env.push([Math.round(performance.now()), Math.round(Math.sqrt(e / 512) * 1000)]); }, 20);
      } catch (e) { window.__envErr = String(e); }
      return s;
    };
  }
})();
`;
const log = (f, o) => appendFileSync(f, JSON.stringify({ wall: new Date().toISOString(), tag: TAG, ...o }) + "\n");
const reqs = new Map();
async function attach() {
  const page = await pageTarget();
  const c = await connect(page.webSocketDebuggerUrl);
  c.ws.onclose = () => { log(OUT, { kind: "collector", text: "ws closed — reattach" }); setTimeout(() => attach().catch((e) => log(OUT, { kind: "collector", text: "reattach failed " + e })), 2000); };
  c.on(async (m) => {
    const p = m.params;
    if (m.method === "Runtime.consoleAPICalled") log(OUT, { kind: "console", level: p.type, text: p.args.map((a) => a.value ?? a.description ?? a.type).join(" "), url: p.stackTrace?.callFrames?.[0]?.url });
    else if (m.method === "Runtime.exceptionThrown") { const d = p.exceptionDetails; log(OUT, { kind: "exception", text: d.exception?.description ?? d.text, url: d.url, line: d.lineNumber }); }
    else if (m.method === "Log.entryAdded") log(OUT, { kind: "log", level: p.entry.level, source: p.entry.source, text: p.entry.text, url: p.entry.url });
    else if (m.method === "Network.requestWillBeSent") {
      const q = p.request;
      if (q.url.includes("/attempts")) { reqs.set(p.requestId, q.url); log(ATT, { kind: "attempt-req", method: q.method, url: q.url, bodyBytes: q.postData?.length ?? null, hasPostData: q.hasPostData });
        if (q.method === "POST") { try { const d = await c.send("Network.getRequestPostData", { requestId: p.requestId });
          const raw = d.base64Encoded ? Buffer.from(d.postData, "base64") : Buffer.from(d.postData, "latin1");
          const h = Buffer.alloc(44); h.write("RIFF", 0); h.writeUInt32LE(36 + raw.length, 4); h.write("WAVEfmt ", 8); h.writeUInt32LE(16, 16); h.writeUInt16LE(1, 20); h.writeUInt16LE(1, 22);
          h.writeUInt32LE(16000, 24); h.writeUInt32LE(32000, 28); h.writeUInt16LE(2, 32); h.writeUInt16LE(16, 34); h.write("data", 36); h.writeUInt32LE(raw.length, 40);
          const f = `${EV}/sent-${TAG}-${Date.now()}.wav`; writeFileSync(f, Buffer.concat([h, raw])); log(ATT, { kind: "attempt-pcm-saved", file: f.split("/").pop(), bytes: raw.length, b64: d.base64Encoded });
        } catch (e) { log(ATT, { kind: "attempt-pcm-error", text: String(e) }); } } }
      else if (q.url.includes("/api/course")) log(OUT, { kind: "req", method: q.method, url: q.url, body: q.postData?.slice(0, 300) });
    } else if (m.method === "Network.responseReceived") {
      const r = p.response;
      if (reqs.has(p.requestId)) log(ATT, { kind: "attempt-status", status: r.status, url: r.url });
      if (r.status >= 400) log(OUT, { kind: "http", status: r.status, url: r.url });
    } else if (m.method === "Network.loadingFinished" && reqs.has(p.requestId)) {
      try { const b = await c.send("Network.getResponseBody", { requestId: p.requestId }); log(ATT, { kind: "attempt-body", url: reqs.get(p.requestId), body: b.body }); }
      catch (e) { log(ATT, { kind: "attempt-body-error", text: String(e) }); }
    } else if (m.method === "Network.loadingFailed") log(OUT, { kind: "netfail", text: p.errorText, type: p.type, url: reqs.get(p.requestId) });
    else if (m.method === "Page.frameNavigated" && !p.frame.parentId) log(OUT, { kind: "nav", url: p.frame.url });
  });
  await c.send("Runtime.enable"); await c.send("Log.enable"); await c.send("Network.enable"); await c.send("Page.enable");
  await c.send("Page.addScriptToEvaluateOnNewDocument", { source: INIT });
  log(OUT, { kind: "collector", text: `attached ${page.id}` });
  console.log("collector attached", page.id);
}
await attach();
setInterval(() => {}, 1 << 30);
