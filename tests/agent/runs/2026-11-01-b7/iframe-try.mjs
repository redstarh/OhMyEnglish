// 막힌 플레이어에서 학습자가 할 법한 두 동작 — 큰 재생 버튼 클릭, 키 k — 뒤의 상태. 앱 코드는 건드리지 않음.
import { connect, PORT, sleep } from "./cdp.mjs";
import { writeFileSync } from "node:fs";
const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
const f = list.filter((t) => t.type === "iframe" && t.url.includes("youtube.com/embed")).at(-1);
const fc = await connect(f.webSocketDebuggerUrl);
const ev = async (e) => (await fc.send("Runtime.evaluate", { returnByValue: true, userGesture: true, expression: e })).result.value;
const st = `(() => { const v = document.querySelector('video'); const mp = document.querySelector('#movie_player'); const b = document.querySelector('.ytp-large-play-button');
  const r = b?.getBoundingClientRect(); return { t: v ? Math.round(v.currentTime*100)/100 : null, paused: v?.paused, state: mp?.getPlayerState?.(), rs: v?.readyState,
  bigBtn: b ? { display: getComputedStyle(b).display, vis: getComputedStyle(b).visibility, w: Math.round(r.width) } : null, spinner: !!document.querySelector('.ytp-spinner') && getComputedStyle(document.querySelector('.ytp-spinner')).display, cls: mp?.className.match(/\\b[a-z]+-mode\\b/g) }; })()`;
const out = { before: await ev(st) };
await fc.send("Input.dispatchKeyEvent", { type: "keyDown", key: "k", code: "KeyK", text: "k" }); await fc.send("Input.dispatchKeyEvent", { type: "keyUp", key: "k", code: "KeyK" });
await sleep(3000); out.afterKeyK = await ev(st);
await ev(`document.querySelector('.ytp-large-play-button')?.click()`); await sleep(3000); out.afterBigBtnClick = await ev(st);
writeFileSync(process.argv[2], JSON.stringify(out, null, 1)); console.log(JSON.stringify(out)); fc.close();
