// 시나리오 10 — 실패와 복구: 마이크 거부 → 카드 안 실패 상자 → Try again(성공) 또는 ← Home
// 사용: node s10.mjs s10 retry | node s10.mjs s10b home  — 코치 진입 뒤 첫 getUserMedia 한 번만 NotAllowedError 로 거절함(드라이버 쪽 주입)
import { scenario, APP, sleep, byText } from "./board.mjs";
import { slowSocket } from "./slow.mjs";
const [key, branch] = process.argv.slice(2);
const deny = `(() => { const orig = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices); window.__gumLog = [];
  navigator.mediaDevices.getUserMedia = (c) => { if (window.__coach && !window.__denied) { window.__denied = 1; window.__gumLog.push('denied'); return Promise.reject(new DOMException('Permission denied', 'NotAllowedError')); } window.__gumLog.push('allowed'); return orig(c); }; })()`;
const ENTRY = branch === "practice" ? ["마이크를 거부한 상태에서 Start speaking", "start-session"] : ["마이크를 거부한 상태에서 More practice 의 Free talk", "practice-free_talk"];
const { p, step, note, done } = await scenario(key, { init: slowSocket(900) + ";" + deny });
try {
  await p.nav(`${APP}/`); await sleep(2500); await p.ev("window.__coach = 1");
  await step(ENTRY[0], ENTRY[1], { desc: "브라우저가 마이크를 거부함(NotAllowedError 주입)", after: 300 });
  if (branch !== "practice") { await p.waitFor(`!!document.querySelector('[data-testid=session-failed]')`, 15000); await sleep(800);
  note("failed reason: " + (await p.ev(`document.querySelector('[data-testid=session-failed]').dataset.reason`)) + " / " + (await p.text("session-failed"))?.replace(/\n/g, " | ")); }
  if (branch === "retry") {
    await step("카드 안 실패 상자", byText("[data-testid=session-failed] button", /^Try again$/, "[data-testid=session-failed] button: Try again"), { desc: "마이크를 허용하고 다시 시도함", after: 300 });
    await p.waitFor(`document.querySelector('[data-testid=home-hero]')?.dataset.mode === 'session' || location.pathname !== '/'`, 15000, 20); await sleep(1500);
    await step("다시 시도해 세션이 시작됨", null, { scrollTop: true });
    await p.waitFor(`location.pathname.startsWith('/results/')`, 40000, 50); await sleep(3000);
    await step("결과 화면", null, { scrollTop: true });
  } else if (branch === "practice") {
    await p.waitFor(`document.querySelector('[data-testid=practice-day]')?.dataset.state === 'ready'`, 15000); await sleep(800);
    await step("카드 안 문장 연습", "course-start", { desc: "따라 말하기를 시작함(마이크 거부)", after: 300 });
    await sleep(6000);
    note("practice after deny: " + JSON.stringify(await p.sp()));
    await step("마이크 거부 뒤 문장 연습 카드", null, { scrollTop: true });
  } else {
    await step("카드 안 실패 상자", "session-failed-home", { desc: "포기하고 홈 대기로 돌아감" });
    await sleep(800);
    await step("홈 대기로 돌아옴 · 메뉴 잠금이 풀림", null, { scrollTop: true });
    note("navLocked: " + JSON.stringify((await p.sp()).navLocked));
  }
  note("gum: " + JSON.stringify(await p.ev("window.__gumLog").catch(() => "page changed")));
  done(true);
} catch (e) { note("ERROR " + e.message); done(false, e); }
