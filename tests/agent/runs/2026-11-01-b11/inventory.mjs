// 회차 b11 — 화면마다 눌 수 있는 요소를 DOM 에서 뽑음. 사용: node inventory.mjs <width> <path...>
import { open, APP, saver, sleep } from "./lib.mjs";
import { ENUM } from "./enum.mjs";
const width = Number(process.argv[2]); const paths = process.argv.slice(3);
const { note, save } = saver(`INV-${width}`);
const p = await open({ port: 9345, width, height: 1000 });
for (const path of paths) {
  try {
    await p.nav(`${APP}${path}`);
    await sleep(3500);
    const items = await p.ev(ENUM);
    note(path, { path: await p.ev("location.pathname"), count: items.length, items, overflow: await p.overflowX() });
    await p.shot(`INV-${width}${path.replace(/\//g, "_") || "_root"}`);
  } catch (e) { note(path + " ERROR", String(e)); }
}
note("logs", p.logs.filter((l) => !/DevTools|HMR|Download the React/.test(l.text)));
save(); p.c.close();
