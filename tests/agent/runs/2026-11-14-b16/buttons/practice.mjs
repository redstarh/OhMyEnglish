// 2단계 — 홈 카드의 문장 연습 버튼(1400). 가짜 마이크 소리는 말이 아니므로 전사·판정 내용은 보지 않고
// 단계 전환·버튼 상태만 판정함. ⚠️ 시도(course_attempts)와 진도(Day 6 완료 포함)가 격리 DB 에 남음.
import { APP, connect, newPage, verdicts, shot } from "./lib.mjs";

const W = Number(process.argv[2] ?? 1400);
const V = verdicts(`practice-${W}.json`);
const { ctx } = await connect();
const page = await newPage(ctx, W);
const $ = (tid) => page.locator(`[data-testid="${tid}"]`);
const num = async () => (await $("course-sentence-number").innerText()).trim();

// 단계 기록기 — data-phase 의 변화를 페이지 안에서 모음(관측 누락을 막으려고 폴링이 아니라 관찰자를 씀).
async function armPhases() {
  await page.evaluate(() => {
    window.__phases = [];
    let last = null;
    const read = () => {
      const el = document.querySelector('[data-testid="course-phase"]');
      const p = el ? el.dataset.phase : "idle";
      if (p !== last) {
        window.__phases.push([Math.round(performance.now()), p, document.querySelector('[data-testid="course-sentence-number"]')?.textContent]);
        last = p;
      }
    };
    read();
    window.__phaseObs?.disconnect();
    window.__phaseObs = new MutationObserver(read);
    window.__phaseObs.observe(document.body, { subtree: true, childList: true, attributes: true, characterData: true });
  });
}
const phases = () => page.evaluate(() => window.__phases.map((x) => x[1]));
const phaseLog = () => page.evaluate(() => window.__phases);
async function waitPhase(p, ms = 40000) {
  await page.waitForFunction((pp) => (document.querySelector('[data-testid="course-phase"]')?.dataset.phase ?? "idle") === pp, p, { timeout: ms });
}

try {
  await page.goto(APP + "/", { waitUntil: "domcontentloaded" });
  await page.waitForSelector('[data-testid="home-hero"][data-state="ready"]', { timeout: 15000 });
  await page.waitForTimeout(800);
  await $("start-session").click();
  await page.waitForSelector('[data-testid="course-start"]', { timeout: 10000 });
  await page.waitForTimeout(500);

  // P1 Manual
  await $("course-mode-manual").click();
  const pm = await $("course-mode-manual").getAttribute("aria-pressed");
  const pa = await $("course-mode-auto").getAttribute("aria-pressed");
  const ls = await page.evaluate(() => localStorage.getItem("omy.course.mode"));
  V.add({ id: "P1", screen: "home-practice", action: "Manual", expect: "manual aria-pressed=true · auto=false · localStorage manual", actual: `manual=${pm} auto=${pa} ls=${ls}`, verdict: pm === "true" && pa === "false" && ls === "manual" ? "통과" : "실패" });

  // P2 Manual Start → ① → ② → ③ · 끝나면 그 문장에 머묾
  const n0 = await num();
  await armPhases();
  await $("course-start").click();
  await page.waitForTimeout(300);
  const retryShown = await $("course-retry").count();
  await waitPhase("done");
  await page.waitForTimeout(2500); // 수동이면 자동 전진(1.5s)이 없어야 함
  const seq = await phases();
  const n1 = await num();
  const label = (await $("course-phase").innerText()).trim();
  V.add({
    id: "P2", screen: "home-practice", action: "Start(수동)",
    expect: "단계 idle→listen→repeat→judge→done · Start 자리가 Try again · 끝나도 같은 문장",
    actual: `phases=${seq.join(">")} retry=${retryShown} label="${label}" 문장 ${n0}→${n1}`,
    verdict: seq.join(">") === "idle>listen>repeat>judge>done" && retryShown === 1 && n0 === n1 ? "통과" : "실패",
    evidence: await phaseLog(),
  });
  await shot(page, `practice-${W}-done.png`);

  // P3 Try again → 단계를 처음부터 다시
  await armPhases();
  await $("course-retry").click();
  await waitPhase("done");
  const seq3 = await phases();
  V.add({ id: "P3", screen: "home-practice", action: "Try again", expect: "done→listen→repeat→judge→done", actual: `phases=${seq3.join(">")}`, verdict: seq3.join(">") === "done>listen>repeat>judge>done" ? "통과" : "실패" });

  // P4 Next → 다음 문장 · 대기
  await $("course-next").click();
  await page.waitForTimeout(500);
  const n4 = await num();
  const ph4 = await $("course-phase").count();
  const st4 = await $("course-start").count();
  V.add({ id: "P4", screen: "home-practice", action: "Next →(수동)", expect: "문장 번호 +1 · 단계 표시 없음 · Start 보임", actual: `${n1}→${n4} phase=${ph4} start=${st4}`, verdict: n4 !== n1 && ph4 === 0 && st4 === 1 ? "통과" : "실패" });

  // P5 Back → 앞 문장
  await $("course-prev").click();
  await page.waitForTimeout(500);
  const n5 = await num();
  V.add({ id: "P5", screen: "home-practice", action: "← Back", expect: `문장 ${n1} 로 돌아감`, actual: `${n4}→${n5}`, verdict: n5 === n1 ? "통과" : "실패" });

  // P6 Auto Start → done 뒤 다음 문장으로 스스로 넘어가 listen 을 다시 시작
  await $("course-mode-auto").click();
  const pa6 = await $("course-mode-auto").getAttribute("aria-pressed");
  await armPhases();
  await $("course-start").click();
  await waitPhase("done");
  await page.waitForFunction((n) => {
    const t = document.querySelector('[data-testid="course-sentence-number"]')?.textContent?.trim();
    return t && t !== n;
  }, n5, { timeout: 8000 }).catch(() => {});
  await page.waitForTimeout(400);
  const n6 = await num();
  const log6 = await phaseLog();
  const seq6 = log6.map((x) => x[1]);
  V.add({
    id: "P6", screen: "home-practice", action: "Auto · Start",
    expect: "auto aria-pressed=true · done 뒤 문장 번호 +1 · listen 재개",
    actual: `auto=${pa6} phases=${seq6.join(">")} 문장 ${n5}→${n6}`,
    verdict: pa6 === "true" && n6 !== n5 && seq6.lastIndexOf("listen") > seq6.indexOf("done") ? "통과" : "실패",
    evidence: log6,
  });

  // P7 연습 도중 Close → 대기 카드 (도는 연습이 멈춤)
  await $("practice-close").click();
  await page.waitForTimeout(800);
  const m7 = await $("home-hero").getAttribute("data-mode");
  V.add({ id: "P7", screen: "home-practice", action: "← Close(자동 연습 도중)", expect: "data-mode=idle", actual: `mode=${m7}`, verdict: m7 === "idle" ? "통과" : "실패" });

  // P8 마지막 문장의 Finish Day — Day 6(단원 101–113)
  await $("home-path-all").click();
  await $("path-day-6").click();
  await page.waitForSelector('[data-testid="course-start"]', { timeout: 10000 });
  await $("course-mode-manual").click();
  let clicks = 0;
  while ((await $("course-finish").count()) === 0 && clicks < 300) {
    await $("course-next").click();
    clicks += 1;
  }
  const lastNum = await num();
  const lastUnit = (await $("course-unit").innerText()).trim();
  const nextGone = await $("course-next").count();
  const finDisabled0 = await $("course-finish").isDisabled();
  const finPrimary = await $("course-finish").evaluate((e) => e.classList.contains("omy-button-primary"));
  await $("course-start").click();
  await waitPhase("done");
  const finDisabled1 = await $("course-finish").isDisabled();
  await $("course-finish").click();
  await page.waitForTimeout(1200);
  const notice = (await $("course-notice").innerText().catch(() => "")).trim();
  const afterNum = await num();
  const afterUnit = (await $("course-unit").innerText()).trim();
  V.add({
    id: "P8", screen: "home-practice", action: "Finish Day(Day 6 마지막 문장)",
    expect: "마지막 문장에서 Next 대신 Finish Day(파란 바탕) · done 전 disabled · 누르면 안내 \"You finished this Day!\" · 첫 문장으로 되감음",
    actual: `Next ${clicks}회 → ${lastUnit} ${lastNum} next=${nextGone} primary=${finPrimary} disabled ${finDisabled0}→${finDisabled1} notice="${notice}" 뒤 ${afterUnit} ${afterNum}`,
    verdict: nextGone === 0 && finPrimary && finDisabled0 && !finDisabled1 && notice === "You finished this Day!" && /Sentence 1 \//.test(afterNum) && /Unit 101\b/.test(afterUnit) ? "통과" : "실패",
  });
  await shot(page, `practice-${W}-finished.png`);
  await $("practice-close").click();
  await page.waitForTimeout(800);
} catch (e) {
  V.add({ id: "PX", screen: "home-practice", action: "드라이버 예외", expect: "-", actual: e.message.split("\n")[0], verdict: "불확실" });
  await shot(page, `practice-${W}-error.png`);
} finally {
  V.flush();
  await page.close();
  process.exit(0);
}
