"""회차 b16 흐름·논리 점검 보고서를 만든다 — `python3 build.py` 가 같은 폴더에 index.html 을 씀.

근거: tests/agent/runs/2026-11-14-b16/{screens,buttons}/result.md 와 호출자 대조(verify/*.mjs).
썸네일은 옆 폴더의 새 스토리보드(../2026-11-14-user-scenarios/shots/)를 씀.
"""

from html import escape
from pathlib import Path

SHOTS = "../2026-11-14-user-scenarios/shots/"

# (ID, 등급, 제목, 근거 사진들, 무엇이 문제인가, 보완안, 확인 상태, 태스크·결정)
DEFECTS = [
    ("B-D1", "높음", "Start speaking 을 누르면 창이 맨 위로 튐(1400×900)",
     ["home_practice-1400-02.jpg"],
     "연습이 뜨는 첫 순간 카드가 433→335px 로 줄어 문서가 창보다 짧아지고 스크롤이 0 에 붙음. 사용자가 정한 「Start speaking 은 창을 움직이지 않음」을 어김.",
     "연습 로딩 중에도 카드에 대기와 같은 최소 높이를 줌.",
     "직접 재현함 — scrollY 40→0 · 카드 최저 335px", "TASK-319"),
    ("S-D2", "높음", "같은 Day 를 홈은 In progress, /course 는 Not started 로 보임",
     ["view_all-1400-02.jpg", "course-1400-01.jpg"],
     "홈 판정은 진도 행이 있기만 하면(지난 회차 것 포함) 진행 중으로 봄. Your progress 는 같은 화면에서 0 / 6 days 라 화면 안에서도 모순임.",
     "두 화면이 판정 함수 하나를 씀(이번 회차 완료 · 시작 위치 이탈 기준).",
     "직접 재현함 — 홈 D2~D5 started · /course D2~D5 Not started", "TASK-322"),
    ("S-D1", "중간", "390 폭 영상 화면에서 영상 오른쪽 302px 가 잘림",
     ["videos-390-02.jpg"],
     "iframe 이 640px 고정이고 body 가 가로 스크롤을 막아 재생 버튼이 반쯤 잘림.",
     "width 100% + aspect-ratio 16/9 (Day 화면과 같은 방식).",
     "직접 재현함 — body.scrollWidth 692", "TASK-321"),
    ("B-D2", "낮음", "홈의 History → · Weekly report → 만 파란 바탕이 아님",
     ["home_idle-1400-01.jpg"],
     "다른 화면의 같은 → 이동은 파란 바탕(omy-button-primary)임. 홈만 회색이라 규칙이 갈림.",
     "두 링크에 omy-button-primary 를 줌.", "코드로 확인함", "TASK-320"),
    ("B-D4", "낮음", "End lesson · 실패 화면 Try again 등에 testid 없음",
     ["coach-1400-03.jpg"],
     "시험이 문구로 버튼을 골라야 해 문구가 바뀌면 시험이 조용히 깨짐. 사용자에게 보이는 문제는 아님.",
     "data-testid 를 붙임.", "탭 보고", "TASK-320"),
]

# (주제, [(장면, 무엇이 헷갈리는가, 근거 사진, 보완안, 결정 필요)])
FLOWS = [
    ("A. 같은 일을 하는 입구가 둘 — 사용자는 다른 학습이라고 기대함", [
        ("홈 대기", "빠른 카드 Shadow a sentence = More practice 의 Shadowing, Repair your mistakes = Weak spots, Listen &amp; notice = Learn with videos. 코드도 같은 입구를 씀.",
         "home_idle-1400-01.jpg", "빠른 카드를 More practice 의 「추천」 표시로 합치거나 한쪽을 뺌.", True),
        ("홈 대기", "More practice 의 Grammar course 와 Start speaking 이 같은 일(현재 Day 문장 연습)을 함.",
         "home_idle-1400-01.jpg", "Grammar course 를 뺌. 남기려면 「Opens above」 안내를 붙임.", True),
        ("/course · /course/1", "메뉴에서는 빠졌지만 결과 화면 등에서 닿고, Start·Continue 가 영상이 있는 옛 Day 화면으로 들어감. 「학습은 홈에서만」 결정과 다른 두 번째 학습 길임.",
         "course-1400-01.jpg", "/course 와 /course/&lt;day&gt; 를 홈으로 넘기고, 그곳을 가리키는 버튼을 홈 Day 줄로 바꿈.", True),
    ]),
    ("B. 상태·기간 표시가 서로 맞지 않음", [
        ("홈 Continue your path", "모든 Day 가 In progress 인데 Your progress 는 0 / 6 days.",
         "view_all-1400-02.jpg", "S-D2 를 고침.", False),
        ("홈 Your progress", "Sessions·Patterns 는 지난주 리포트 값인데 「This week: 0 / 7 days」 바로 아래에 있어 이번 주 값으로 읽힘.",
         "home_idle-1400-01.jpg", "줄 이름을 「Last week」처럼 기간이 보이게 바꿈.", False),
        ("주간 리포트", "11-14 에 열면 11/2~11/8(지난주)을 보이는데 본문은 「this week」라고 함.",
         "weekly-1400-01.jpg", "제목에 기간(Nov 2 – Nov 8)을 넣고 본문의 this week 를 고침.", False),
        ("결과 화면", "11-01 세션 결과를 11-14 에 열어도 「You finished today」. 문구가 고정돼 있음.",
         "results-1400-02.jpg", "세션 날짜로 문구를 만듦(「You finished on Nov 1」).", False),
    ]),
    ("C. 이름과 하는 일이 다름", [
        ("홈 문장 연습", "카드 머리 「← Close」(카드 닫기)와 아래 「← Back」(이전 문장)이 같은 왼쪽 화살표라 Back 이 홈으로 가는 버튼으로 읽힘.",
         "home_practice-1400-02.jpg", "아래 버튼을 「← Previous」로 바꿈.", False),
        ("기록", "「Not checked」가 무엇을 확인하지 않았다는 뜻인지 설명이 없음.",
         "history-1400-01.jpg", "「Not analyzed yet」으로 바꾸고 언제 분석되는지 한 줄을 붙임.", False),
        ("영상 화면", "「Mark start」만 보고는 무엇을 하는지 모름. 아래 문장을 읽어야 앎.",
         "videos-1400-02.jpg", "「Mark a hard part」로 바꾸거나 설명을 버튼 옆으로 올림.", False),
    ]),
    ("D. 되돌아갈 길이 없음", [
        ("기록", "공부한 날 줄이 눌리지 않음. 지난 결과로 돌아갈 길이 없고 결과 화면은 세션 직후에만 닿음.",
         "history-1400-02.jpg", "날짜 줄을 그날의 결과(세션 목록)로 연결함.", False),
        ("주간 리포트", "홈에서 들어와도 돌아가는 버튼이 「← History」뿐임. 390 에서는 로고만 홈으로 감.",
         "weekly-390-01.jpg", "「← Home」을 함께 둠(결과 화면처럼).", False),
    ]),
    ("E. 사실과 다른 칭찬", [
        ("코치 세션 결과", "한마디도 안 한 15초 세션 뒤에 「Nothing to check · You finished today」.",
         "coach-1400-04.jpg", "발화 0건이면 「We didn't hear you this time」과 다시 시작 버튼을 보임.", False),
        ("문장 연습", "말한 내용이 판정이 끝날 때까지(최대 약 30초) 화면에 안 나오고 빈 결과가 이어짐.",
         "home_practice-1400-04.jpg", "진행 중: 말하는 동안 글자를 보이는 실시간 표시(Web Speech) — 사용자 결정 완료.", False),
    ]),
    ("F. 모양 기준의 범위", [
        ("홈 · 세션 · 영상", "More practice 8개 · View all · Practice a pattern · End lesson · 영상 화면 Check/Delete/Mark 가 홈 버튼 기준(36px · 13.6px)과 다름.",
         "home_idle-1400-01.jpg", "이 버튼들을 기준에 넣을지 정함. 넣으면 모두 omy-button 으로 바꿈.", True),
    ]),
]

LIMITS = [
    "세션 실패(마이크 거부) 화면은 재지 못했음 — 시험 Chrome 의 가짜 권한 UI 가 거부를 우회해 스트림을 줌. 앱 결함이 아님.",
    "화면 탭이 Nova 세션을 상한(2개)보다 많은 4개 열었음 — 마이크 거부 재시도가 세션을 그대로 열었기 때문. 모두 닫혔고 발화는 0건.",
    "코치 세션의 전사·코치 발화 품질은 판정하지 않음 — 가짜 마이크 소리는 말이 아님.",
    "Day 마치기 · 약점 연습 · 쉐도잉 장면은 이번 보드에 없음(문장 수십 개 · Nova 세션 상한).",
    "흐름 문제 가운데 빠른 카드 · 기록 날짜 줄 · 결과 문구는 내가 코드로 다시 확인했음. 나머지는 TestAgent 판단이고 근거 사진을 붙였음.",
]

CSS = """
body{font-family:-apple-system,BlinkMacSystemFont,'Apple SD Gothic Neo',sans-serif;margin:0;background:#f6f7fb;color:#172036;line-height:1.55}
header{background:#172b63;color:#fff;padding:28px 40px}
header h1{margin:0 0 6px;font-size:24px} header p{margin:2px 0;color:#d6dcf0;font-size:14px}
main{max-width:1180px;margin:0 auto;padding:24px 32px 60px}
h2{font-size:19px;margin:34px 0 10px} h3{font-size:16px;margin:24px 0 8px}
.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
.card{background:#fff;border:1px solid #e3e6ef;border-radius:14px;padding:14px 16px}
.card b{display:block;font-size:26px} .card span{font-size:12px;color:#5b6478}
table{width:100%;border-collapse:collapse;background:#fff;border:1px solid #e3e6ef;border-radius:12px;overflow:hidden;font-size:14px}
th,td{padding:10px 12px;border-bottom:1px solid #eef0f5;vertical-align:top;text-align:left}
th{background:#f0f2f8;font-size:12px;color:#5b6478;text-transform:uppercase;letter-spacing:.06em}
td img{width:180px;border:1px solid #e3e6ef;border-radius:8px;display:block;margin-bottom:4px}
.sev{display:inline-block;padding:2px 8px;border-radius:99px;font-size:12px;font-weight:700}
.높음{background:#fde2e1;color:#a4231f}.중간{background:#fff1d6;color:#8a5a00}.낮음{background:#e6ecfb;color:#2c4fb5}
.dec{display:inline-block;padding:2px 8px;border-radius:99px;font-size:12px;font-weight:700;background:#ede7fb;color:#5b34b5}
.note{font-size:13px;color:#5b6478} ul{margin:6px 0 0 18px} code{background:#eef0f5;padding:1px 5px;border-radius:5px;font-size:12px}
a{color:#2c4fb5}
header code{background:rgba(255,255,255,.16);color:#fff}
td:first-child{white-space:nowrap}
"""


def img(name: str) -> str:
    src = SHOTS + name
    return f'<a href="{src}" target="_blank"><img loading="lazy" src="{src}" alt="{escape(name)}"></a>'


def defects_table() -> str:
    rows = []
    for did, sev, title, shots, what, fix, check, task in DEFECTS:
        rows.append(
            f"<tr><td><b>{did}</b><br><span class='sev {sev}'>{sev}</span></td>"
            f"<td><b>{escape(title)}</b><br>{escape(what)}<br><span class='note'>확인: {escape(check)}</span></td>"
            f"<td>{''.join(img(s) for s in shots)}</td><td>{escape(fix)}</td><td><code>{task}</code></td></tr>"
        )
    head = "<tr><th>ID</th><th>문제</th><th>근거</th><th>보완안</th><th>태스크</th></tr>"
    return f"<table>{head}{''.join(rows)}</table>"


def flows_html() -> str:
    out = []
    for theme, items in FLOWS:
        rows = []
        for scene, what, shot, fix, decide in items:
            badge = " <span class='dec'>사용자 결정</span>" if decide else ""
            rows.append(f"<tr><td>{scene}</td><td>{what}</td><td>{img(shot)}</td><td>{fix}{badge}</td></tr>")
        head = "<tr><th>장면</th><th>무엇이 헷갈리는가</th><th>근거</th><th>보완안</th></tr>"
        out.append(f"<h3>{theme}</h3><table>{head}{''.join(rows)}</table>")
    return "".join(out)


def main() -> None:
    n_flow = sum(len(items) for _, items in FLOWS)
    n_dec = sum(1 for _, items in FLOWS for it in items if it[4])
    html = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<title>OhMyEnglish 흐름·논리 점검 보고 — 회차 b16</title><style>{CSS}</style></head><body>
<header><h1>OhMyEnglish 흐름·논리 점검 보고 — 회차 2026-11-14-b16</h1>
<p>TestAgent(전용 런처 · OS 샌드박스) 두 개를 Paseo 탭 둘(화면 · 버튼)에서 Playwright(CDP)로 돌린 결과와 내 대조를 합침.</p>
<p>대상 HEAD <code>a5ac4bf</code>(앱 코드 <code>e26e89d</code> 이후 같음) · 시험용 백엔드 :8002 격리 DB · 1400×1000 과 390×844.</p></header>
<main>
<div class="cards">
<div class="card"><b>96 / 97</b><span>버튼 동작 통과</span></div>
<div class="card"><b>11 / 13</b><span>화면 판정 통과(실패 1 · 차단 1)</span></div>
<div class="card"><b>{len(DEFECTS)}</b><span>결함(태스크 등록함)</span></div>
<div class="card"><b>{n_flow}</b><span>흐름·논리 문제(사용자 결정 {n_dec})</span></div>
</div>
<p class="note">새 스토리보드: <a href="../2026-11-14-user-scenarios/index.html">12장면 · 27단계 · 1400/390</a>
(옛 보드 2026-11-01 판은 없어진 메뉴·경로를 거쳐 새로 만들었음).</p>

<h2>1. 결함 — 고칠 것</h2>{defects_table()}

<h2>2. 흐름·논리 문제와 보완안</h2>
<p class="note">기준: ① 다음 할 일이 화면만으로 보이는가 · ② 이름과 하는 일이 맞는가 · ③ 막다른 곳 · 되돌아갈 길 없음 · 같은 일을 하는 두 입구.
<span class='dec'>사용자 결정</span> 표시는 무엇을 남기고 뺄지 정해 주셔야 진행할 수 있는 항목임.</p>
{flows_html()}

<h2>3. 이번 회차가 재지 못한 것</h2><ul>{''.join(f'<li>{escape(x)}</li>' for x in LIMITS)}</ul>

<h2>4. 근거 파일</h2><ul>
<li>화면 탭: <code>tests/agent/runs/2026-11-14-b16/screens/result.md</code> · <code>screens/evidence/</code></li>
<li>버튼 탭: <code>tests/agent/runs/2026-11-14-b16/buttons/result.md</code> · <code>buttons/evidence/</code></li>
<li>내 대조: <code>tests/agent/runs/2026-11-14-b16/verify/d1.mjs</code> · <code>verify/screens.mjs</code></li>
<li>dev DB 는 회차 전후 같음(<code>db-dev-start.json</code> = <code>db-dev-end.json</code>).</li></ul>
</main></body></html>
"""
    Path(__file__).with_name("index.html").write_text(html, encoding="utf-8")
    print("written", len(html.splitlines()), "lines")


if __name__ == "__main__":
    main()
