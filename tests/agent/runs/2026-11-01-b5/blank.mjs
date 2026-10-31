// 회차 b5 — 화면을 about:blank 로 비운다(언마운트 저장이 한 번 나감).
import { connect, pageTarget, sleep } from "./cdp.mjs";
const c = await connect((await pageTarget()).webSocketDebuggerUrl);
await c.send("Page.enable"); await c.send("Page.navigate", { url: "about:blank" }); await sleep(1500); c.close();
