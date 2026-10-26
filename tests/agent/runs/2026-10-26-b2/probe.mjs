// 회차 b2 — 일회성 진단: 현재 위치와 버튼의 React 핸들러 부착 여부.
import { connect, pageTarget, sleep } from "./cdp.mjs";
const c = await connect((await pageTarget()).webSocketDebuggerUrl);
const ev = async (e) => (await c.send("Runtime.evaluate", { expression: e, returnByValue: true, awaitPromise: true, userGesture: true })).result.value;
console.log("path", await ev("location.pathname"));
const hyd = `(() => { const b=[...document.querySelectorAll('button')].find(b=>b.textContent.trim()==='문법 코스'); return b ? Object.keys(b).filter(k=>k.startsWith('__react')).join(',') + ' disabled=' + b.disabled : 'none'; })()`;
console.log("hydration", await ev(hyd));
await ev(`[...document.querySelectorAll('button')].find(b=>b.textContent.trim()==='문법 코스').click()`);
for (let i=0;i<40;i++){ await sleep(250); const p=await ev("location.pathname"); if(p==='/course'){console.log("navigated after", (i+1)*250,"ms"); break;} }
console.log("path", await ev("location.pathname"));
c.close();
