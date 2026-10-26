// 회차 b2 — 일회성 평가: node ev.mjs '<식>'
import { connect, pageTarget } from "./cdp.mjs";
const c = await connect((await pageTarget()).webSocketDebuggerUrl);
const r = await c.send("Runtime.evaluate", { expression: process.argv[2], returnByValue: true, awaitPromise: true });
console.log(JSON.stringify(r.result.value ?? r, null, 1));
c.close();
