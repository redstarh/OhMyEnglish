// 시나리오 3·4·5 — 홈 카드에서 세션 진입 → 카드 안 세션 → 결과 화면.
// 사용: node sess.mjs <key> <entry-testid> "<첫 단계 이름>" "<누른 뒤 설명>" [delayMs]
import { scenario, APP, sleep } from "./board.mjs";
import { slowSocket } from "./slow.mjs";
const [key, tid, title, desc, delay = "900"] = process.argv.slice(2);
const { p, step, note, done } = await scenario(key, { init: slowSocket(Number(delay)) });
const lines = `(() => { const s = document.querySelector('[data-testid=session-panel]'); return s ? s.innerText.split('\\n').filter(Boolean).length : -1; })()`;
try {
  await p.nav(`${APP}/`); await sleep(2500);
  await step(title, tid, { desc, after: 200 });
  await p.waitFor(`document.querySelector('[data-testid=home-hero]')?.dataset.mode === 'session' || location.pathname !== '/'`, 10000, 20);
  await sleep(1200);
  await step("카드 안에서 세션이 시작됨", null, { desc: "다른 학습 버튼과 메뉴는 잠김", scrollTop: true });
  await p.waitFor(`${lines} >= 6 || location.pathname.startsWith('/results/')`, 30000, 50).catch((e) => note("lines wait: " + e.message));
  await sleep(1500);
  if (await p.ev(`location.pathname === '/'`)) await step("코치와 주고받은 대화 줄이 카드 안에 쌓임", null, { desc: "stub 픽스처 세 턴", scrollTop: true });
  else note("results reached before conversation shot");
  await p.waitFor(`location.pathname.startsWith('/results/')`, 40000, 50);
  await sleep(3000);
  await step("세션이 끝나 결과 화면으로 넘어감", null, { desc: "이 스택은 분석이 꺼져 있어 Checking… 이 그대로 남음", scrollTop: true });
  note("wsTypes: " + JSON.stringify(await p.ev("window.__wsTypes ?? null").catch(() => "page changed")));
  note("sockets: " + JSON.stringify(p.sockets));
  done(true);
} catch (e) { note("ERROR " + e.message); done(false, e); }
