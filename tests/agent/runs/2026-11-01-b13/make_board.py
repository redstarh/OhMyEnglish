"""회차 b13 — raw/<시나리오>.json 의 단계 기록으로 사용자 시나리오 화면 보드(board/index.html)를 만듦.
외부 의존 없음. 썸네일은 board/shots/*.jpg(폭 700) 를 상대 경로로 씀."""
import html, json, pathlib

R = pathlib.Path(__file__).resolve().parent
OUT = R / "board" / "index.html"

# (번호, 제목, 설명, [(줄 키, 줄 이름, 단계 이름 바꾸기)])
SCENARIOS = [
    ("1", "오늘의 문장 연습", "홈의 오늘의 Day 카드에서 말하기를 시작하면 카드 크기 그대로 그 안에서 문장 연습이 열림. 듣고 따라 말하고 다음 문장으로 넘긴 뒤 닫음.",
     [("s01", "1400 폭", {}), ("s01m", "390 폭", {})]),
    ("2", "Day 마치기", "마지막 문장까지 넘기고 한 번 따라 말하면 Finish Day 가 켜짐. 마치고 닫으면 Day 카드와 진도 카드가 다음 Day 로 바뀜.",
     [("s02", "1400 폭", {})]),
    ("3", "코치 대화", "More practice 의 Free talk 로 코치와 대화함. 세션은 홈 맨 위 카드 안에서 돌고, 끝나면 결과 화면으로 넘어감.",
     [("s03", "Free talk", {})]),
    ("4", "약점 연습", "Focus patterns 의 Practice a pattern 또는 Repair your mistakes 카드로 약점 패턴 대화를 시작함.",
     [("s04", "Practice a pattern", {}), ("s04b", "Repair your mistakes", {})]),
    ("5", "쉐도잉", "Shadow a sentence 카드로 쉐도잉을 시작하면 카드 안에 지문과 Listen · Read along 이 뜸.",
     [("s05", "Shadow a sentence", {3: "카드 안 쉐도잉 패널(지문 · Listen · Read along)"})]),
    ("6", "문법 코스", "사이드바 Practice 로 코스 목록에 가서 진행 중인 Day 를 엶. Day 화면은 영상과 문장 연습을 함께 보임.",
     [("s06", "1400 폭", {})]),
    ("7", "영상으로 배우기", "Listen & notice 카드로 영상 목록에 가서 영상을 엶. 구간을 찍어 받아쓴 문장을 저장하고, 문장 속 낱말을 눌러 뜻을 봄.",
     [("s07", "1400 폭", {})]),
    ("8", "이력과 주간", "사이드바 Review 로 이력을, Weekly report 와 사이드바 Progress 로 주간 리포트를 봄.",
     [("s08", "1400 폭", {})]),
    ("9", "결과 화면", "분석이 끝난 세션의 결과 화면에서 Practice this 를 누르면 그 패턴으로 홈 카드 안 세션이 바로 시작됨.",
     [("s09", "분석 끝난 세션 → Practice this", {})]),
    ("10", "실패와 복구", "마이크가 거부되면 카드 안에 실패 상자가 뜸. Try again 으로 다시 하거나 ← Home 으로 대기로 돌아감. 문장 연습은 실패 상자 대신 카드 안 안내를 보임.",
     [("s10", "Try again 으로 복구", {}), ("s10b", "← Home 으로 돌아감", {}), ("s10c", "문장 연습에서 거부", {})]),
]

NOTES = {
    "s01": "Listen 도 듣기 → 따라 말하기 → 판정을 한 바퀴 돎. 그래서 Start 를 먼저 누르고 Listen 을 뒤에 둠.",
    "s01m": "390 폭은 사이드바 대신 위쪽 막대 4칸이 보임.",
    "s02": "중간 문장 화면은 생략함(Next → 를 여러 번 누름). 이 판은 여섯 Day 를 모두 마친 상태에서 Day 5 를 마쳐 새 바퀴(Day 1 · 0 / 6 days)로 넘어감. Day 번호와 완료 수는 같은 스택의 다른 회차가 바꿀 수 있음.",
    "s03": "stub 세션은 0.1초 안팎에 끝남. 세션 화면을 찍으려고 브라우저 쪽에서만 소켓 메시지 전달을 늦춤(앱 코드는 그대로). 창은 스크롤되지 않으므로 세션 화면은 맨 위로 올려 찍음.",
    "s04": "세션 화면은 시나리오 3 과 같은 방법으로 찍음.",
    "s04b": "세션 화면은 시나리오 3 과 같은 방법으로 찍음.",
    "s05": "소켓 주소가 ?mode=shadowing&source=additional 임.",
    "s06": "Day 화면의 영상은 재생하지 않은 상태임.",
    "s07": "끝에 저장한 문장을 Delete 로 지워 격리 DB 를 되돌림. stub 이라 낱말 뜻은 「I couldn't find it」 안내가 뜸.",
    "s08": "",
    "s09": "/history 에는 세션 행으로 가는 링크가 없어 결과 화면은 주소로 직접 엶(격리 DB 의 c7482f05 · 회차 b10). 새 결과는 분석이 꺼져 Checking… 으로 남음.",
    "s10": "코치 진입 뒤 첫 getUserMedia 한 번을 NotAllowedError 로 거절하도록 드라이버가 주입함. 실패 상자의 Try again 버튼에는 data-testid 가 없음.",
    "s10b": "",
    "s10c": "문장 연습은 실패 상자를 쓰지 않고 카드 안 안내 「I can't use the mic. Please allow the mic in your browser.」 를 보임.",
}


def card(step, overrides, last, narrow=False):
    title = overrides.get(step["n"], step["title"])
    img = "shots/" + step["file"].replace(".png", ".jpg")
    label = " · ".join(x.strip() for x in (step.get("label") or "").split("\n") if x.strip())
    who = step.get("tid") or step.get("selector")
    if who:
        sel = f'<code>{html.escape(step["tid"])}</code>' if step.get("tid") else f'<span class="sel">{html.escape(step["selector"])}</span>'
        pressed = f'<div class="btn"><span class="k">누름</span> <b>{html.escape(label or "(문구 없음)")}</b><br>{sel}</div>'
    else:
        pressed = '<div class="btn none">도착 화면 · 누른 것 없음</div>'
    desc = f'<p class="desc">{html.escape(step["desc"])}</p>' if step.get("desc") else ""
    path = f'<div class="path">{html.escape(step["path"])}</div>'
    arrow = "" if last else '<div class="arrow" aria-hidden="true">→</div>'
    return (f'<figure class="card{" narrow" if narrow else ""}"><div class="no">{step["n"]}</div>'
            f'<img loading="lazy" src="{img}" alt="{html.escape(title)}" data-full="{img}" data-cap="{html.escape(title)}">'
            f'<figcaption><div class="t">{html.escape(title)}</div>{pressed}{desc}{path}</figcaption></figure>{arrow}')


def main():
    toc, rows, total = [], [], 0
    for num, title, intro, lanes in SCENARIOS:
        lane_html = []
        for key, lane, overrides in lanes:
            meta = json.loads((R / "raw" / f"{key}.json").read_text(encoding="utf-8"))
            steps = meta["steps"]; total += len(steps)
            cards = "".join(card(s, overrides, i == len(steps) - 1, meta["width"] < 600) for i, s in enumerate(steps))
            note = NOTES.get(key, "")
            lane_html.append(f'<div class="lane"><div class="lanehead"><span class="lane-name">{html.escape(lane)}</span>'
                             f'<span class="meta">{len(steps)}단계 · 폭 {meta["width"]}</span>'
                             + (f'<span class="note">{html.escape(note)}</span>' if note else "") +
                             f'</div><div class="row">{cards}</div></div>')
        toc.append(f'<li><a href="#sc{num}">{num}. {html.escape(title)}</a></li>')
        rows.append(f'<section id="sc{num}"><h2>{num}. {html.escape(title)}</h2><p class="intro">{html.escape(intro)}</p>{"".join(lane_html)}</section>')
    OUT.write_text(TEMPLATE.replace("{{TOC}}", "".join(toc)).replace("{{ROWS}}", "".join(rows)).replace("{{TOTAL}}", str(total)), encoding="utf-8")
    print("wrote", OUT, "steps", total)


TEMPLATE = """<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>OhMyEnglish 사용자 시나리오 화면 보드 · 2026-11-01</title>
<style>
:root { --bg:#f4f5f8; --fg:#1b1f2a; --muted:#667085; --card:#fff; --line:#e3e6ee; --accent:#ff2d55; --link:#3157d5; }
* { box-sizing:border-box; } body { margin:0; font:14px/1.5 -apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Segoe UI",sans-serif; background:var(--bg); color:var(--fg); }
header { padding:28px 32px 12px; } h1 { margin:0 0 6px; font-size:24px; } .sub { color:var(--muted); margin:0; }
.legend { margin:12px 0 0; padding:12px 14px; background:#fff; border:1px solid var(--line); border-radius:10px; max-width:1100px; }
.legend li { margin:2px 0; } .mark { display:inline-block; width:14px; height:10px; border:3px solid var(--accent); border-radius:3px; vertical-align:middle; }
nav.toc { position:sticky; top:0; z-index:5; background:rgba(244,245,248,.95); backdrop-filter:blur(4px); border-bottom:1px solid var(--line); padding:8px 32px; }
nav.toc ol { margin:0; padding:0; list-style:none; display:flex; flex-wrap:wrap; gap:6px 14px; } nav.toc a { color:var(--link); text-decoration:none; } nav.toc a:hover { text-decoration:underline; }
section { padding:18px 0 6px; border-bottom:1px solid var(--line); } section h2 { margin:0 32px 4px; font-size:19px; } .intro { margin:0 32px 8px; color:#344054; max-width:1100px; }
.lane { margin:6px 0 14px; } .lanehead { margin:0 32px 6px; display:flex; flex-wrap:wrap; gap:4px 12px; align-items:baseline; }
.lane-name { font-weight:600; } .meta { color:var(--muted); font-size:12px; } .note { color:#7a5b00; background:#fff7db; border:1px solid #f3e2a6; border-radius:6px; padding:1px 8px; font-size:12px; }
.row { display:flex; align-items:flex-start; overflow-x:auto; padding:6px 32px 14px; gap:0; scroll-snap-type:x proximity; }
.card { position:relative; flex:0 0 auto; width:340px; margin:0; background:var(--card); border:1px solid var(--line); border-radius:12px; box-shadow:0 1px 3px rgba(16,24,40,.06); overflow:hidden; scroll-snap-align:start; }
.card img { display:block; width:100%; height:240px; object-fit:cover; object-position:top; cursor:zoom-in; border-bottom:1px solid var(--line); background:#eef0f4; }
.no { position:absolute; top:8px; left:8px; background:var(--fg); color:#fff; border-radius:99px; min-width:24px; height:24px; text-align:center; line-height:24px; font-size:12px; font-weight:700; }
figcaption { padding:10px 12px 12px; } .t { font-weight:600; margin-bottom:6px; }
.btn { font-size:12.5px; background:#fff1f4; border:1px solid #ffc7d3; border-radius:8px; padding:6px 8px; } .btn .k { color:var(--accent); font-weight:700; }
.btn code, .btn .sel { font:12px ui-monospace,SFMono-Regular,Menlo,monospace; color:#475467; word-break:break-all; } .btn.none { background:#f2f4f7; border-color:var(--line); color:var(--muted); }
.desc { margin:6px 0 0; color:#344054; font-size:12.5px; } .path { margin-top:6px; font:11px ui-monospace,Menlo,monospace; color:var(--muted); word-break:break-all; }
.arrow { flex:0 0 auto; width:44px; margin-top:105px; text-align:center; font-size:28px; color:#98a2b3; }
.card.narrow { width:220px; } .card.narrow img { height:420px; }
#lb { position:fixed; inset:0; background:rgba(10,12,18,.86); display:none; align-items:center; justify-content:center; flex-direction:column; z-index:50; cursor:zoom-out; padding:20px; }
#lb.on { display:flex; } #lb img { max-width:96vw; max-height:88vh; border-radius:8px; background:#fff; } #lb div { color:#fff; margin-top:10px; font-size:15px; }
footer { padding:18px 32px 40px; color:var(--muted); font-size:12.5px; }
</style></head><body>
<header>
<h1>OhMyEnglish 사용자 시나리오 화면 보드</h1>
<p class="sub">대상 커밋 63e1bdc(r2 · TASK-307 반영) · 2026-11-01 · 시나리오 10개(갈래 포함 14줄) · 단계 {{TOTAL}}개 · 모든 화면은 실제 앱을 조작해 찍은 것임</p>
<ul class="legend">
<li>각 줄은 한 시나리오를 왼쪽에서 오른쪽으로 보임. 줄이 넓으면 가로로 스크롤함.</li>
<li>화면 안의 <span class="mark"></span> 빨간 테두리는 그 단계에서 사용자가 다음으로 누른 요소임. 카드 아래 「누름」 칸에 화면 문구(영어 UI)와 data-testid 를 적었음. testid 가 없는 요소는 고른 방법을 적었음.</li>
<li>썸네일을 누르면 크게 봄. 다시 누르거나 Esc 로 닫음.</li>
<li>스택: 프런트 :3000(next dev) · 백엔드 :8002(VOICE_ADAPTER=stub · WORKER_ENABLED=false) · 격리 DB ohmyenglish_course_paid · 헤드리스 Chrome 가짜 마이크. 그래서 말하기 판정 대신 「I can't check your speaking now」 가, 새 결과 화면에는 Checking… 이 뜸.</li>
<li>오늘의 연습 카드는 대기·연습·세션·실패에서 같은 고정 높이를 씀(TASK-307 · 1400 폭 528 px · 390 폭 672 px). 문장 연습은 카드 안쪽 스크롤 없이 다 보임.</li>
<li>세션을 시작해도 창은 스크롤하지 않음. 그래서 아래쪽 버튼(More practice 등)으로 시작한 세션은 카드가 보이게 맨 위로 올려 찍었음 — 390 폭에서는 누른 직후 카드가 화면 밖에 있음.</li>
<li>알려진 결함(r2 측정): 390 폭에서 판정 상자(You said)의 낱말 줄이 줄바꿈되지 않아, 긴 문장이면 카드가 화면보다 넓어지고 ← Close · Next · Auto 가 화면 밖으로 밀림. 이 보드의 단계 화면에는 나오지 않음(stub 은 판정 상자를 띄우지 않음).</li>
</ul>
</header>
<nav class="toc"><ol>{{TOC}}</ol></nav>
{{ROWS}}
<footer>드라이버와 단계 기록: tests/agent/runs/2026-11-01-b13/ (s01.mjs ~ s10.mjs · sess.mjs · raw/*.json). 보드 생성: make_board.py.</footer>
<div id="lb" role="dialog" aria-modal="true"><img alt=""><div></div></div>
<script>
(() => { const lb = document.getElementById('lb'), im = lb.querySelector('img'), cap = lb.querySelector('div');
  document.addEventListener('click', (e) => { const t = e.target; if (t.matches('.card img')) { im.src = t.dataset.full; cap.textContent = t.dataset.cap; lb.classList.add('on'); } else if (lb.contains(t)) lb.classList.remove('on'); });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') lb.classList.remove('on'); }); })();
</script>
</body></html>
"""

if __name__ == "__main__":
    main()
