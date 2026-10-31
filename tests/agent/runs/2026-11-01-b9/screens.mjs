// 회차 b9 — 시나리오 9: 영상 목록 → 영상 등록(사용자처럼 링크 붙여 넣기) → 영상 화면 · 이력 · 주간 화면의 문구와 남은 한국어.
// 영상 화면에는 testid 가 없어 버튼은 문구로 고름(이 화면의 문구 자체가 시험 대상임).
import { open, APP, saver, sleep } from "./lib.mjs";
const { note, save } = saver("SCREENS");
const p = await open();
const B = (t) => `[...document.querySelectorAll('button')].find(b => b.textContent.trim() === ${JSON.stringify(t)})`;
const clickText = async (t) => { await p.waitFor(`(() => { const b = ${B(t)}; return !!b && !b.disabled && Object.keys(b).some(k => k.startsWith('__reactProps')); })()`, 15000); await p.ev(`${B(t)}.click()`); };
const page = async (label) => { await sleep(1500); note(`${label}Text`, (await p.ev("document.querySelector('main')?.innerText ?? document.body.innerText")).slice(0, 3000)); note(`${label}Hangul`, await p.hangul()); await p.shot(`SCREENS-${label}`); };
try {
  await p.nav(`${APP}/videos`);
  await page("videosEmpty");
  // 링크 붙여 넣기 → Check → Save
  await p.waitFor(`!!document.querySelector('#video-url') && Object.keys(document.querySelector('#video-url')).some(k => k.startsWith('__reactProps'))`, 15000);
  await p.ev(`(() => { const i = document.querySelector('#video-url'); const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set; set.call(i, 'https://www.youtube.com/watch?v=DjgXa-L0Zm0'); i.dispatchEvent(new Event('input', { bubbles: true })); })()`);
  await clickText("Check");
  await p.waitFor(`!!${B("Save")} || !!document.querySelector('[role=status]')`, 20000);
  note("afterCheck", await p.ev(`document.querySelector('main').innerText.slice(0, 800)`));
  if (await p.ev(`!!${B("Save")}`)) { await clickText("Save"); await p.waitFor(`!!document.querySelector('a[href^="/videos/"]')`, 15000); }
  await page("videosList");
  const href = await p.ev(`document.querySelector('a[href^="/videos/"]')?.getAttribute('href')`);
  note("videoHref", href);
  await p.nav(`${APP}${href}`);
  await p.waitFor(`document.body.innerText.includes('Saved sentences') || document.body.innerText.includes("I can't find this video.")`, 20000);
  await page("videoDetail");
  note("videoDetailButtons", await p.ev(`[...document.querySelectorAll('main button')].map(b => b.textContent.trim() + (b.disabled ? '(off)' : ''))`));
  for (const path of ["/history", "/history/weekly"]) {
    await p.nav(`${APP}${path}`);
    await page(path === "/history" ? "history" : "weekly");
  }
} catch (e) { note("ERROR", String(e?.stack ?? e)); }
finally { note("logs", p.logs.filter((l) => !/DevTools|HMR/.test(l.text)).map((l) => [l.kind, l.url, l.text.slice(0, 200)])); save(); p.c.close(); }
