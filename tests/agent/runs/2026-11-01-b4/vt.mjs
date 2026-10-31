// 회차 b4 — 지금 열린 화면의 YouTube 영상 시각만 읽는다(읽기 전용).
import { connect, PORT } from "./cdp.mjs";
const l = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
const f = l.find((t) => t.type === "iframe" && t.url.includes("youtube.com/embed"));
if (!f) { console.log(JSON.stringify({ frame: false })); process.exit(0); }
const fc = await connect(f.webSocketDebuggerUrl); await fc.send("Runtime.enable");
const r = await fc.send("Runtime.evaluate", { returnByValue: true, expression: `(() => { const v = document.querySelector('video'); const mp = document.querySelector('#movie_player'); return { t: v ? Math.round(v.currentTime*10)/10 : null, paused: v?.paused, state: mp?.getPlayerState?.() }; })()` });
console.log(JSON.stringify({ frame: true, url: f.url.slice(0, 80), ...r.result.value })); fc.close();
