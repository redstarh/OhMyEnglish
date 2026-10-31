import { open } from "./lib.mjs";
const p = await open();
console.log(JSON.stringify({ href: await p.ev("location.href"), s: await p.state().catch(e => String(e)), phases: await p.ev("window.__phases?.slice(-6)"), gum: await p.ev("window.__gum") }));
p.c.close();
