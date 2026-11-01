// 회차 b15 — TASK-311 화면별 이동 버튼. 사용: node pages.mjs <폭> <포트>
// ⛔ `/course/<day>` 는 열기만 해도 진도를 저장하므로 열지 않음(dev DB).
import { open, APP, saver, sleep } from "./lib.mjs";
const width = Number(process.argv[2] ?? 1400), port = Number(process.argv[3] ?? 9365);
const { note, save } = saver(`pages-${width}`);
const p = await open({ port, width, height: 1000 });
const pages = { course: "/course", history: "/history", weekly: "/history/weekly", results: "/results/f1e0930e-b22f-4e93-b3ec-699ac42d18cd", videos: "/videos", video: "/videos/e5463a72-bc9d-488e-8357-f4dc13ddfa54" };
for (const [name, path] of Object.entries(pages)) {
  await p.nav(`${APP}${path}`); await sleep(2500);
  note(name, await p.ev(`[...document.querySelectorAll('.omy-button')].filter(e => e.getClientRects().length).map(e => { const r = e.getBoundingClientRect(); const s = getComputedStyle(e); return [e.innerText.trim().slice(0, 24), Math.round(r.height), s.fontSize, s.backgroundColor].join(' | '); })`));
  await p.shot(`page-${name}-${width}`);
}
save(); p.c.close();
