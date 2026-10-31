// 사전 실행 — 녹음 창이 입력 파일의 몇 초에 걸리는지 잰다. 판정(POST) 전에 문서를 떠나므로 Nova 호출 0.
// 사용: node probe.mjs <label> <sentenceIndex(1-based)>
import { open, APP, saver, sleep } from "./lib.mjs";
const [label, idx] = [process.argv[2], Number(process.argv[3] ?? 4)];
const { out, note, save } = saver(`PROBE-${label}`);
const p = await open();
try {
  await p.nav(`${APP}/course/1`, p.READY);
  await p.click("수동");
  // 지정 문장까지 수동 「다음 문장」으로 옮김 (수동이라 연습이 돌지 않음)
  for (let g = 0; g < 10 && (await p.state()).num !== `문장 ${idx} / 5`; g++) { await p.click((await p.state()).num > `문장 ${idx}` ? "← 이전" : "다음 문장 →"); await sleep(200); }
  note("before", await p.state());
  await p.click("시작");
  await p.waitFor(`document.querySelector('[data-testid=course-phase]')?.dataset.phase === 'repeat'`, 20000, 5);
  await sleep(400);
  note("gum", await p.ev("window.__gum"));
  note("phases", await p.ev("window.__phases"));
  note("env", await p.ev("window.__env.filter(x => x[1] > 5).slice(0, 15)"));
  note("envFirst", await p.ev("window.__env.slice(0, 3)")); await sleep(1500); note("envMax", await p.ev("window.__env.reduce((m, x) => x[1] > m[1] ? x : m, [0, -1])")); note("envLen", await p.ev("window.__env.length")); note("envErr", await p.ev("window.__envErr ?? null"));
  note("waitLabel", await p.ev("document.querySelector('[data-testid=course-phase]')?.textContent"));
} catch (e) { note("ERROR", String(e?.stack ?? e)); }
finally {
  await p.c.send("Page.navigate", { url: "about:blank" }); // 판정 전에 떠남 → POST 없음
  save(); p.c.close();
}
