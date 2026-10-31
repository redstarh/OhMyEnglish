import { connect, PORT } from "./cdp.mjs";
const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
const f = list.filter((t) => t.type === "iframe" && t.url.includes("youtube.com/embed")).at(-1);
const fc = await connect(f.webSocketDebuggerUrl);
const r = await fc.send("Runtime.evaluate", { returnByValue: true, expression: `({ url: location.href.slice(0, 120), ready: document.readyState, text: document.body?.innerText?.slice(0, 400), err: document.querySelector('.ytp-error')?.innerText ?? null,
  mp: !!document.querySelector('#movie_player'), cls: document.querySelector('#movie_player')?.className?.slice(0, 300), vsrc: document.querySelector('video')?.src?.slice(0, 60) ?? null, rs: document.querySelector('video')?.readyState })` });
console.log(JSON.stringify(r.result.value, null, 1)); fc.close();
