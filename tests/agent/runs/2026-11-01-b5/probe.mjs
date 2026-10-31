// 회차 b5 — 영상 클릭 재생이 되는지만 본다(진단용).
import { connect, pageTarget, sleep, PORT } from "./cdp.mjs";
const c = await connect((await pageTarget()).webSocketDebuggerUrl);
const ev = async (e) => (await c.send("Runtime.evaluate", { expression: e, returnByValue: true })).result.value;
const ids = async () => (await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json()).filter(t => t.type === "iframe").map(t => t.id.slice(0, 8));
console.log("before", await ids());
const b = await ev(`(() => { const r = document.querySelector('[data-testid=course-player] iframe').getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2, w: r.width, h: r.height }; })()`);
console.log(b);
for (const type of ["mousePressed", "mouseReleased"]) await c.send("Input.dispatchMouseEvent", { type, x: b.x, y: b.y, button: "left", clickCount: 1 });
for (let i = 0; i < 4; i++) { await sleep(1500); console.log(i, await ids()); }
c.close();
