// 회차 b12 — 수집기 판별력 확인: 같은 수집 수단이 console.error 와 잡히지 않은 예외를 잡는가
import { page, APP, sleep } from "./h.mjs";
import { saver } from "./lib.mjs";
const { note, save } = saver("PROBE-logs");
const p = await page();
await p.nav(`${APP}/`); await p.waitFor(p.hydrated("start-session"), 20000); await sleep(1500);
await p.ev(`console.error('b12-probe-console'); setTimeout(() => { throw new Error('b12-probe-throw'); }, 0); true`); await sleep(800);
note("logs", p.logs); save(); p.c.close();
