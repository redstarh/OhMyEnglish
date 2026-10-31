// 회차 2026-11-01-b3 — 상시 수집기. 회차 내내 붙어 있으면서
// ⑴ 콘솔·예외·네트워크 실패를 evidence/console-all.jsonl 에 남기고
// ⑵ 새 문서마다 관측 스크립트(단계 기록·getUserMedia 트랙 기록)를 심는다.
// 관측 스크립트는 앱 동작을 바꾸지 않는다 — getUserMedia 는 원래 함수를 그대로 부르고 결과 트랙만 기록한다.
import { appendFileSync } from "node:fs";
import { connect, pageTarget, EV } from "./cdp.mjs";

const OUT = `${EV}/console-all.jsonl`;
const INIT = `
(() => {
  window.__phases = [];
  window.__tracks = [];
  let last = "";
  setInterval(() => {
    const ph = document.querySelector('[data-testid=course-phase]');
    const num = document.querySelector('[data-testid=course-sentence-number]');
    const unit = document.querySelector('[data-testid=course-unit]');
    const notice = document.querySelector('[data-testid=course-notice]');
    const sig = [ph ? ph.dataset.phase : "none", num ? num.textContent : "", unit ? unit.textContent : "", notice ? notice.textContent : ""].join("|");
    if (sig !== last) {
      last = sig;
      window.__phases.push({ t: Math.round(performance.now()), wall: Date.now(), phase: ph ? ph.dataset.phase : "none", label: ph ? ph.textContent : "", num: num ? num.textContent : "", unit: unit ? unit.textContent : "", notice: notice ? notice.textContent : "" });
    }
  }, 20);
  const md = navigator.mediaDevices;
  if (md && md.getUserMedia) {
    const orig = md.getUserMedia.bind(md);
    md.getUserMedia = async (c) => {
      const s = await orig(c);
      for (const tr of s.getTracks()) window.__tracks.push(tr);
      return s;
    };
  }
})();
`;

const page = await pageTarget();
const c = await connect(page.webSocketDebuggerUrl);
const log = (o) => appendFileSync(OUT, JSON.stringify({ wall: new Date().toISOString(), ...o }) + "\n");
c.on((m) => {
  if (m.method === "Runtime.consoleAPICalled") {
    log({
      kind: "console",
      level: m.params.type,
      text: m.params.args.map((a) => a.value ?? a.description ?? a.type).join(" "),
      url: m.params.stackTrace?.callFrames?.[0]?.url,
    });
  } else if (m.method === "Runtime.exceptionThrown") {
    const d = m.params.exceptionDetails;
    log({ kind: "exception", text: d.exception?.description ?? d.text, url: d.url, line: d.lineNumber });
  } else if (m.method === "Log.entryAdded") {
    log({ kind: "log", level: m.params.entry.level, source: m.params.entry.source, text: m.params.entry.text, url: m.params.entry.url });
  } else if (m.method === "Network.responseReceived") {
    const r = m.params.response;
    if (r.status >= 400 || r.url.includes("/api/course")) log({ kind: "http", status: r.status, url: r.url, method: m.params.type });
  } else if (m.method === "Network.requestWillBeSent") {
    const q = m.params.request;
    if (q.url.includes("/api/course")) log({ kind: "req", method: q.method, url: q.url, body: q.postData?.slice(0, 300) });
  } else if (m.method === "Network.loadingFailed") {
    log({ kind: "netfail", text: m.params.errorText, type: m.params.type, blocked: m.params.blockedReason });
  } else if (m.method === "Page.frameNavigated" && !m.params.frame.parentId) {
    log({ kind: "nav", url: m.params.frame.url });
  }
});
await c.send("Runtime.enable");
await c.send("Log.enable");
await c.send("Network.enable");
await c.send("Page.enable");
await c.send("Page.addScriptToEvaluateOnNewDocument", { source: INIT });
log({ kind: "collector", text: `attached ${page.id}` });
console.log("collector attached", page.id);
setInterval(() => {}, 1 << 30);
