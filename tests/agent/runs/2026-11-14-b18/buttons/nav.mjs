// 2단계 — 홈 밖 화면의 이동 버튼. 사용: node nav.mjs <폭>.
// ⚠️ 격리 DB 에는 세션이 하나인 날이 없어(2026-11-14 6개 · 2026-11-01 102개) N6 은 /api/history 응답에서
//    한 날의 sessions 를 1개로 줄인 대역으로 봄. 화면 논리만 판정하고 서버 데이터는 판정하지 않음.
// 영상 화면의 구간 표시는 Save 를 누르지 않음(저장 없음). /videos 의 Check 는 누르지 않음(바깥 조회).
import { APP, connect, newPage, verdicts, shot, waitUrl } from "./lib.mjs";

const W = Number(process.argv[2] ?? 1400);
const V = verdicts(`nav-${W}.json`);
const { ctx } = await connect();
const ZERO = "13869294-9b06-4c75-a56c-6529dcfa7971";
const SPOKEN = "9feb8af1-e7fa-4be1-a9ed-9278f4ae22f4";
const page = await newPage(ctx, W);
const path = () => new URL(page.url()).pathname;
const $ = (tid) => page.locator(`[data-testid="${tid}"]`);

async function go(p, wait) {
  await page.goto(APP + p, { waitUntil: "domcontentloaded" });
  if (wait) await page.waitForSelector(wait, { timeout: 20000 });
  await page.waitForTimeout(800);
}
async function clickTo(id, screen, from, tid, want, extra = {}) {
  await go(from, `[data-testid="${tid}"]`);
  const look = await $(tid).evaluate((e) => ({ omy: e.classList.contains("omy-button"), primary: e.classList.contains("omy-button-primary"), text: e.innerText.trim() }));
  await $(tid).click();
  const ok = await waitUrl(page, (u) => u.pathname === want);
  const lookOk = extra.primary === undefined || look.primary === extra.primary;
  V.add({ id, screen, action: `${tid} 「${look.text}」`, expect: `주소 ${want}${extra.primary === undefined ? "" : extra.primary ? " · 파란 바탕" : " · 회색"}`, actual: `url=${path()} ${JSON.stringify(look)}`, verdict: ok && look.omy && lookOk ? "통과" : "실패" });
}

try {
  await clickTo("N1", "/history", "/history", "history-weekly", "/history/weekly", { primary: true });
  await clickTo("N2", "/history", "/history", "history-home", "/", { primary: false });
  await clickTo("N3", "/history/weekly", "/history/weekly", "weekly-history", "/history", { primary: false });
  await clickTo("N4", "/history/weekly", "/history/weekly", "weekly-home", "/", { primary: false });

  // N5 세션이 여럿인 날 — 줄을 펼쳐 제목 목록에서 고름
  await go("/history", '[data-testid="history-day-group"]');
  const group = $("history-day-group").first();
  const before = await group.evaluate((d) => ({ open: d.open, visible: [...d.querySelectorAll('[data-testid="history-session-link"]')].filter((a) => a.checkVisibility()).length }));
  await group.locator("summary").click();
  await page.waitForTimeout(400);
  const opened = await group.evaluate((d) => ({ open: d.open, links: [...d.querySelectorAll('[data-testid="history-session-link"]')].filter((a) => a.checkVisibility()).map((a) => ({ text: a.innerText.trim(), href: a.getAttribute("href") })) }));
  const summary = (await group.locator("summary").innerText()).replace(/\s+/g, " ").trim();
  const first = opened.links[0];
  await group.locator('[data-testid="history-session-link"]').first().click();
  const okG = first ? await waitUrl(page, (u) => u.pathname === first.href) : false;
  V.add({ id: "N5", screen: "/history", action: "세션 여럿인 날 줄 → 펼침 → 첫 제목", expect: "닫힘(보이는 링크 0) → 펼침(개수 = 줄의 「N lessons」 · 제목이 비지 않음) → 그 /results/<id>", actual: `summary="${summary}" before=${JSON.stringify(before)} opened=${opened.open} links=${opened.links.length} 예=${JSON.stringify(opened.links.slice(0, 3))} url=${path()}`, verdict: !before.open && before.visible === 0 && opened.open && opened.links.length === Number((summary.match(/(\d+) lessons/) ?? [])[1]) && opened.links.every((l) => l.text.length > 1) && okG ? "통과" : "실패" });
  await shot(page, `nav-${W}-result-from-group.png`);

  // N6 세션이 하나인 날(대역) — 줄이 그 결과로 바로 감
  let single = null;
  await page.route("**/api/history", async (route) => {
    const res = await route.fetch();
    const body = await res.json();
    const days = body.days ?? body.rows ?? body.history ?? null;
    const list = Array.isArray(days) ? days : Object.values(body).find((v) => Array.isArray(v) && v.some((r) => r && r.sessions));
    const row = list?.find((r) => (r.sessions ?? []).length > 1);
    if (row) {
      row.sessions = row.sessions.slice(0, 1);
      single = { day: row.day, id: row.sessions[0].session_id };
    }
    await route.fulfill({ response: res, json: body });
  });
  await go("/history", '[data-testid="history-day-link"]');
  const dl = await $("history-day-link").first().evaluate((a) => ({ text: a.innerText.trim(), href: a.getAttribute("href"), omy: a.classList.contains("omy-button") }));
  await $("history-day-link").first().click();
  const okS = single ? await waitUrl(page, (u) => u.pathname === `/results/${single.id}`) : false;
  V.add({ id: "N6", screen: "/history(대역)", action: "세션 하나인 날 줄", expect: "줄이 링크 history-day-link · omy-button 아님(목록 항목) · /results/<그 세션>", actual: `single=${JSON.stringify(single)} link=${JSON.stringify(dl)} url=${path()}`, verdict: single && dl.href === `/results/${single.id}` && !dl.omy && okS ? "통과" : "실패" });
  await page.unroute("**/api/history");

  // 결과 화면
  await clickTo("N7", "/results(발화 있음)", `/results/${SPOKEN}`, "results-home", "/", { primary: false });
  await clickTo("N8", "/results(발화 있음)", `/results/${SPOKEN}`, "results-history", "/history", { primary: true });
  await go(`/results/${ZERO}`, '[data-testid="results-status"]');
  const z = { status: (await $("results-status").innerText()).trim(), done: await $("results-done").count(), body: (await page.locator("main").innerText()).replace(/\s+/g, " ").slice(0, 400) };
  V.add({ id: "N9", screen: "/results(발화 0)", action: "상태 줄 · 완료 문구", expect: "「We didn't hear you this time.」 · 완료 문구(results-done) 숨김 · 마이크 안내", actual: JSON.stringify(z), verdict: /We didn't hear you this time\./.test(z.status) && z.done === 0 && /Check your microphone/.test(z.body) ? "통과" : "실패" });
  await clickTo("N10", "/results(발화 0)", `/results/${ZERO}`, "results-start-again", "/", { primary: true });
  await page.waitForSelector('[data-testid="home-hero"]', { timeout: 20000 }).catch(() => {});
  const heroMode = await $("home-hero").getAttribute("data-mode").catch(() => null);
  V.add({ id: "N10b", screen: "홈(Start again 뒤)", action: "도착한 홈의 카드 상태", expect: "대기 카드(data-mode=idle) — 세션을 스스로 열지 않음", actual: `mode=${heroMode}`, verdict: heroMode === "idle" ? "통과" : "실패" });

  // /course · /course/1 리다이렉트
  for (const [id, p] of [["N11", "/course"], ["N12", "/course/1"]]) {
    const resp = await page.goto(APP + p, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(1500);
    const chain = [];
    for (let r = resp?.request(); r; r = r.redirectedFrom()) chain.unshift(r.url());
    V.add({ id, screen: p, action: "주소 직접 열기", expect: "홈 / 로 넘어감 · 홈 카드 보임", actual: `url=${path()} chain=${JSON.stringify(chain)} hero=${await $("home-hero").count()}`, verdict: path() === "/" && (await $("home-hero").count()) === 1 ? "통과" : "실패" });
  }

  // 영상
  await clickTo("N13", "/videos", "/videos", "videos-home", "/", { primary: false });
  await go("/videos", '[data-testid="videos-home"]');
  const check = page.locator("main").getByRole("button", { name: "Check" });
  const c0 = await check.isDisabled();
  await page.locator("main input").first().fill("https://www.youtube.com/watch?v=dQw4w9WgXcQ");
  const c1 = await check.isDisabled();
  await page.locator("main input").first().fill("");
  V.add({ id: "N14", screen: "/videos", action: "Check(문구로 고름 · 누르지 않음)", expect: "빈칸 disabled → 주소 입력 뒤 enabled", actual: `disabled ${c0}→${c1}`, verdict: c0 && !c1 ? "통과" : "실패" });
  const vHref = await page.locator('main a[href^="/videos/"]').first().getAttribute("href");
  await page.locator('main a[href^="/videos/"]').first().click();
  const okV = await waitUrl(page, (u) => u.pathname === vHref);
  V.add({ id: "N15", screen: "/videos", action: "영상 제목", expect: `주소 ${vHref}`, actual: `url=${path()}`, verdict: okV ? "통과" : "실패" });
  await page.waitForSelector('[data-testid="video-back"]', { timeout: 20000 });
  await page.waitForTimeout(2500);

  // N16 Mark a hard part → End the hard part here · Cancel
  const sec = page.locator("main section").filter({ has: page.getByRole("button", { name: /Mark a hard part|End the hard part here|Cancel/ }) }).first();
  const btns = async () => sec.getByRole("button").evaluateAll((els) => els.map((e) => ({ t: e.innerText.trim(), omy: e.classList.contains("omy-button"), dis: e.disabled })));
  const s0 = await btns();
  await page.getByRole("button", { name: "Mark a hard part" }).click();
  await page.waitForTimeout(600);
  const s1 = await btns();
  const hint = (await sec.innerText()).replace(/\s+/g, " ").trim();
  await page.getByRole("button", { name: "Cancel" }).click();
  await page.waitForTimeout(500);
  const s2 = await btns();
  V.add({ id: "N16", screen: "/videos/<id>", action: "Mark a hard part → Cancel", expect: "「Mark a hard part」 → 「The hard part starts at m:ss. Press the button when it ends.」 + End the hard part here + Cancel → Cancel 로 처음 상태", actual: `${JSON.stringify(s0)} → ${JSON.stringify(s1)} hint="${hint.slice(0, 120)}" → ${JSON.stringify(s2)}`, verdict: s0.map((b) => b.t).join("|") === "Mark a hard part" && s1.map((b) => b.t).join("|") === "End the hard part here|Cancel" && /The hard part starts at \d+:\d\d\. Press the button when it ends\./.test(hint) && s2.map((b) => b.t).join("|") === "Mark a hard part" && [...s0, ...s1].every((b) => b.omy) ? "통과" : "실패" });
  await page.getByRole("button", { name: "Mark a hard part" }).click();
  await page.waitForTimeout(1500);
  await page.getByRole("button", { name: "End the hard part here" }).click();
  await page.waitForTimeout(600);
  const s3 = await btns();
  const hint3 = (await sec.innerText()).replace(/\s+/g, " ").trim();
  await page.getByRole("button", { name: "Cancel" }).click();
  await page.waitForTimeout(500);
  const s4 = await btns();
  V.add({ id: "N17", screen: "/videos/<id>", action: "Mark a hard part → End the hard part here → Cancel(Save 누르지 않음)", expect: "구간 문구 · Save(빈칸이라 disabled) + Cancel → Cancel 로 처음 상태", actual: `${JSON.stringify(s3)} hint="${hint3.slice(0, 120)}" → ${JSON.stringify(s4)}`, verdict: s3.length === 2 && s3[1].t === "Cancel" && s3[0].dis && /again and again/.test(hint3) && s4.map((b) => b.t).join("|") === "Mark a hard part" ? "통과" : "실패" });
  await shot(page, `nav-${W}-video.png`);
  await page.locator('[data-testid="video-back"]').click();
  const okB = await waitUrl(page, (u) => u.pathname === "/videos");
  V.add({ id: "N18", screen: "/videos/<id>", action: "video-back 「← Videos」", expect: "주소 /videos", actual: `url=${path()}`, verdict: okB ? "통과" : "실패" });
} catch (e) {
  V.add({ id: "NX", screen: "nav", action: "드라이버 예외", expect: "-", actual: e.message.split("\n")[0], verdict: "불확실" });
  await shot(page, `nav-${W}-error.png`);
} finally {
  V.flush();
  await page.close();
  process.exit(0);
}
