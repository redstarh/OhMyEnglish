// measures.json 으로 storyboard/index.html 을 만듦(b16 과 같은 형식): node runs/2026-11-14-b18/screens/build-board.mjs
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
const HERE = dirname(fileURLToPath(import.meta.url));
const R = JSON.parse(readFileSync(join(HERE, "evidence", "measures.json"), "utf8"));
const SCENES = [
  ["home_idle", "홈 대기", "첫 화면. 메뉴는 Home 하나 · 빠른 카드와 Grammar course 없음. 대기 카드 높이는 KO 저장값을 따름(끔 513.6 px · 켬 558.4 px)."],
  ["home_practice", "홈 문장 연습 (KO 끔 · KO 켬 · 실시간 표시)", "Start speaking 이 카드 안에서 현재 Day 의 문장 연습을 엶. Listen/Slow 없음. KO 를 켜면 문장 아래 한국어 번역이 나옴. 말하는 동안의 글자는 가짜 SpeechRecognition(addInitScript)으로 보였음 — 시험 Chrome 의 진짜 인식기는 가짜 오디오를 전사하지 않음."],
  ["path_day2", "Day 2 를 고른 연습", "Continue your path 의 Day 2 줄을 누르면 주소가 / 그대로이고 카드에서 Day 2 가 열림. 390 은 카드로 스크롤함."],
  ["view_all", "View all 펼침", "View all 이 홈 목록을 모든 Day 로 펼치고 Show less 로 접음."],
  ["coach", "코치 세션 (Free talk) → 발화 없는 결과", "More practice 의 Free talk 가 카드 안에서 Nova 세션을 엶. 가짜 마이크라 말이 없으므로 End lesson 뒤 결과는 「We didn't hear you this time」임. 전사·분석은 판정하지 않음."],
  ["history", "기록 /history (날짜 줄 → 결과)", "Your progress 의 History 로 들어감. 세션이 여럿인 날짜 줄은 펼쳐 세션 목록을 보이고, 세션을 누르면 그 결과로 감. 격리 DB 에 세션이 하나뿐인 날이 없어 「줄 → 바로 결과」 갈래는 이 보드에 없음."],
  ["weekly", "주간 /history/weekly", "Your progress 의 Weekly report 로 들어감. 제목에 기간 · ← Home 으로 돌아감."],
  ["results", "결과 /results/&lt;id&gt; (지난 완료 · 발화 없음)", "격리 DB 의 11-01 완료 세션과 11-14 발화 0건 세션을 주소로 엶."],
  ["course", "/course · /course/1 리다이렉트", "옛 코스 목록과 Day 화면 주소가 홈으로 넘어감."],
  ["videos", "영상 목록 · 영상 화면", "More practice 의 Learn with videos 로 /videos, 첫 영상으로 /videos/&lt;id&gt;."],
];
const esc = (s) => String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const judge = (m) => {
  const bad = [];
  if (m.bodyScrollWidth > m.innerWidth) bad.push(`가로 넘침 body ${m.bodyScrollWidth}/${m.innerWidth}`);
  if (m.offRight.length) bad.push(`화면 밖 글자 ${m.offRight.length}`);
  if (m.wideMedia.length) bad.push(`화면 밖 미디어 ${m.wideMedia.length}`);
  const clip = m.clipped.filter((c) => !(c.cw <= 1 && c.ch <= 1));
  if (clip.length) bad.push(`잘림 ${clip.length}`);
  return bad;
};
const KEY_TEXTS = ["practice-day", "course-sentence-number", "course-translation-text", "course-live", "course-transcript", "course-notice", "results-status", "weekly-heading", "weekly-period", "home-weekly-period"];
let html = `<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>OhMyEnglish 화면 스토리보드 — 회차 2026-11-14-b18</title>
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
.say{font-size:12px;color:#1b2033;margin-bottom:8px}
.bad{color:#c0392b;font-weight:600}
.thumbs{display:flex;gap:16px;align-items:flex-start}
.thumbs figure{margin:0} .thumbs figcaption{font-size:11px;color:#5b6275}
.thumbs img{border:1px solid #d6dae5;border-radius:6px;display:block;object-fit:cover;object-position:top}
.w1400 img{width:420px;height:300px} .w390 img{width:117px;height:253px}
</style></head><body>
<header><h1>OhMyEnglish 화면 스토리보드 — 회차 2026-11-14-b18 (화면 탭 · 고친 뒤)</h1>
<p>헤드리스 Chrome(CDP :9461) · 1400×1000 과 390×844 · 백엔드 :8002 격리 DB ohmyenglish_course_paid · VOICE_ADAPTER=nova · HEAD 0428af4</p>
<p>앞 판(b16 · 고치기 전)은 docs/ux/2026-11-14-user-scenarios/ 에 그대로 있음. 썸네일을 누르면 전체 페이지 원본이 열림. 측정값의 정본은 ../evidence/measures.json 임.</p></header><nav>`;
for (const [id, t] of SCENES) if (R[id]) html += `<a href="#${id}">${t}</a>`;
html += `</nav>`;
let si = 0;
let steps = 0;
for (const [id, title, lead] of SCENES) {
  const byW = R[id];
  if (!byW) continue;
  si += 1;
  html += `<section id="${id}"><h2>${si}. ${title}</h2><p class="lead">${lead}</p><div class="steps">`;
  const a = byW["1400"] ?? [];
  const b = byW["390"] ?? [];
  const ns = [...new Set([...a, ...b].map((s) => s.n))].sort((x, y) => x - y);
  for (const n of ns) {
    steps += 1;
    const s1 = a.find((s) => s.n === n);
    const s2 = b.find((s) => s.n === n);
    const desc = (s1 ?? s2).desc;
    const meta = [s1, s2]
      .filter(Boolean)
      .map((s) => {
        const w = s.m.innerWidth;
        const parts = [`${w}: ${s.m.url}`, `body ${s.m.bodyScrollWidth}/${s.m.innerWidth}`];
        if (s.m.hero) parts.push(`카드 ${s.m.hero.h}px(${s.m.heroMode})`);
        if (s.m.koPressed) parts.push(`KO ${s.m.koPressed === "true" ? "켬" : "끔"}`);
        const bad = judge(s.m);
        return esc(parts.join(" · ")) + (bad.length ? ` <span class="bad">${esc(bad.join(" · "))}</span>` : "");
      })
      .join("<br>");
    const t = (s1 ?? s2).m.texts;
    const say = KEY_TEXTS.filter((k) => t[k]).map((k) => `${k}: 「${t[k]}」`).join(" · ");
    const fig = (s, cls) =>
      s ? `<figure class="${cls}"><a href="shots/${s.file}" target="_blank"><img loading="lazy" src="shots/${s.file}" alt="${esc(s.desc)}"></a><figcaption>${cls.slice(1)} 폭</figcaption></figure>` : `<figure class="${cls}"><figcaption>${cls.slice(1)} 폭 — 없음</figcaption></figure>`;
    html += `<div class="step"><div class="num">${n}</div><div><div class="desc">${esc(desc)}</div><div class="meta">${meta}</div>${say ? `<div class="say">${esc(say)}</div>` : ""}<div class="thumbs">${fig(s1, "w1400")}${fig(s2, "w390")}</div></div></div>`;
  }
  for (const w of ["1400", "390"]) if (byW[`err-${w}`]) html += `<p class="bad">${w} 오류: ${esc(byW[`err-${w}`])}</p>`;
  html += `</div></section>`;
}
html += `</body></html>`;
writeFileSync(join(HERE, "storyboard", "index.html"), html);
console.log(`scenes=${si} steps=${steps}`);
