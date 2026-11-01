// 회차 b15 — TASK-309 아래쪽 입구의 카드 스크롤. 사용: node reveal.mjs <폭> <포트>
// ⛔ 마이크 권한을 거부해 세션이 소켓을 열기 전에 실패하게 함 — dev DB 에 세션이 생기지 않고 Nova 를 부르지 않음.
import { open, APP, VIS, saver, sleep } from "./lib.mjs";
const width = Number(process.argv[2] ?? 390), port = Number(process.argv[3] ?? 9366);
const { note, save } = saver(`reveal-${width}`);
const p = await open({ port, width, height: 1000 });
await p.c.send("Browser.setPermission", { permission: { name: "microphone" }, setting: "denied", origin: APP });
const hero = () => p.ev(`(() => { const r = ${VIS("home-hero")}.getBoundingClientRect(); return { top: Math.round(r.top), bottom: Math.round(r.bottom), scrollY: Math.round(scrollY), mode: ${VIS("home-hero")}.dataset.mode }; })()`);
const home = async () => { await p.nav(`${APP}/`, `!!(${VIS("home-hero")}) && !!(${VIS("practice-free_talk")})`); await sleep(1200); };

// ① 아래쪽 입구 · 카드가 화면 밖 → 카드로 스크롤
await home();
await p.ev(`window.scrollTo(0, document.documentElement.scrollHeight)`); await sleep(400);
note("bottom.before", await hero());
await p.click("practice-free_talk"); await sleep(1500);
note("bottom.after", await hero());
note("failedHome", await p.ev(`(() => { const e = ${VIS("session-failed-home")}; if (!e) return null; const r = e.getBoundingClientRect(); return { h: Math.round(r.height), cls: e.className, inView: r.top >= 0 && r.bottom <= innerHeight }; })()`));
await p.shot(`reveal-bottom-${width}`);

// ② 아래쪽 입구 · 카드가 이미 다 보임 → 움직이지 않음 (보이는 입구가 있을 때만)
await home();
note("visible.before", await hero());
const visibleEntry = await p.ev(`(() => { const e = ${VIS("practice-free_talk")}; const r = e.getBoundingClientRect(); return r.bottom <= innerHeight; })()`);
note("visible.entryInView", visibleEntry);
if (visibleEntry) { await p.click("practice-free_talk"); await sleep(1500); note("visible.after", await hero()); }

// ③ Start speaking · 카드 일부가 화면 밖 → 창이 움직이지 않음(TASK-305)
await home();
await p.ev(`window.scrollTo(0, 120)`); await sleep(400);
note("start.before", await hero());
await p.click("start-session"); await sleep(1500);
note("start.after", await hero());
await p.click("practice-close"); await sleep(800);
save(); p.c.close();
