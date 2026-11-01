// 시나리오 7 — 영상으로 배우기: Listen & notice → 영상 목록 → 영상 하나 → 구간 표시 → 문장 저장 → 낱말 뜻
// 끝에 저장한 문장을 지워 격리 DB 를 되돌림.
import { scenario, APP, API, sleep, byText } from "./board.mjs";
import { yt, VID } from "./h.mjs";
const { p, step, note, done } = await scenario("s07");
const btn = (re, name) => byText("button", re, name);
try {
  await p.nav(`${APP}/`); await sleep(2500);
  await step("홈의 Listen & notice 카드", "quick-videos", { desc: "영상 목록으로 감" });
  await p.waitFor(`location.pathname === '/videos' && !!document.querySelector('a[href^="/videos/"]')`, 15000); await sleep(1000);
  await step("영상 목록 · 링크 칸과 저장된 영상", { name: 'a[href^="/videos/"] (영상 제목)', js: `document.querySelector('a[href^="/videos/"]')` }, { desc: "저장된 영상을 엶" });
  await p.waitFor(`!!document.querySelector('iframe')`, 15000); await sleep(4000);
  await step("영상 화면", { name: "iframe (YouTube 재생 버튼)", js: `document.querySelector('iframe')` }, { desc: "영상을 재생함", after: 3000 });
  note("video after play: " + JSON.stringify(await yt(VID)));
  await step("영상이 재생됨", btn(/^Mark start$/, "button: Mark start"), { desc: "들을 구간의 시작을 찍음", after: 4500 });
  await step("시작을 찍음 · 계속 재생", btn(/^Mark end$/, "button: Mark end"), { desc: "구간의 끝을 찍음", after: 1200 });
  await p.ev(`(() => { const t = document.querySelector('#phrase-transcript'); const set = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set; set.call(t, 'I start work at 8:00 in the morning.'); t.dispatchEvent(new Event('input', { bubbles: true })); })()`); await sleep(400);
  await step("구간 반복 재생 · 받아쓰기를 적음", btn(/^Save$/, "button: Save"), { desc: "들은 문장을 저장함", after: 1500 });
  await step("저장된 문장 목록", btn(/^work$/, "button: 낱말 work"), { desc: "문장 속 낱말을 눌러 뜻을 봄", after: 3500 });
  note("lookup status: " + (await p.ev(`[...document.querySelectorAll('[role=status]')].map(e => e.innerText).join(' / ')`)));
  await step("낱말 뜻 조회 결과", null, { desc: "stub 이라 뜻을 받지 못한 안내가 뜸" });
  // 되돌리기: 저장한 문장 지우기(확인 상자 없음)
  await p.mouseAny(btn(/^Delete$/, "Delete")); await sleep(1500);
  const vids = await (await fetch(`${API}/api/videos`)).json(); note("phrase_count after cleanup: " + JSON.stringify(vids.videos.map((v) => v.phrase_count)));
  done(true);
} catch (e) { note("ERROR " + e.message); done(false, e); }
