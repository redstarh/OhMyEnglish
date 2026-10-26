// 회차 b2 — 일회성 진단: 관측 스크립트가 없는 새 탭에서 getUserMedia 가 끝나는지.
import { connect, PORT, sleep } from "./cdp.mjs";
const t = await (await fetch(`http://127.0.0.1:${PORT}/json/new?${encodeURIComponent(process.argv[2])}`, { method: "PUT" })).json();
const c = await connect(t.webSocketDebuggerUrl);
await sleep(2500);
const r = await c.send("Runtime.evaluate", { expression: `Promise.race([navigator.mediaDevices.getUserMedia({audio:true}).then(s=>{const o="ok "+s.getTracks().map(t=>t.label+":"+t.readyState); s.getTracks().forEach(t=>t.stop()); return o}).catch(e=>"err "+e.name+" "+e.message), new Promise(r=>setTimeout(()=>r("timeout 8s"),8000))])`, returnByValue: true, awaitPromise: true, userGesture: true });
console.log(process.argv[2], JSON.stringify(r.result.value));
c.close();
await fetch(`http://127.0.0.1:${PORT}/json/close/${t.id}`);
