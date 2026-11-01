// 회차 b11 — 영상 화면 흐름. 사용: node videos.mjs <youtube-url> [width]
// 화면에 testid 가 없어 버튼은 문구로 고르고, 누름은 실제 마우스로 함. 판정은 화면 글자·API 요청·DB 로 함.
import { open, APP, saver, sleep } from "./lib.mjs";
const url = process.argv[2], width = Number(process.argv[3] ?? 1400);
const { note, save } = saver(`VIDEOS-${width}`);
const p = await open({ port: 9345, width, height: 1000 });
await p.c.send("Network.enable");
let reqs = [], sockets = [], dialogAccept = false, dialogs = [];
p.c.on((d) => {
  if (d.method === "Network.requestWillBeSent" && /:8002|youtube\.com\/oembed|noembed/.test(d.params.request.url) && d.params.request.method !== "OPTIONS") reqs.push(`${d.params.request.method} ${d.params.request.url.replace("http://localhost:8002", "")}`);
  if (d.method === "Network.responseReceived" && /youtube\.com\/oembed|noembed/.test(d.params.response.url)) reqs.push(`  <- ${d.params.response.status} ${d.params.response.url.slice(0, 80)}`);
  if (d.method === "Network.webSocketCreated" && /8002/.test(d.params.url)) sockets.push(d.params.url);
  if (d.method === "Page.javascriptDialogOpening") { dialogs.push(d.params.message); p.c.send("Page.handleJavaScriptDialog", { accept: dialogAccept }).catch(() => {}); }
});
const byText = (txt, tag = "button,a") => `[...document.querySelectorAll('${tag}')].filter(e => e.getClientRects().length && e.textContent.trim() === ${JSON.stringify(txt)})`;
const mouseAt = async (expr) => {
  const pt = await p.ev(`(() => { const e = ${expr}; if (!e) return null; e.scrollIntoView({ block: 'center', behavior: 'instant' }); const r = e.getBoundingClientRect(); return { x: Math.round(r.x + r.width / 2), y: Math.round(r.y + r.height / 2), disabled: !!e.disabled }; })()`);
  if (!pt) return "없음";
  for (const type of ["mousePressed", "mouseReleased"]) await p.c.send("Input.dispatchMouseEvent", { type, x: pt.x, y: pt.y, button: "left", clickCount: 1 });
  return pt;
};
const main = () => p.ev(`(document.querySelector('main') ?? document.body).innerText.slice(0, 1500)`);
const step = async (name, expr, wait = 2000) => { reqs = []; dialogs = []; const pt = expr ? await mouseAt(expr) : null; await sleep(wait);
  note(name, { pt, path: await p.ev("location.pathname + location.search"), reqs: [...reqs], dialogs: [...dialogs], text: (await main()).slice(0, 700) }); };
try {
  await p.nav(`${APP}/videos`); await sleep(3000);
  await step("open", null, 0);
  // 빈 값이면 Check 비활성
  note("checkDisabledEmpty", await p.ev(`${byText("Check")}[0]?.disabled`));
  // 잘못된 링크 → 안내
  await mouseAt(`document.querySelector('input')`); await p.c.send("Input.insertText", { text: "https://example.com/not-a-video" });
  await step("checkBadUrl", `${byText("Check")}[0]`, 3000);
  await p.ev(`(() => { const i = document.querySelector('input'); i.select(); })()`); await p.c.send("Input.insertText", { text: url });
  await step("check", `${byText("Check")}[0]`, 4000);
  await step("cancelPreview", `${byText("Cancel")}[0]`, 800);
  await step("checkAgain", `${byText("Check")}[0]`, 4000);
  await step("save", `${byText("Save")}[0]`, 3000);
  const links = await p.ev(`[...document.querySelectorAll('a[href^="/videos/"]')].map(a => ({ href: a.getAttribute('href'), text: a.textContent.trim().slice(0, 60) }))`);
  note("listAfterSave", links);
  const mine = links.find((l) => !l.href.includes("b502eaf3"));
  if (!mine) throw new Error("저장한 영상이 목록에 없음");
  await step("openDetail", `[...document.querySelectorAll('a[href="${mine.href}"]')][0]`, 6000);
  note("iframe", await p.ev(`[...document.querySelectorAll('iframe')].map(f => f.src.slice(0, 80))`));
  await step("markStart", `${byText("Mark start")}[0]`, 3000);
  const buttons = () => p.ev(`[...document.querySelectorAll('main button, main a, button')].filter(e => e.getClientRects().length).map(e => e.textContent.trim().slice(0, 30))`);
  note("buttonsAfterMarkStart", await buttons());
  await step("redo", `${byText("Redo")}[0] ?? ${byText("Start over")}[0]`, 800);
  note("buttonsAfterRedo", await buttons());
  await step("markStart2", `${byText("Mark start")}[0]`, 3500);
  const endBtn = (await buttons()).find((b) => /end/i.test(b) && b !== "Mark start");
  note("endLabel", endBtn ?? null);
  if (endBtn) await step("markEnd", `${byText(endBtn)}[0]`, 2000);
  note("buttonsAfterMarkEnd", await buttons());
  const ta = await p.ev(`!!document.querySelector('textarea')`);
  if (ta) {
    note("saveDisabledEmpty", await p.ev(`${byText("Save")}[0]?.disabled`));
    await mouseAt(`document.querySelector('textarea')`); await p.c.send("Input.insertText", { text: "This is a test sentence from round b11." });
    await step("savePhrase", `${byText("Save")}[0]`, 3000);
    note("buttonsAfterSavePhrase", await buttons());
    await step("listen", `${byText("Listen")}[0] ?? ${byText("▶ Listen")}[0]`, 1500);
    const btns = await buttons(); note("phraseButtons", btns);
    const practise = btns.find((b) => /practi/i.test(b));
    if (practise) {
      sockets = [];
      await step("practise", `${byText(practise)}[0]`, 3000);
      try { await p.waitFor(`location.pathname.startsWith('/results/') || !!document.querySelector('[data-testid=session-failed]')`, 30000); } catch {}
      note("practiseEnd", { path: await p.ev("location.pathname"), sockets: [...sockets] });
      await p.nav(`${APP}${mine.href}`); await sleep(5000);
    }
    const del = (await buttons()).find((b) => /^(Delete|Remove)$/.test(b));
    if (del) await step("deletePhrase", `${byText(del)}[0]`, 2500);
  }
  await step("backToVideos", `${byText("← Videos")}[0]`, 2500);
  dialogAccept = false;
  const rowDelete = `[...document.querySelectorAll('li')].find(li => li.querySelector('a[href="${mine.href}"]'))?.querySelector('button')`;
  await step("deleteVideoCancel", rowDelete, 2000);
  dialogAccept = true;
  await step("deleteVideoAccept", rowDelete, 3000);
  note("listAfterDelete", await p.ev(`[...document.querySelectorAll('a[href^="/videos/"]')].map(a => a.getAttribute('href'))`));
} catch (e) { note("ERROR", String(e?.stack ?? e).slice(0, 600)); }
finally { note("logs", p.logs.filter((l) => !/DevTools|HMR|Download the React|postMessage/.test(l.text))); save(); p.c.close(); }
