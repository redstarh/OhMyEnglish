// 열어 둔 문장 연습 화면이 가만히 있으면 진도를 저장하지 않는지 잼(`TASK-347`) — 프런트 :3000 이 떠 있을 때
// `node tests/agent/tools/progress-idle-save.mjs`. 쓰기 요청은 모두 막고 진도 저장만 셈(dev DB 에 닿지 않음).
// ⛔ 고치기 전 실측: 12초 가만히 2건 · 닫을 때 1건 — 낡은 화면이 다른 기기의 진도를 예전 자리로 덮었음.
// ⚠️ 연습은 열리자마자 시작하므로(`TASK-348`) Manual 로 두고 잼 — 자동 모드면 판정 뒤 저장이 섞임.
import { chromium } from "playwright";
const b = await chromium.launch();
const p = await (await b.newContext({ viewport: { width: 393, height: 659 }, isMobile: true, hasTouch: true })).newPage();
const saves = [];
const failures = [];
const check = (ok, msg) => { console.log(`${ok ? "ok  " : "FAIL"} ${msg}`); if (!ok) failures.push(msg); };
await p.route("**/api/**", (r) => {
  if (r.request().method() === "GET") return r.continue();
  if (r.request().url().includes("/progress")) saves.push(r.request().postDataJSON());
  return r.fulfill({ status: 204, body: "" });
});
await p.goto("http://localhost:3000/", { waitUntil: "networkidle" });
await p.evaluate(() => localStorage.setItem("omy.course.mode", "manual"));
await p.getByRole("button", { name: /Start speaking/ }).click();
await p.waitForSelector('[data-testid="course-card"]');
const t0 = saves.length;
await p.waitForTimeout(12000);
check(saves.length - t0 === 0, `가만히 12초 저장 ${saves.length - t0}건`);
await p.getByRole("button", { name: /Close/ }).click(); await p.waitForTimeout(800);
check(saves.length - t0 === 0, `자리를 안 바꾸고 닫음 저장 ${saves.length - t0}건`);
await p.getByRole("button", { name: /Start speaking/ }).click(); await p.waitForSelector('[data-testid="course-card"]');
const t1 = saves.length;
await p.getByTestId("course-next").click(); await p.waitForTimeout(6000);
check(saves.length - t1 >= 1, `Next 로 옮기면 저장 ${saves.length - t1}건 ${JSON.stringify(saves.at(-1))}`);
await b.close();
console.log(failures.length ? `FAILED ${failures.length}` : "ALL PASS");
process.exit(failures.length ? 1 : 0);
