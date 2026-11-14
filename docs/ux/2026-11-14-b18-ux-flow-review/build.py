"""회차 b18(고친 뒤 전체 재시험) 흐름·논리 점검 보고서를 만든다 — `python3 build.py` 가 같은 폴더에 index.html 을 씀.

근거: tests/agent/runs/2026-11-14-b18/{screens,buttons}/result.md 와 호출자 대조.
썸네일은 옆 폴더의 b18 스토리보드(../2026-11-14-b18-user-scenarios/shots/)를 씀. b16 판은 그대로 남김.
"""

from html import escape
from pathlib import Path

SHOTS = "../2026-11-14-b18-user-scenarios/shots/"

# b16 보고서 항목의 지금 상태 — (b16 항목, 지금, 근거)
B16 = [
    ("B-D1 Start speaking 때 창이 튐", "고쳐짐", "버튼 탭 1400×860 · 1400×700 · 390 통과(1400×900 은 스크롤 여지 0 이라 불확실) · TASK-319"),
    ("S-D2 홈과 /course 의 Day 상태", "고쳐짐", "/course 는 홈으로 넘어감 · 홈 Day 상태와 진도 수가 맞음 · TASK-322·323"),
    ("S-D1 390 영상 잘림", "고쳐짐", "390 body.scrollWidth 390 · TASK-321"),
    ("B-D2 홈 → 가 파란 바탕 아님", "고쳐짐", "TASK-320"),
    ("B-D4 testid 없음", "일부 남음", "영상 두 화면만 남음 → 새 결함 B18-D1(TASK-332)"),
    ("A 같은 일을 하는 두 입구(빠른 카드 · Grammar course · 옛 코스)", "고쳐짐", "TASK-323"),
    ("B 기간 표시(진도 · 주간 · 결과 · Day 상태)", "고쳐짐 · 남은 것 N1·N6·N7", "TASK-329"),
    ("C 이름(Back · Not checked · Mark start)", "고쳐짐 · 남은 것 N5", "TASK-329"),
    ("D 되돌아갈 길(기록 날짜 줄 · 주간 ← Home)", "고쳐짐", "세션 여럿인 날 확인 · 하나인 날은 데이터 없어 불확실 · TASK-329"),
    ("E 빈 세션 칭찬 · 말한 내용이 안 보임", "고쳐짐 · 남은 것 N4", "TASK-329 · TASK-317(사용자 실기기 확인)"),
    ("F 버튼 모양 기준", "고쳐짐 · 남은 것 X1·X2", "TASK-323"),
]

# (ID, 장면, 무엇이 헷갈리는가, 근거 사진, 보완안, 사용자 결정 필요)
FLOWS = [
    ("N1", "홈 Your progress", "「Last week · Nov 2 – Nov 8」 꼬리표 아래에 Best streak 이 함께 놓임. Best streak 은 전체 기간 값이라 지난주 값으로 읽힘.",
     "home_idle-1400-01.jpg", "Best streak 을 꼬리표 위(진도 줄)로 옮기고 꼬리표는 Sessions·Patterns 만 덮음.", False),
    ("N2", "문장 연습 결과", "「You said:」 바로 아래에 원문 줄이 이름표 없이 거의 같은 문장으로 다시 나옴. 다 맞으면 같은 말이 두 번 보임.",
     "home_practice-1400-04.jpg", "다 맞으면 둘째 줄 대신 「All words matched」 한 줄 · 아니면 둘째 줄에 「Sentence:」 이름표.", True),
    ("N3", "코치 세션", "More practice 의 「Free talk」로 열었는데 세션 제목은 「English talk」.",
     "coach-1400-03.jpg", "세션 제목을 누른 버튼 이름과 맞춤.", False),
    ("N4", "발화 없는 결과", "「Start again →」와 「← Home」이 둘 다 홈으로 감. 「Start again」은 그 학습을 다시 여는 것으로 읽힘.",
     "coach-1400-04.jpg", "같은 학습을 바로 다시 열거나, 이름을 「Back to Home」으로 바꾸고 「← Home」을 뺌.", True),
    ("N5", "기록", "발화 0건뿐인 날도 「Not analyzed yet」으로 보여 나중에 분석될 것처럼 읽힘. 연속 학습일도 말하지 않은 세션을 셈.",
     "history-1400-03.jpg", "발화 0건뿐인 날은 「Nothing said」로 적음 · 연속 학습일에서 발화 0건 세션을 뺄지 정함.", True),
    ("N6", "주간 리포트", "「Try this week」 제목 아래 본문이 「Nothing to show for last week.」",
     "weekly-1400-01.jpg", "그 절의 빈 문구를 「No suggestions yet.」처럼 기간 없는 말로 바꿈.", False),
    ("N7", "지난 세션 결과", "11-01 세션 결과에 「Today's drill was shorter than planned.」가 남음(하네스 기대값이라 남겨 둔 문구).",
     "results-1400-01.jpg", "하네스 기대값과 함께 「This drill was shorter than planned.」로 바꿈.", False),
    ("N8", "기록", "공부하지 않은 날짜가 모두 줄로 나와 공부한 날이 묻힘.",
     "history-1400-03.jpg", "공부한 날만 보이거나 빈 날을 「No study · Nov 2 – Nov 13」 한 줄로 접음.", True),
    ("N9", "영상 목록", "링크 저장 버튼 이름이 「Check」라 무엇을 하는지 모름.",
     "videos-1400-01.jpg", "「Save video」로 바꿈.", False),
    ("N10", "홈 대기(KO 켬)", "KO 를 켜면 대기 카드가 558 px 인데 내용은 제목·설명 두 줄이라 남색 빈 자리가 큼(대기 = 연습 높이 결정의 결과).",
     "home_idle-1400-02.jpg", "대기 = 연습 높이를 유지할지 정함(TASK-310·328 결정).", True),
    ("X1", "홈 대기", "「Start speaking」만 홈 버튼 기준(omy-button)이 아님 — 남색 카드 위 흰 버튼이고 예외로 적혀 있지 않음.",
     "home_idle-1400-01.jpg", "남색 카드 위 예외로 설계서에 적거나 기준 모양으로 맞춤.", True),
    ("X2", "More practice", "「Learn with videos」는 다른 화면으로 가는 이동인데 회색임(「앞으로 가는 이동만 파란 바탕」 규칙에 이 경우가 없음).",
     "home_idle-1400-01.jpg", "More practice 묶음은 회색으로 둔다고 규칙에 적음(권장) 또는 파란 바탕.", False),
    ("X3", "문장 연습", "KO 버튼은 글자가 「KO」뿐이라 처음 보면 무엇을 켜는지 모를 수 있음.",
     "home_practice-1400-02.jpg", "툴팁(title)을 붙이거나 「KO 번역」처럼 이름을 늘림.", False),
]

LIMITS = [
    "영상 화면의 「구간 끝」 성공 경로는 차단됨 — 헤드리스에서 영상 재생 위치가 0:00 에 머묾(버튼 탭 N17 두 폭).",
    "기록에서 세션이 하나뿐인 날의 바로가기는 시험 데이터가 없어 불확실(화면 탭 S6b).",
    "실시간 표시는 가짜 인식기로만 잼 — 진짜 인식 품질은 사용자 실기기 확인(TASK-317)이 근거.",
    "Nova 세션은 탭마다 2개(상한 안) · 모두 발화 0건. dev DB 는 회차 전후 같음.",
]

CSS = """
body{font-family:-apple-system,BlinkMacSystemFont,'Apple SD Gothic Neo',sans-serif;margin:0;background:#f6f7fb;color:#172036;line-height:1.55}
header{background:#172b63;color:#fff;padding:28px 40px}
header h1{margin:0 0 6px;font-size:24px} header p{margin:2px 0;color:#d6dcf0;font-size:14px}
header code{background:rgba(255,255,255,.16);color:#fff}
main{max-width:1180px;margin:0 auto;padding:24px 32px 60px}
h2{font-size:19px;margin:34px 0 10px}
.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
.card{background:#fff;border:1px solid #e3e6ef;border-radius:14px;padding:14px 16px}
.card b{display:block;font-size:26px} .card span{font-size:12px;color:#5b6478}
table{width:100%;border-collapse:collapse;background:#fff;border:1px solid #e3e6ef;font-size:14px}
th,td{padding:10px 12px;border-bottom:1px solid #eef0f5;vertical-align:top;text-align:left}
th{background:#f0f2f8;font-size:12px;color:#5b6478;text-transform:uppercase;letter-spacing:.06em}
td:first-child{white-space:nowrap}
td img{width:180px;border:1px solid #e3e6ef;border-radius:8px;display:block}
.ok{color:#1d7a46;font-weight:700}.part{color:#8a5a00;font-weight:700}
.dec{display:inline-block;padding:2px 8px;border-radius:99px;font-size:12px;font-weight:700;background:#ede7fb;color:#5b34b5}
.note{font-size:13px;color:#5b6478} ul{margin:6px 0 0 18px} code{background:#eef0f5;padding:1px 5px;border-radius:5px;font-size:12px}
a{color:#2c4fb5}
"""


def img(name: str) -> str:
    src = SHOTS + name
    return f'<a href="{src}" target="_blank"><img loading="lazy" src="{src}" alt="{escape(name)}"></a>'


def b16_table() -> str:
    rows = "".join(
        f"<tr><td>{escape(item)}</td><td class='{'ok' if now == '고쳐짐' else 'part'}'>{escape(now)}</td><td>{escape(why)}</td></tr>"
        for item, now, why in B16
    )
    return f"<table><tr><th>b16 항목</th><th>지금</th><th>근거</th></tr>{rows}</table>"


def flows_table() -> str:
    rows = []
    for fid, scene, what, shot, fix, decide in FLOWS:
        badge = " <span class='dec'>사용자 결정</span>" if decide else ""
        rows.append(f"<tr><td><b>{fid}</b></td><td>{escape(scene)}</td><td>{escape(what)}</td><td>{img(shot)}</td><td>{escape(fix)}{badge}</td></tr>")
    head = "<tr><th>ID</th><th>장면</th><th>무엇이 헷갈리는가</th><th>근거</th><th>보완안</th></tr>"
    return f"<table>{head}{''.join(rows)}</table>"


def main() -> None:
    n_dec = sum(1 for item in FLOWS if item[5])
    html = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<title>OhMyEnglish 흐름·논리 점검 보고 — 회차 b18 (고친 뒤 재시험)</title><style>{CSS}</style></head><body>
<header><h1>OhMyEnglish 흐름·논리 점검 보고 — 회차 2026-11-14-b18 (고친 뒤 재시험)</h1>
<p>TestAgent(전용 런처 · OS 샌드박스) 두 개를 Paseo 탭 둘(화면 · 버튼)에서 Playwright(CDP)로 다시 돌린 결과와 내 대조를 합침.</p>
<p>대상 HEAD <code>8cec9d2</code> 이후 · 시험용 백엔드 :8002 격리 DB · 1400×1000 과 390×844. 앞 판(b16)은 <a style="color:#fff" href="../2026-11-14-ux-flow-review/index.html">여기</a>에 그대로 있음.</p></header>
<main>
<div class="cards">
<div class="card"><b>143 / 146</b><span>버튼 동작 통과(실패 0 · 차단 2 · 불확실 1)</span></div>
<div class="card"><b>30 단계</b><span>화면 10장면 두 폭 통과(불확실 1)</span></div>
<div class="card"><b>1</b><span>새 결함(B18-D1 · TASK-332)</span></div>
<div class="card"><b>{len(FLOWS)}</b><span>새 흐름 관찰(사용자 결정 {n_dec})</span></div>
</div>
<p class="note">새 스토리보드: <a href="../2026-11-14-b18-user-scenarios/index.html">10장면 · 30단계 · 1400/390</a> (KO 켬·끔 · 실시간 표시 포함).</p>

<h2>1. b16 보고서 항목 — 고쳐졌는가</h2>{b16_table()}

<h2>2. 새 결함</h2>
<table><tr><th>ID</th><th>문제</th><th>보완안</th><th>태스크</th></tr>
<tr><td><b>B18-D1</b></td><td>영상 목록·영상 화면의 버튼과 링크에 testid 가 없음(b16 D4 잔여). 소스에서 내가 확인함 — 두 화면 모두 testid 가 돌아가기 링크 하나뿐.</td>
<td>videos-check · videos-delete · video-mark-start 같은 testid 를 붙임.</td><td><code>TASK-332</code></td></tr></table>

<h2>3. 새 흐름·논리 관찰과 보완안</h2>
<p class="note">모두 결함이 아니라 판단이 필요한 관찰임. <span class='dec'>사용자 결정</span> 표시는 무엇을 남기고 바꿀지 정해 주셔야 진행할 수 있는 항목임. 나머지는 문구·배치를 바로 고칠 수 있는 항목임.</p>
{flows_table()}

<h2>4. 이번 회차가 재지 못한 것</h2><ul>{''.join(f'<li>{escape(x)}</li>' for x in LIMITS)}</ul>

<h2>5. 근거 파일</h2><ul>
<li>화면 탭: <code>tests/agent/runs/2026-11-14-b18/screens/result.md</code></li>
<li>버튼 탭: <code>tests/agent/runs/2026-11-14-b18/buttons/result.md</code></li>
<li>dev DB 전후: <code>tests/agent/runs/2026-11-14-b18/db-dev-start.json</code> = <code>db-dev-end.json</code></li></ul>
</main></body></html>
"""
    Path(__file__).with_name("index.html").write_text(html, encoding="utf-8")
    print("written", len(html.splitlines()), "lines")


if __name__ == "__main__":
    main()
