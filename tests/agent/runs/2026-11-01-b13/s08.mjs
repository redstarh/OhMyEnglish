// 시나리오 8 — 이력과 주간: 사이드바 Review → 이력 → Weekly report → ← History → 사이드바 Progress
import { scenario, APP, sleep, byText } from "./board.mjs";
const { p, step, note, done } = await scenario("s08");
const link = (re, name) => byText("a", re, name);
try {
  await p.nav(`${APP}/`); await sleep(2500);
  await step("홈에서 사이드바 Review", "nav-review", { desc: "학습 이력으로 감" });
  await p.waitFor(`location.pathname === '/history'`, 10000); await sleep(2000);
  await step("이력 화면(위쪽)", null, { desc: "날짜별 학습 기록", scrollTop: true });
  await step("이력 화면(아래쪽 링크)", link(/^Weekly report/, "a: Weekly report →"), { desc: "이번 주 리포트를 엶" });
  await p.waitFor(`location.pathname === '/history/weekly'`, 10000); await sleep(2500);
  await step("주간 리포트", link(/History$/, "a: ← History"), { desc: "이력으로 돌아감" });
  await p.waitFor(`location.pathname === '/history'`, 10000); await sleep(1500);
  await step("이력으로 돌아옴", "nav-progress", { desc: "사이드바 Progress 로도 주간 리포트에 감" });
  await p.waitFor(`location.pathname === '/history/weekly'`, 10000); await sleep(2500);
  await step("주간 리포트 · 사이드바 Progress 가 켜짐", null, { scrollTop: true });
  done(true);
} catch (e) { note("ERROR " + e.message); done(false, e); }
