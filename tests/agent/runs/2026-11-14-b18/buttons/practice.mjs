// 2단계 — 홈 문장 연습 버튼. 사용: node practice.mjs <폭>.
// 가짜 SpeechRecognition(b17 live.mjs)을 심고, 판정 요청 `**/attempts/text` 와 진도 저장은 page.route 로 받아
// 가짜 응답을 줌 — 격리 DB 에 시도·진도가 쌓이지 않음. 판정 내용은 보지 않고 단계·버튼·요청 수만 판정함.
import { connect, newPage, verdicts, shot, home, routeCourse, installFakes, save } from "./lib.mjs";

const W = Number(process.argv[2] ?? 1400);
const V = verdicts(`practice-${W}.json`);
const { ctx } = await connect();
await ctx.grantPermissions(["microphone"], { origin: "http://localhost:3000" });
const page = await newPage(ctx, W);
await page.addInitScript(installFakes);
const reqs = await routeCourse(page);
const $ = (tid) => page.locator(`[data-testid="${tid}"]`);
const txt = async (tid) => ((await $(tid).count()) ? (await $(tid).first().innerText()).trim() : null);
const num = () => txt("course-sentence-number");
const tries = async () => Number(((await txt("course-attempts")) ?? "").replace(/\D/g, ""));
const setScript = (s) => page.evaluate((x) => (window.__srScript = x), s);
const heroH = () => page.evaluate(() => Math.round(document.querySelector('[data-testid="home-hero"]').getBoundingClientRect().height * 10) / 10);

async function armPhases() {
  await page.evaluate(() => {
    window.__phases = [];
    let last = null;
    const read = () => {
      const el = document.querySelector('[data-testid="course-phase"]');
      const p = el ? el.dataset.phase : "idle";
      const live = !!document.querySelector('[data-testid="course-live-interim"], [data-testid="course-live-final"]');
      const key = p + (live ? "+live" : "");
      if (key !== last) {
        window.__phases.push([Math.round(performance.now()), key, document.querySelector('[data-testid="course-sentence-number"]')?.textContent]);
        last = key;
      }
    };
    read();
    window.__phaseObs?.disconnect();
    window.__phaseObs = new MutationObserver(read);
    window.__phaseObs.observe(document.body, { subtree: true, childList: true, attributes: true, characterData: true });
  });
}
const phaseLog = () => page.evaluate(() => window.__phases);
const plainSeq = async () => {
  const out = [];
  for (const [, k] of await phaseLog()) {
    const p = k.replace("+live", "");
    if (out[out.length - 1] !== p) out.push(p);
  }
  return out.join(">");
};
async function waitPhase(p, ms = 20000) {
  await page.waitForFunction((pp) => (document.querySelector('[data-testid="course-phase"]')?.dataset.phase ?? "idle") === pp, p, { timeout: ms });
}
async function openPractice() {
  await home(page);
  await $("start-session").click();
  await page.waitForSelector('[data-testid="course-start"], [data-testid="course-retry"]', { timeout: 15000 });
  await page.waitForTimeout(500);
}
const speakScript = async () => {
  const s = ((await txt("course-sentence")) ?? "").replace(/[.,!?]/g, "");
  const w = s.split(/\s+/);
  return [
    { at: 300, type: "interim", text: w.slice(0, 2).join(" ") },
    { at: 900, type: "interim", text: w.slice(0, 4).join(" ") },
    { at: 1800, type: "final", text: s },
  ];
};

try {
  await page.goto("http://localhost:3000/", { waitUntil: "domcontentloaded" });
  const ko0 = await page.evaluate(() => localStorage.getItem("omy.course.translation"));
  const mode0 = await page.evaluate(() => localStorage.getItem("omy.course.mode"));
  await openPractice();

  // K1 KO 켬 — 문장 아래 번역 · 저장 · 새로 고친 뒤에도 켜짐
  const trBefore = await $("course-translation-text").count();
  const idleH = await heroH();
  await $("course-translation").click();
  await page.waitForTimeout(400);
  const k1 = {
    pressed: await $("course-translation").getAttribute("aria-pressed"),
    text: await txt("course-translation-text"),
    ls: await page.evaluate(() => localStorage.getItem("omy.course.translation")),
    h: await heroH(),
  };
  await shot(page, `practice-${W}-ko-on.png`);
  V.add({ id: "K1", screen: "home-practice", action: "KO 켬", expect: "aria-pressed=true · 문장 아래 course-translation-text 에 한국어 · localStorage 기록 (대조: 켜기 전 번역 0)", actual: `before=${trBefore} ${JSON.stringify(k1)} 끔일 때 카드 ${idleH}`, verdict: trBefore === 0 && k1.pressed === "true" && /[가-힣]/.test(k1.text ?? "") && k1.ls !== null ? "통과" : "실패" });
  await page.reload({ waitUntil: "domcontentloaded" });
  await page.waitForSelector('[data-testid="home-hero"][data-state="ready"]', { timeout: 20000 });
  await page.waitForTimeout(800);
  const idleKoH = await heroH();
  await $("start-session").click();
  await page.waitForSelector('[data-testid="course-start"], [data-testid="course-retry"]', { timeout: 15000 });
  await page.waitForTimeout(500);
  const k2 = { pressed: await $("course-translation").getAttribute("aria-pressed"), text: await txt("course-translation-text"), practiceH: await heroH() };
  V.add({ id: "K2", screen: "home-practice", action: "KO 켬 → 새로 고침 → Start speaking", expect: "KO 가 켜진 채 · 번역 보임", actual: `${JSON.stringify(k2)} 대기 카드(KO 켬) ${idleKoH}`, verdict: k2.pressed === "true" && /[가-힣]/.test(k2.text ?? "") ? "통과" : "실패" });
  await $("course-translation").click();
  await page.waitForTimeout(400);
  const k3a = { pressed: await $("course-translation").getAttribute("aria-pressed"), tr: await $("course-translation-text").count() };
  await page.reload({ waitUntil: "domcontentloaded" });
  await page.waitForSelector('[data-testid="home-hero"][data-state="ready"]', { timeout: 20000 });
  await page.waitForTimeout(800);
  await $("start-session").click();
  await page.waitForSelector('[data-testid="course-start"], [data-testid="course-retry"]', { timeout: 15000 });
  await page.waitForTimeout(500);
  const k3b = { pressed: await $("course-translation").getAttribute("aria-pressed"), tr: await $("course-translation-text").count() };
  V.add({ id: "K3", screen: "home-practice", action: "KO 끔 → 새로 고침", expect: "끈 직후 번역 0 · 새로 고친 뒤에도 끔", actual: `끈 직후 ${JSON.stringify(k3a)} · 새로 고친 뒤 ${JSON.stringify(k3b)}`, verdict: k3a.pressed === "false" && k3a.tr === 0 && k3b.pressed === "false" && k3b.tr === 0 ? "통과" : "실패" });

  // P1 Manual
  await $("course-mode-manual").click();
  const p1 = { manual: await $("course-mode-manual").getAttribute("aria-pressed"), auto: await $("course-mode-auto").getAttribute("aria-pressed"), ls: await page.evaluate(() => localStorage.getItem("omy.course.mode")) };
  V.add({ id: "P1", screen: "home-practice", action: "Manual", expect: "manual aria-pressed=true · auto=false · localStorage manual", actual: JSON.stringify(p1), verdict: p1.manual === "true" && p1.auto === "false" && p1.ls === "manual" ? "통과" : "실패" });

  // P2 Start → ① Listen → ② Say it(실시간 줄) → ③ Check → 판정
  const n0 = await num();
  const try0 = await tries();
  await setScript(await speakScript());
  await armPhases();
  const posts0 = reqs.posts.length;
  await $("course-start").click();
  await page.waitForSelector('[data-testid="course-live-interim"]', { timeout: 10000 });
  const liveText = await txt("course-live-interim");
  const postsAtLive = reqs.posts.length;
  await shot(page, `practice-${W}-live.png`);
  const labels = [];
  await waitPhase("done");
  await page.waitForTimeout(2500); // 수동이면 앞으로 넘어가지 않아야 함
  const log2 = await phaseLog();
  const seq2 = await plainSeq();
  const liveDuringRepeat = log2.some(([, k]) => k === "repeat+live");
  const p2 = { n: await num(), try1: await tries(), retry: await $("course-retry").count(), start: await $("course-start").count(), verdicts: await page.locator('[data-testid="course-spoken"] [data-verdict]').count(), live: await $("course-live").count(), label: await txt("course-phase") };
  await shot(page, `practice-${W}-judged.png`);
  V.add({
    id: "P2", screen: "home-practice", action: "Start(수동) → ① → ② → ③ → 판정",
    expect: "단계 idle>listen>repeat>judge>done · repeat 중 실시간 줄(POST 전) · POST 1 · 판정 낱말 표시 · Try 증가 · Start 자리가 Try again · 같은 문장에 머묾",
    actual: `seq=${seq2} liveInRepeat=${liveDuringRepeat} live="${liveText}" postsAtLive=${postsAtLive - posts0} posts=${reqs.posts.length - posts0} ${JSON.stringify(p2)} 문장 ${n0}→${p2.n} try ${try0}→${p2.try1}`,
    verdict: seq2 === "idle>listen>repeat>judge>done" && liveDuringRepeat && postsAtLive === posts0 && reqs.posts.length - posts0 === 1 && p2.verdicts > 0 && p2.try1 > try0 && p2.retry === 1 && p2.start === 0 && p2.n === n0 && p2.live === 0 ? "통과" : "실패",
    evidence: log2,
  });

  // P3 Try again
  await setScript(await speakScript());
  await armPhases();
  const posts3 = reqs.posts.length;
  const try3 = await tries();
  await $("course-retry").click();
  await waitPhase("done");
  await page.waitForTimeout(400);
  const seq3 = await plainSeq();
  V.add({ id: "P3", screen: "home-practice", action: "Try again", expect: "done>listen>repeat>judge>done · POST +1 · Try 증가", actual: `seq=${seq3} posts+${reqs.posts.length - posts3} try ${try3}→${await tries()}`, verdict: seq3 === "done>listen>repeat>judge>done" && reqs.posts.length - posts3 === 1 && (await tries()) > try3 ? "통과" : "실패" });

  // U1 말 없음 — Try 가 늘지 않고 「I couldn't hear you」
  await setScript([]);
  const postsU = reqs.posts.length;
  const tryU = await tries();
  const tU = Date.now();
  await $("course-retry").click();
  await page.waitForFunction(() => /couldn't hear you/.test(document.querySelector('[data-testid="course-notice"]')?.textContent ?? ""), null, { timeout: 12000 }).catch(() => {});
  const elapsedU = Date.now() - tU;
  const noticeU = await txt("course-notice");
  await page.waitForTimeout(500);
  V.add({ id: "U1", screen: "home-practice", action: "말 없음(인식 결과 0)", expect: "「I couldn't hear you」 안내 · POST 없음 · Try 그대로", actual: `notice="${noticeU}" ${elapsedU}ms posts+${reqs.posts.length - postsU} try ${tryU}→${await tries()}`, verdict: /couldn't hear you/.test(noticeU ?? "") && reqs.posts.length === postsU && (await tries()) === tryU ? "통과" : "실패" });

  // P4 Next →
  const nBefore = await num();
  await $("course-next").click();
  await page.waitForTimeout(600);
  const p4 = { n: await num(), phase: await $("course-phase").count(), start: await $("course-start").count(), notice: await txt("course-notice") };
  V.add({ id: "P4", screen: "home-practice", action: "Next →(수동)", expect: "문장 번호가 바뀜 · 단계 표시 없음 · Start 보임 · 앞 안내 지움", actual: `${nBefore}→${JSON.stringify(p4)}`, verdict: p4.n !== nBefore && p4.phase === 0 && p4.start === 1 && !p4.notice ? "통과" : "실패" });

  // P5 ← Previous
  const prevLabel = await txt("course-prev");
  await $("course-prev").click();
  await page.waitForTimeout(600);
  const n5 = await num();
  V.add({ id: "P5", screen: "home-practice", action: "← Previous", expect: `문구 「← Previous」 · 문장 ${nBefore} 로 돌아감`, actual: `label="${prevLabel}" ${p4.n}→${n5}`, verdict: prevLabel === "← Previous" && n5 === nBefore ? "통과" : "실패" });

  // P6 Auto · Start → done 뒤 다음 문장으로 넘어가 listen 재개
  await $("course-mode-auto").click();
  const pa = await $("course-mode-auto").getAttribute("aria-pressed");
  await setScript(await speakScript());
  await armPhases();
  const startTid = (await $("course-retry").count()) ? "course-retry" : "course-start";
  await $(startTid).click();
  await waitPhase("done");
  await page.waitForFunction((n) => {
    const t = document.querySelector('[data-testid="course-sentence-number"]')?.textContent?.trim();
    return t && t !== n;
  }, n5, { timeout: 10000 }).catch(() => {});
  await page.waitForTimeout(500);
  const n6 = await num();
  const log6 = await phaseLog();
  const seq6 = log6.map((x) => x[1].replace("+live", ""));
  V.add({ id: "P6", screen: "home-practice", action: "Auto · Start", expect: "auto aria-pressed=true · done 뒤 문장 번호가 바뀌고 listen 재개", actual: `auto=${pa} seq=${seq6.join(">")} 문장 ${n5}→${n6}`, verdict: pa === "true" && n6 !== n5 && seq6.lastIndexOf("listen") > seq6.indexOf("done") ? "통과" : "실패", evidence: log6 });

  // P7 자동 연습 도중 ← Close
  await $("practice-close").click();
  await page.waitForTimeout(800);
  const m7 = await $("home-hero").getAttribute("data-mode");
  const abort7 = await page.evaluate(() => window.__sr.calls.slice(-4).map((c) => c[0]));
  V.add({ id: "P7", screen: "home-practice", action: "← Close(자동 연습 도중)", expect: "data-mode=idle · 인식기가 멈춤", actual: `mode=${m7} 마지막 인식기 호출=${JSON.stringify(abort7)}`, verdict: m7 === "idle" ? "통과" : "실패" });

  // P8 Finish Day — Day 6 마지막 문장
  await $("home-path-all").click();
  await page.waitForTimeout(300);
  await $("path-day-6").click();
  await page.waitForSelector('[data-testid="course-start"], [data-testid="course-retry"]', { timeout: 15000 });
  await $("course-mode-manual").click();
  let clicks = 0;
  while ((await $("course-finish").count()) === 0 && clicks < 300) {
    await $("course-next").click();
    clicks += 1;
  }
  const last = { n: await num(), unit: await txt("course-unit"), next: await $("course-next").count(), disabled: await $("course-finish").isDisabled(), primary: await $("course-finish").evaluate((e) => e.classList.contains("omy-button-primary")) };
  await setScript(await speakScript());
  await $("course-start").click();
  await waitPhase("done");
  const enabled = !(await $("course-finish").isDisabled());
  const prog0 = reqs.progress.length;
  await $("course-finish").click();
  await page.waitForTimeout(1500);
  const after = { notice: await txt("course-notice"), n: await num(), unit: await txt("course-unit") };
  const completedPost = reqs.progress.slice(prog0).find((p) => p.body?.completed === true);
  await shot(page, `practice-${W}-finished.png`);
  V.add({
    id: "P8", screen: "home-practice", action: "Finish Day(Day 6 마지막 문장)",
    expect: "마지막 문장에서 Next 대신 Finish Day(파란 바탕) · done 전 disabled → done 뒤 enabled · 「You finished this Day!」 · 첫 문장으로 되감음 · 완료 저장 요청(completed=true)",
    actual: `Next ${clicks}회 → ${JSON.stringify(last)} enabled=${enabled} after=${JSON.stringify(after)} completedPost=${JSON.stringify(completedPost ?? null)}`,
    verdict: last.next === 0 && last.primary && last.disabled && enabled && after.notice === "You finished this Day!" && /Sentence 1 \//.test(after.n ?? "") && /Unit 101\b/.test(after.unit ?? "") && completedPost ? "통과" : "실패",
  });
  await $("practice-close").click();
  await page.waitForTimeout(600);

  // 처음 저장값으로 되돌림(KO · 모드)
  await page.evaluate(([k, m]) => {
    if (k === null) localStorage.removeItem("omy.course.translation"); else localStorage.setItem("omy.course.translation", k);
    if (m === null) localStorage.removeItem("omy.course.mode"); else localStorage.setItem("omy.course.mode", m);
  }, [ko0, mode0]);
  save(`practice-${W}-storage.json`, { ko0, mode0 });
} catch (e) {
  V.add({ id: "PX", screen: "home-practice", action: "드라이버 예외", expect: "-", actual: e.message.split("\n")[0], verdict: "불확실" });
  await shot(page, `practice-${W}-error.png`);
} finally {
  save(`practice-${W}-requests.json`, { posts: reqs.posts.length, progress: reqs.progress, pcm: reqs.pcm });
  V.flush();
  await page.close();
  process.exit(0);
}
