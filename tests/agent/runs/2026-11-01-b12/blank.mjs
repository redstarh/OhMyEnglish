import { page, dayProgress, sleep } from "./h.mjs";
const p = await page(); await p.c.send("Page.navigate", { url: "about:blank" }); await sleep(1500);
console.log(JSON.stringify({ reqs: p.reqs, day: process.argv[2] ? await dayProgress(Number(process.argv[2])) : null })); p.c.close();
