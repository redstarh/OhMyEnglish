// 회차 b9 — 시나리오 4·5·6: 홈의 진입 버튼 하나로 세션을 열고 덮개 층·대화 줄·결과 이동을 봄.
// 사용: node session.mjs <라벨> <testid> [port]   예) node session.mjs rec start-session
import { open, APP, saver, sleep, VIS } from "./lib.mjs";
const label = process.argv[2], tid = process.argv[3], port = Number(process.argv[4] ?? 9335);
const { note, save } = saver(`SESSION-${label}`);
const p = await open({ port, width: 1400, height: 1000 });
const ws = [];
p.c.on((d) => { if (d.method === "Network.webSocketCreated") ws.push(d.params.url); });
await p.c.send("Network.enable");
try {
  await p.nav(`${APP}/`);
  await p.waitFor(p.hydrated(tid), 20000);
  const navRect = await p.ev(`(() => { const r = ${VIS("nav-home")}.getBoundingClientRect(); return [Math.round(r.x + r.width / 2), Math.round(r.y + r.height / 2)]; })()`);
  note("navHomeCenter", navRect);
  // 덮개 층 · 대화 줄 · 실패 상자 · 경로를 변화마다 기록함 (클라이언트 이동이라 window 가 남음)
  await p.ev(`(() => { window.__t0 = performance.now(); window.__mo = []; window.__lines = new Map(); window.__seen = new Set(); let last = '';
    const snap = () => { const ov = document.querySelector('[data-testid=session-overlay]'); const f = document.querySelector('[data-testid=session-failed]');
      if (ov) { for (const el of ov.querySelectorAll('p')) { const s = el.textContent.trim(); if (/^(Coach|You): /.test(s)) window.__lines.set(s.slice(0, 200), Math.round(performance.now() - window.__t0)); }
        const w = document.createTreeWalker(ov, NodeFilter.SHOW_TEXT); let n; while ((n = w.nextNode())) { const s = n.textContent.trim(); if (s) window.__seen.add(s.slice(0, 200)); } }
      const k = location.pathname + '|' + !!ov + '|' + (f ? f.dataset.reason : '-');
      if (k !== last) { last = k; window.__mo.push([Math.round(performance.now() - window.__t0), location.pathname, !!ov, f ? f.dataset.reason : null]); } };
    new MutationObserver(snap).observe(document.documentElement, { subtree: true, childList: true, characterData: true, attributes: true }); window.__snap = snap; })()`);
  note("click", await p.click(tid));
  await p.waitFor(`!!document.querySelector('[data-testid=session-overlay]') || location.pathname !== '/'`, 10000, 10);
  const cover = await p.ev(`(() => { const ov = document.querySelector('[data-testid=session-overlay]'); if (!ov) return { overlay: false, path: location.pathname };
    const [x, y] = ${JSON.stringify(navRect)}; const el = document.elementFromPoint(x, y);
    return { overlay: true, z: getComputedStyle(ov).zIndex, pos: getComputedStyle(ov).position, hitInsideOverlay: ov.contains(el), hitIsNav: !!el?.closest('[data-testid^=nav-]'), hitTag: el?.tagName }; })()`);
  note("coverAtSidebar", cover);
  await p.shot(`SESSION-${label}-overlay`);
  // 결과로 가거나 실패 상자가 뜰 때까지
  await p.waitFor(`location.pathname.startsWith('/results/') || !!document.querySelector('[data-testid=session-failed]')`, 60000, 50);
  await sleep(300);
  note("mo", await p.ev("window.__mo"));
  note("lines", await p.ev("[...window.__lines.entries()]"));
  note("overlayTexts", await p.ev("[...window.__seen]"));
  note("path", await p.ev("location.pathname"));
  if (await p.ev("location.pathname.startsWith('/results/')")) {
    await sleep(4000);
    note("resultsText", (await p.ev("document.querySelector('main')?.innerText ?? document.body.innerText")).slice(0, 4000));
    note("resultsHangul", await p.hangul());
    note("resultsActiveNav", await p.ev(`[...document.querySelectorAll('[data-testid^=nav-]')].filter(e => e.getClientRects().length && e.getAttribute('aria-current') === 'page').map(e => e.dataset.testid)`));
    await p.shot(`SESSION-${label}-results`);
  } else {
    note("failedBox", await p.ev(`(() => { const f = document.querySelector('[data-testid=session-failed]'); return { reason: f.dataset.reason, text: f.innerText }; })()`));
    note("failedHangul", await p.hangul());
    await p.shot(`SESSION-${label}-failed`);
  }
} catch (e) { note("ERROR", String(e?.stack ?? e)); try { note("mo", await p.ev("window.__mo")); } catch {} }
finally { await sleep(300); note("webSockets", ws); note("logs", p.logs.filter((l) => !/DevTools|HMR/.test(l.text))); save(); p.c.close(); }
