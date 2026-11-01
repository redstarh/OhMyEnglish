// 시나리오 9 — 결과 화면: 분석이 끝난 세션(격리 DB 의 c7482f05 · 회차 b10)의 결과 → Practice this → 카드 안 세션 → 새 결과
// /history 에는 세션 행으로 가는 링크가 없어(b11) 결과 화면은 주소로 직접 엶.
import { scenario, APP, sleep, byText } from "./board.mjs";
import { slowSocket } from "./slow.mjs";
const SID = "c7482f05-42ef-42b9-b2ff-89d344d2f7dc";
const { p, step, note, done } = await scenario("s09", { init: slowSocket(900) });
try {
  await p.nav(`${APP}/results/${SID}`); await sleep(3500);
  await step("분석이 끝난 결과 화면", null, { desc: "요약 · 오늘의 실수 · 다음 연습", scrollTop: true });
  await step("오늘의 실수 목록", byText("a,button", /^Practice this$/, "Practice this (첫 번째)"), { desc: "그 패턴으로 바로 연습을 시작함", after: 300 });
  await p.waitFor(`document.querySelector('[data-testid=home-hero]')?.dataset.mode === 'session'`, 15000, 20); await sleep(1500);
  note("entry: " + (await p.ev("location.pathname + location.search")) + " sockets " + JSON.stringify(p.sockets));
  await step("홈 카드 안에서 그 패턴 세션이 시작됨", null, { scrollTop: true });
  await p.waitFor(`location.pathname.startsWith('/results/')`, 40000, 50); await sleep(3000);
  await step("새 결과 화면(분석 꺼짐 → Checking…)", null, { scrollTop: true });
  done(true);
} catch (e) { note("ERROR " + e.message); done(false, e); }
