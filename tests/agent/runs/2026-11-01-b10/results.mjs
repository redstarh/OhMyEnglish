// 회차 b10 — 결과 화면을 새로 열어 글자·한글 줄·스크린샷을 남김. 사용: node results.mjs <라벨> <세션 id> [대기 초]
import { open, APP, API, saver, sleep } from "./lib.mjs";
const [label, sid, waitSec = "6"] = process.argv.slice(2);
const { note, save } = saver(`RESULTS-${label}`);
const p = await open({ width: 1400, height: 1000 });
try {
  const api = await (await fetch(`${API}/api/sessions/${sid}/results`)).json();
  note("apiHasSummary", api.summary != null); note("apiStatus", api.status);
  await p.nav(`${APP}/results/${sid}`);
  await sleep(Number(waitSec) * 1000);
  const t = await p.ev("document.querySelector('main')?.innerText ?? document.body.innerText");
  note("hasTodaysLesson", t.includes("Today's lesson")); note("text", t.slice(0, 8000));
  note("hangul", await p.hangul());
  // 칸별 위치 (스크린샷과 대조용)
  note("headings", await p.ev(`[...document.querySelectorAll('main h1,main h2')].map(h => h.textContent.trim())`));
  await p.shot(`RESULTS-${label}`);
} catch (e) { note("ERROR", String(e?.stack ?? e)); }
finally { save(); p.c.close(); }
