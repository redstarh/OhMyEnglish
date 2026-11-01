// 회차 b15 — TASK-310·311 화면 측정. 사용: node measure.mjs <폭> <포트>
// ⛔ dev DB 위에서 돎 — 문장 연습은 열기만 하고 Start·Next 를 누르지 않음(진도·시도 기록을 바꾸지 않게).
//    상태별 크기는 DOM 에 내용을 넣어 잼(단계 줄 · 결과 칸 · 565문장).
import { readFileSync } from "node:fs";
import { open, APP, VIS, saver, sleep } from "./lib.mjs";

const width = Number(process.argv[2] ?? 1400);
const port = Number(process.argv[3] ?? 9365);
const content = JSON.parse(readFileSync("/Users/redstar/MyProject/OhMyEnglish/app/backend/app/content/grammar_basic.json", "utf8"));
const sentences = content.days.flatMap((d) => d.units.flatMap((u) => u.sentences));
const topics = content.days.flatMap((d) => d.units.map((u) => `Unit ${u.unit} · ${u.topic}`));
const longest = sentences.reduce((a, b) => (b.length > a.length ? b : a));
const { note, save } = saver(`measure-${width}`);
const p = await open({ port, width, height: 1000 });
const rect = (sel) => p.ev(`(() => { const e = ${sel}; if (!e) return null; const r = e.getBoundingClientRect(); return { top: Math.round(r.top), bottom: Math.round(r.bottom), h: Math.round(r.height * 10) / 10 }; })()`);

await p.nav(`${APP}/`, `!!(${VIS("home-hero")})`);
await sleep(800);
note("idle.hero", await rect(VIS("home-hero")));
note("idle.progress", await rect(VIS("home-progress")));
note("labels", await p.ev(`[...document.querySelectorAll('p, h2')].filter(e => /^(today's practice|your progress|continue your path|focus patterns|more practice)$/i.test(e.innerText.trim())).map(e => { const s = getComputedStyle(e); return [e.innerText.trim(), s.fontSize, s.fontWeight, s.letterSpacing, s.textTransform, s.color].join(' | '); })`));
await p.shot(`home-idle-${width}`);

await p.click("start-session");
await p.waitFor(`!!(${VIS("course-card")})`);
await sleep(800);
const card = VIS("course-card");
note("practice.hero", await rect(VIS("home-hero")));
note("practice.progress", await rect(VIS("home-progress")));
note("practice.card", await rect(card));
note("practice.gapBelowCard", await p.ev(`Math.round(${VIS("home-hero")}.getBoundingClientRect().bottom - ${card}.getBoundingClientRect().bottom)`));
note("labels.practice", await p.ev(`[...document.querySelectorAll('p')].filter(e => /^today's practice$/i.test(e.innerText.trim())).map(e => { const s = getComputedStyle(e); return [s.fontSize, s.fontWeight, s.letterSpacing, s.color].join(' | '); })`));
note("buttons", await p.ev(`['practice-close','course-prev','course-start','course-next'].map(t => { const e = [...document.querySelectorAll('[data-testid="' + t + '"]')].find(x => x.getClientRects().length > 0); if (!e) return t + ':없음'; const r = e.getBoundingClientRect(); const s = getComputedStyle(e); return [t, Math.round(r.height), s.fontSize, s.paddingTop, s.borderRadius, s.backgroundColor].join(' '); })`));
await p.shot(`home-practice-${width}`);

// 문장 565개 — 두 줄(높이 고정) 안에 드는가, 카드 높이가 바뀌는가
note("sentences", await p.ev(`(() => { const e = ${VIS("course-sentence")}; const c = ${card}; const orig = e.textContent; const out = { n: 0, overflow: [], cardH: new Set() };
  for (const s of ${JSON.stringify(sentences)}) { e.textContent = s; out.n++; if (e.scrollHeight > e.clientHeight + 1) out.overflow.push(s); out.cardH.add(Math.round(c.getBoundingClientRect().height)); }
  e.textContent = orig; return { n: out.n, overflow: out.overflow.slice(0, 5), overflowCount: out.overflow.length, cardH: [...out.cardH], lineBox: e.clientHeight }; })()`));
// 단원 줄 — 가장 긴 주제가 몇 줄인가(카드 높이가 바뀌는 자리)
note("unitRow", await p.ev(`(() => { const e = ${VIS("course-unit")}; const h = ${VIS("home-hero")}; const orig = e.textContent; const hs = new Set();
  for (const t of ${JSON.stringify(topics)}) { e.textContent = t; hs.add(Math.round(h.getBoundingClientRect().height)); } e.textContent = orig; return [...hs]; })()`));
// 듣기 단계 — 번호 줄에 단계 표시가 붙고 안내가 결과 자리에 들어감
note("phase", await p.ev(`(() => { const num = ${VIS("course-sentence-number")}; const c = ${card}; const slot = ${VIS("course-result-slot")}; const before = Math.round(c.getBoundingClientRect().height);
  const sp = document.createElement('span'); sp.textContent = ' · ② Say it · 3.2s'; num.after(sp);
  const msg = document.createElement('p'); msg.style.fontSize = '0.85rem'; msg.textContent = "I'm listening. Say it, and you will see it below."; slot.append(msg);
  const r = { before, after: Math.round(c.getBoundingClientRect().height), rowH: Math.round(num.parentElement.parentElement.getBoundingClientRect().height) }; sp.remove(); msg.remove(); return r; })()`));
// 결과 — 가장 긴 문장의 「You said」 칸을 결과 자리에 넣음(Spoken 과 같은 마크업)
note("result", await p.ev(`(() => { const c = ${card}; const slot = ${VIS("course-result-slot")}; const before = Math.round(c.getBoundingClientRect().height);
  const s = ${JSON.stringify(longest)}; const words = s.split(' ').map((w, i) => '<span style="text-decoration:' + (i === 2 ? 'underline' : 'none') + '">' + w + '</span> ').join('');
  const d = document.createElement('div'); d.style.cssText = 'padding:6px 10px;border-radius:10px;background:var(--accent-soft);font-size:0.85rem';
  d.innerHTML = '<span style="font-size:0.72rem;color:var(--foreground-muted)">You said: </span><span>' + s.toLowerCase() + '</span><div style="margin-top:2px;overflow-wrap:anywhere">' + words + '<span style="display:block;font-size:0.72rem;color:var(--foreground-muted)">Underline: you said a different word. Strikethrough: you missed the word.</span></div>';
  slot.append(d); const e = ${VIS("course-sentence")}; const orig = e.textContent; e.textContent = s;
  const r = { before, after: Math.round(c.getBoundingClientRect().height), slotH: slot.clientHeight, contentH: Math.round(d.getBoundingClientRect().height), scrolls: slot.scrollHeight > slot.clientHeight + 1 };
  return r; })()`));
await p.shot(`home-practice-result-${width}`);
save();
p.c.close();
