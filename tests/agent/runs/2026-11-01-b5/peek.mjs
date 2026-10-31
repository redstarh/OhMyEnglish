import { connect, pageTarget } from "./cdp.mjs";
const c = await connect((await pageTarget()).webSocketDebuggerUrl);
const r = await c.send("Runtime.evaluate", { expression: process.argv[2], returnByValue: true }); console.log(JSON.stringify(r.result.value ?? r)); c.close();
