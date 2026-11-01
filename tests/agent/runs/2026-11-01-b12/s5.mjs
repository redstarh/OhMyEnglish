// 회차 b12 — 시나리오 5: 코치 세션이 카드 안에서 돎 · 문장 연습을 먼저 닫음 · 잠금 · 결과 이동 · 연결 중/실패 카드 높이.
// 사용: node s5.mjs <label> <width> <entry-testid> <plain|delay|deny> <none|open|started>
//  open    : 문장 연습을 열어 둔 채 진입 · started : 연습에서 Start 를 한 번 눌러 마이크를 잡은 뒤 진입
import { page, APP, sleep, BOXES } from "./h.mjs";
import { saver } from "./lib.mjs";
const [label, W, tid, mode, pre] = process.argv.slice(2);
const { note, save } = saver(`S5-${label}`);
const p = await page({ width: Number(W), height: 1000 });
// getUserMedia 기록(트랙 상태를 나중에 읽음) + 지연/거절
await p.c.send("Page.addScriptToEvaluateOnNewDocument", { source: `(() => { const orig = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices); window.__gum = []; let n = 0;
  navigator.mediaDevices.getUserMedia = (c) => { n++; const k = n; const stack = (new Error().stack || '').split('\\n').slice(2, 4).join(' | ').slice(0, 200);
    const go = () => orig(c).then(s => { window.__gum.push({ k, stack, tracks: s.getTracks() }); return s; });
    if (${JSON.stringify(mode)} === 'delay' && window.__coach && !window.__delayed) { window.__delayed = 1; return new Promise(r => setTimeout(r, 12000)).then(go); }
    if (${JSON.stringify(mode)} === 'deny' && window.__coach && !window.__denied) { window.__denied = 1; return Promise.reject(new DOMException('Permission denied', 'NotAllowedError')); }
    return go(); }; })()` });
const GUM = `window.__gum.map(g => ({ k: g.k, stack: g.stack, states: g.tracks.map(t => t.readyState) }))`;
try {
  await p.nav(`${APP}/`); await p.waitFor(p.hydrated(tid), 20000); await sleep(2500);
  const idleBoxes = await p.boxes(); note("idleBoxes", idleBoxes);
  if (pre !== "none") {
    await p.mouse("start-session"); await p.waitFor(`document.querySelector('[data-testid=practice-day]')?.dataset.state === 'ready'`, 10000); await sleep(600);
    if (pre === "started") { await p.mouse("course-mode-manual"); await sleep(200); await p.mouse("course-start"); await p.phases(15000, (s) => s[0] === "done"); }
    note("practiceBefore", { ...(await p.sp()), gum: await p.ev(GUM) });
  }
  // 상태 변화를 시간순으로 기록
  await p.ev(`(() => { window.__t0 = performance.now(); window.__mo = []; let last = ''; const f = () => { const h = document.querySelector('[data-testid=home-hero]'); const r = h?.getBoundingClientRect();
    const s = [location.pathname, h?.dataset.mode ?? null, !!document.querySelector('[data-testid=sentence-practice]'), !!document.querySelector('[data-testid=session-panel]'), document.querySelector('[data-testid=session-failed]')?.dataset.reason ?? null,
      [...document.querySelectorAll('nav')].filter(n => n.getClientRects().length).map(n => n.dataset.locked ?? '-').join(','), r ? Math.round(r.height) : null];
    const k = JSON.stringify(s); if (k !== last) { last = k; window.__mo.push([Math.round(performance.now() - window.__t0), ...s]); } };
    new MutationObserver(f).observe(document.documentElement, { subtree: true, childList: true, attributes: true, characterData: true }); f(); window.__coach = 1; })()`);
  p.sockets = []; p.reqs = [];
  note("click", await p.mouse(tid));
  await p.waitFor(`document.querySelector('[data-testid=home-hero]')?.dataset.mode === 'session' || location.pathname !== '/'`, 10000, 10);
  await sleep(300);
  const sess = await p.sp(); const sb = await p.boxes();
  note("session", { state: sess, boxes: sb, heroH: sb["home-hero"]?.[3], idleH: idleBoxes["home-hero"][3], notShorter: sb["home-hero"]?.[3] >= idleBoxes["home-hero"][3],
    others: Object.fromEntries(Object.keys(idleBoxes).filter((k) => k !== "home-hero").map((k) => [k, sb[k] && idleBoxes[k] ? [sb[k][0] - idleBoxes[k][0], sb[k][1] - idleBoxes[k][1], sb[k][2] - idleBoxes[k][2]] : null])) });
  await p.shot(`S5-${label}-session`);
  if (mode === "delay") {
    // 연결 중 잠금: 진짜 마우스로 Practice 메뉴와 More practice 다른 버튼을 누름 → 이동·새 소켓 0
    const before = p.sockets.length;
    await p.mouse("nav-practice").catch((e) => note("navPracticeErr", String(e))); await sleep(800);
    await p.mouse("practice-pronunciation").catch((e) => note("pronErr", String(e))); await sleep(800);
    note("gumDuringConnecting", await p.ev(GUM));
    note("lockedClicks", { path: await p.ev("location.pathname"), newSockets: p.sockets.length - before, navLocked: (await p.sp()).navLocked,
      disabled: await p.ev(`[...document.querySelectorAll('[data-testid^=practice-]:is(button),[data-testid^=quick-]:is(button),[data-testid=focus-practice],[data-testid=start-session]')].filter(b => b.getClientRects().length).map(b => [b.dataset.testid, b.disabled])`) });
  }
  if (mode === "deny") {
    await p.waitFor(`!!document.querySelector('[data-testid=session-failed]')`, 10000); await sleep(300);
    const fb = await p.boxes(); note("failed", { reason: (await p.ev(`document.querySelector('[data-testid=session-failed]').dataset.reason`)), heroH: fb["home-hero"][3], idleH: idleBoxes["home-hero"][3], text: await p.ev(`document.querySelector('[data-testid=session-failed]').innerText`) });
    await p.shot(`S5-${label}-failed`);
  } else {
    await p.waitFor(`location.pathname.startsWith('/results/')`, 40000, 50);
  }
  await sleep(1500);
  note("end", { path: await p.ev("location.pathname"), sockets: p.sockets, gum: await p.ev(GUM).catch(() => "page changed"), mo: await p.ev("window.__mo").catch(() => "page changed") });
} catch (e) { note("ERROR", String(e?.stack ?? e).slice(0, 800)); }
finally { note("logs", p.logs.filter((l) => !/DevTools|HMR|Download the React|Fast Refresh/.test(l.text))); save(); p.c.close(); }
