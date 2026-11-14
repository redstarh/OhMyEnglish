// measures.json 으로 storyboard/index.html 을 만듦: node runs/2026-11-14-b16/screens/build-board.mjs
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
const HERE = dirname(fileURLToPath(import.meta.url));
const R = JSON.parse(readFileSync(join(HERE, "evidence", "measures.json"), "utf8"));
const SCENES = [
  ["home_idle", "홈 대기", "첫 화면. 사이드바 메뉴는 Home 하나이고 좁은 화면은 메뉴 줄 없이 로고만 둠."],
  ["home_practice", "홈 문장 연습 (Start speaking)", "오늘의 연습 카드 안에서 현재 Day 의 문장 연습이 열림. 영상 없음 · Listen/Slow 없음."],
  ["path_day2", "Day 2 를 고른 연습", "Continue your path 의 Day 2 줄을 누르면 주소가 / 그대로이고 카드에서 Day 2 가 열림."],
  ["view_all", "View all 펼침", "View all 이 홈 목록을 모든 Day 로 펼치고 Show less 로 접음."],
  ["coach", "코치 세션 (Free talk)", "More practice 의 Free talk 가 카드 안에서 Nova 세션을 엶. 가짜 마이크라 전사·분석은 판정하지 않음."],
  ["mic_denied", "세션 실패 (마이크 거부)", "CDP Browser.setPermission 으로 마이크를 거부한 뒤 Free talk 를 누름."],
  ["history", "기록 /history", "Your progress 의 History 버튼으로 들어감."],
  ["weekly", "주간 /history/weekly", "Your progress 의 Weekly report 버튼으로 들어감."],
  ["results", "결과 /results/&lt;id&gt;", "격리 DB 의 완료 세션. /history 의 결과 링크로 찾음."],
  ["course", "코스 목록 /course", "메뉴에서 빠졌고 주소로만 닿음."],
  ["course_day", "Day 화면 /course/1", "영상과 옛 연습 화면. 열기만 해도 진도를 저장함(격리 DB)."],
  ["videos", "영상 목록 · 영상 화면", "Learn with videos 링크로 /videos, 첫 영상으로 /videos/&lt;id&gt;."],
];
const esc = (s) => String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const judge = (m) => {
  const bad = [];
  if (m.hOverflow) bad.push(`가로 넘침 ${m.scrollWidth}/${m.clientWidth}`);
  const clip = m.clipped.filter((c) => !(c.cw <= 1 && c.ch <= 1));
  if (clip.length) bad.push(`잘림 ${clip.length}`);
  return bad;
};
let html = `<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>OhMyEnglish 화면 스토리보드 — 회차 2026-11-14-b16</title>
<style>
body{font-family:-apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo",sans-serif;margin:0;background:#f5f6fa;color:#1b2033}
header{padding:24px 32px;background:#fff;border-bottom:1px solid #e3e6ef}
h1{font-size:20px;margin:0 0 6px} header p{margin:2px 0;color:#5b6275;font-size:13px}
nav{padding:10px 32px;background:#fff;border-bottom:1px solid #e3e6ef;font-size:13px}
nav a{margin-right:14px;color:#2f5bd8;text-decoration:none}
section{padding:20px 32px} h2{font-size:17px;margin:0 0 4px} .lead{color:#5b6275;font-size:13px;margin:0 0 14px}
.steps{display:flex;flex-direction:column;gap:14px}
.step{background:#fff;border:1px solid #e3e6ef;border-radius:12px;padding:14px;display:grid;grid-template-columns:40px 1fr;gap:12px}
.num{font-weight:700;font-size:18px;color:#2f5bd8}
.desc{font-size:14px;font-weight:600;margin-bottom:4px}
.meta{font-size:12px;color:#5b6275;margin-bottom:8px}
.bad{color:#c0392b;font-weight:600}
.thumbs{display:flex;gap:16px;align-items:flex-start}
.thumbs figure{margin:0} .thumbs figcaption{font-size:11px;color:#5b6275}
.thumbs img{border:1px solid #d6dae5;border-radius:6px;display:block;object-fit:cover;object-position:top}
.w1400 img{width:420px;height:300px} .w390 img{width:117px;height:253px}
</style></head><body>
<header><h1>OhMyEnglish 화면 스토리보드 — 회차 2026-11-14-b16 (화면 탭)</h1>
<p>헤드리스 Chrome(CDP :9401) · 1400×1000 과 390×844 · 백엔드 :8002 격리 DB ohmyenglish_course_paid · VOICE_ADAPTER=nova</p>
<p>썸네일을 누르면 전체 페이지 원본이 열림. 측정값의 정본은 ../evidence/measures.json 임.</p></header><nav>`;
for (const [id, t] of SCENES) if (R[id]) html += `<a href="#${id}">${t}</a>`;
html += `</nav>`;
let si = 0;
for (const [id, title, lead] of SCENES) {
  const byW = R[id];
  if (!byW) continue;
  si += 1;
  html += `<section id="${id}"><h2>${si}. ${title}</h2><p class="lead">${lead}</p><div class="steps">`;
  const a = byW["1400"] ?? [];
  const b = byW["390"] ?? [];
  const ns = [...new Set([...a, ...b].map((s) => s.n))].sort((x, y) => x - y);
  for (const n of ns) {
    const s1 = a.find((s) => s.n === n);
    const s2 = b.find((s) => s.n === n);
    const desc = (s1 ?? s2).desc;
    const meta = [s1, s2]
      .filter(Boolean)
      .map((s) => {
        const w = s.m.innerWidth;
        const parts = [`${w}: ${s.m.url}`, `scrollWidth ${s.m.scrollWidth}/${s.m.clientWidth}`];
        if (s.m.hero) parts.push(`카드 ${s.m.hero.h}px(${s.m.heroMode})`);
        if (s.m.progress) parts.push(`progress ${s.m.progress.h}px`);
        const bad = judge(s.m);
        return esc(parts.join(" · ")) + (bad.length ? ` <span class="bad">${esc(bad.join(" · "))}</span>` : "");
      })
      .join("<br>");
    const fig = (s, cls) =>
      s ? `<figure class="${cls}"><a href="shots/${s.file}" target="_blank"><img loading="lazy" src="shots/${s.file}" alt="${esc(s.desc)}"></a><figcaption>${cls.slice(1)} 폭</figcaption></figure>` : `<figure class="${cls}"><figcaption>${cls.slice(1)} 폭 — 없음</figcaption></figure>`;
    html += `<div class="step"><div class="num">${n}</div><div><div class="desc">${esc(desc)}</div><div class="meta">${meta}</div><div class="thumbs">${fig(s1, "w1400")}${fig(s2, "w390")}</div></div></div>`;
  }
  for (const w of ["1400", "390"]) if (byW[`err-${w}`]) html += `<p class="bad">${w} 오류: ${esc(byW[`err-${w}`])}</p>`;
  html += `</div></section>`;
}
html += `</body></html>`;
writeFileSync(join(HERE, "storyboard", "index.html"), html);
console.log(`scenes=${si}`);
