"""개요서·README·추적표·보관 README 의 링크와 경로 표기가 실재하는지 확인한다 (`TASK-262`).

⛔ **문서를 고친 뒤 이것을 돌린다** — 문서 지도는 경로로 이어져 있고, 경로가 끊긴 지도는
지도가 아니라 소음이다. 2026-09-20 에 이 검사가 실제로 낡은 경로 하나를 잡았다(추적표가 옮겨진
현황 보고를 가리키고 있었다).

⚠️ **짧은 모듈 이름은 검사하지 않는다** — `plan.py` 같은 표기는 경로가 아니라 지시어이고, 그것을
끊김으로 세면 검사가 소음이 되어 진짜 낡은 경로를 가린다(`TOPS` 가 그 경계다).

    python3 scripts/check_doc_links.py      # 리포 뿌리에서
"""

import re
import sys
from pathlib import Path

ROOT = Path(".")
TARGETS = {
    "docs/overview.html": Path("docs"),
    "README.md": Path("."),
    "docs/backup/2026-09-20-superseded/README.md": Path("docs/backup/2026-09-20-superseded"),
    "docs/requirements-tracking.html": Path("docs"),
}
bad = ok = 0
for doc, base in TARGETS.items():
    text = Path(doc).read_text()
    links = set(re.findall(r'href="([^"#][^"]*)"', text)) | set(
        re.findall(r"\]\(([^)#][^)]*)\)", text)
    )
    for link in sorted(links):
        if link.startswith(("http://", "https://", "mailto:")):
            continue
        path = link.split("#")[0]
        if not path:
            continue
        if (base / path).exists():
            ok += 1
        else:
            bad += 1
            print(f"  끊긴 링크: {doc} -> {link}")
    # ⛔ 리포 기준 경로만 검사한다 — 짧은 모듈 이름(`plan.py`)은 경로가 아니라 지시어이고,
    # 그것을 끊김으로 세면 검사가 소음이 되어 진짜 낡은 경로를 가린다.
    TOPS = (
        "docs/",
        "app/",
        "tests/",
        "scripts/",
        "db/",
        "backlog/",
        "handoff/",
        "assets/",
        "infra/",
    )
    paths = set(re.findall(r"<code>([a-zA-Z0-9_./-]+\.(?:md|html|py|sh|sql))</code>", text))
    paths |= set(re.findall(r"`([a-zA-Z0-9_./-]+\.(?:md|html|py|sh|sql))`", text))
    paths = {name for name in paths if name.startswith(TOPS)}
    for name in sorted(paths):
        if (ROOT / name).exists() or (base / name).exists():
            ok += 1
        else:
            bad += 1
            print(f"  없는 경로 표기: {doc} -> {name}")
print(f"확인 {ok + bad}건 · 실재 {ok} · 끊김 {bad}")
sys.exit(1 if bad else 0)
