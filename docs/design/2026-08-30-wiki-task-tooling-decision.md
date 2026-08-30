# 결정 — 위키 · Task/PR 도구 (2026-08-30)

> **상태: 확정.** 근거 조사: `docs/research/2026-08-30-wiki-task-tooling.html` (커밋 `3badf37`).
> 이 문서는 **결정과 근거**만 담는다. 후보별 판정·실측 수치는 보고서가 정본이다.
> 재논의 방지가 목적이다 — 아래 "기각한 대안"을 다시 검토하기 전에 "재검토 트리거"를 먼저 확인할 것.

---

## 결정 3건

| # | 결정 | 근거 (한 줄) |
|--:|---|---|
| 1 | **Gitea 하나를 도입한다** (네이티브, brew) | 이슈+PR 리뷰+칸반을 단일 프로세스로 덮는다. 유휴 **165MB 실측**. 지금 리포는 remote가 없어 PR 개념 자체가 없는데, 로컬 forge를 remote로 붙이면 한 번에 해결된다 |
| 2 | **`TASKS.md`를 상태의 정본으로 유지한다** | 세션 인계 지표가 `TASKS.md:<줄번호>`로 위치를 지목한다. 정본을 옮기면 그 참조 체계를 재설계해야 하고, 이것이 이 선택지들 중 되돌리기가 가장 비싸다. Gitea 이슈는 **버그/PR 트래킹에만** 쓴다 |
| 3 | **위키 도구를 세우지 않는다** | Gitea 리포 브라우저가 `docs/**.md`를 그대로 렌더링한다. 현재 필요한 것은 "읽기 전용 문서 뷰"이고 이것으로 충족된다. 추가 상주 0 |

**총비용: 상주 프로세스 1개 · 유휴 ~165MB · 외부 DB 0 · 컨테이너 0.**

## 왜 이 조합인가

되돌리기 어려운 변경을 **하나도 하지 않는** 조합이다. Gitea는 지우면 끝이고(리포는 원래 것이 정본), `TASKS.md`는 건드리지 않았고, 위키는 세우지 않았다. 반대로 정본 이동(2번)과 위키 도구 채택(3번)은 나중에도 얹을 수 있다.

판정을 지배한 축은 **"컨테이너냐 네이티브냐"**였다. 이 맥의 podman machine 게스트가 컨테이너 0개 상태에서 이미 ~450MB를 커밋한다(`free -m` 실측 454/3890MB) — 앱이 100MB든 상관없이 VM이 예산을 먼저 먹는다. Gitea는 공식 darwin-arm64 바이너리와 Homebrew 병이 있어 이 비용이 0이다.

## 기각한 대안 — 다시 꺼내기 전에 읽을 것

| 대안 | 기각 사유 | 근거 |
|---|---|---|
| **Gitea Wiki로 `docs/` 정본** | **구조적으로 불가능.** 위키는 별도 `<repo>.wiki` git 리포가 정본이고, 메인 리포 폴더를 위키 소스로 지정하는 설정이 없다 | `models/repo/wiki.go:74` (`repo.Name+".wiki"`) · `models/repo/repo.go:77` (`*.wiki` 예약) · `repo.go:654` (`IsWikiRepo`는 `.wiki` 접미사 판정) · 기능 요청 `go-gitea/gitea#23640 "Publish code as wiki"`가 2023-03-22 생성 후 **여전히 open** |
| **Otter Wiki 즉시 채택** | 기각이 아니라 **보류**. 위키 정본이 리포 `docs/`여야 한다면 +160MB(네이티브)는 협상 불가인 확정 비용이다 — 지금은 그 값을 낼 이유가 없다 | 보고서 A절 |
| **Backlog.md로 `TASKS.md` 이전** | 기각이 아니라 **보류**. 도구 자체는 제약을 만족함을 확인했다(아래) — 막는 것은 도구가 아니라 인계 규약이다 | 결정 2번 |
| **Forgejo** | darwin 릴리스 자산이 없다(리눅스 전용). brew 또는 podman VM ~450MB가 필요 | 보고서 B절 |
| **Wiki.js** | 공식 문서 축자: *"A Git repository must be dedicated to Wiki.js. It is not possible to use only a subfolder"* → 이 리포 `docs/` 지정이 공식 불가 | 보고서 A절 |
| **Outline** | 라이선스 본문이 스스로 *"is not an Open Source license"*(BSL 1.1) → 요건 탈락 | 보고서 A절 |
| **LeafWiki** | 외부에서 넣은 md에 `leafwiki_id` frontmatter를 **디스크에 되쓰기**하고 opt-out이 없다 → git diff 오염 | README 자기 인정 |
| **Plane / GitLab CE** | 리소스 과잉. Plane은 compose 서비스 13개 + SQLite 축소가 구조적 불가(`ArrayField`/`ArrayAgg`는 PostgreSQL 전용), GitLab은 공식 하한이 *"at least 8 GB of memory"* | 보고서 B절 |

### Backlog.md — 검증됐고 보류된 것 (2026-08-30 실측)

나중에 결정 2번을 뒤집을 때 재조사하지 않도록 확인 결과를 남긴다. 실제 리포의 태스크 파일(`backlog/tasks/back-200 - ....md`)을 직접 열어 확인했다.

- **정본**: `backlog/` 폴더 안 평문 md, 태스크 1개 = 파일 1개. 공식 문구 *"Local-first — no server, no account, no telemetry; tasks are plain files in your repo."*
- **상주 0 확인**: CLI 전용. 웹 UI는 `backlog browser`로 온디맨드, `127.0.0.1` 바인딩, 프로세스 종료 시 사라진다
- **설치**: `brew install backlog-md` (npm/bun/nix도 있음)
- **frontmatter를 도구가 쓴다** — `id`/`status`/`labels`/`dependencies`/`priority`/`updated_date`. LeafWiki 탈락 사유와는 성질이 다르다(**남이 쓴 md 오염이 아니라 도구가 만든 자기 포맷**). 단 `updated_date`가 변경마다 갱신되므로 **손댈 때마다 diff에 한 줄 노이즈**가 붙는다
- **`dependencies` 필드가 있다** → "착수 전 필수 조건" 추적에 그대로 맞는다
- **PR은 못 덮는다** — Plan/Task/Status만. 요구사항 B의 4개 중 3개다

## 확정된 첫 걸음

1. `brew install gitea` → SQLite로 기동 → `git remote add local <로컬 forge>` 후 push. 이슈·PR·칸반이 한 번에 생긴다.
2. 설치 위저드 없이 HTTP 200이 뜨는 **최소 `app.ini`** 구조는 실측으로 확인됐다. 키는 아래이고, **비밀값 3개는 반드시 새로 생성한다**(조사 때 쓴 값을 재사용하지 말 것 — `gitea generate secret SECRET_KEY` / `INTERNAL_TOKEN` / `JWT_SECRET`).

```ini
RUN_MODE = prod
WORK_PATH = <작업 경로>
[server]
HTTP_ADDR = 127.0.0.1        ; 외부 노출 금지
HTTP_PORT = <포트>
ROOT_URL = http://127.0.0.1:<포트>/
DISABLE_SSH = true
OFFLINE_MODE = true
LFS_START_SERVER = false
[database]
DB_TYPE = sqlite3            ; 외부 DB 0
PATH = <경로>/data/gitea.db
[repository]
ROOT = <경로>/data/repos
[security]
INSTALL_LOCK = true          ; 설치 위저드 건너뛰기
SECRET_KEY = <생성>
INTERNAL_TOKEN = <생성>
[service]
DISABLE_REGISTRATION = true
[log]
LEVEL = warn
[indexer]
ISSUE_INDEXER_TYPE = bleve   ; 이슈가 쌓이면 메모리가 165MB 위로 오른다
[oauth2]
JWT_SECRET = <생성>
```

3. `TASKS.md`는 **그대로 둔다.** 이슈로 이중 등록하지 않는다 — 결정 2번이 정본 이동을 보류했으므로 병행 운영도 하지 않는다.

## 재검토 트리거

이 결정을 다시 열 조건을 미리 못 박는다. 조건 없이 재논의하지 않는다.

| 결정 | 뒤집을 조건 |
|---|---|
| 3번 (위키 없음) | 위키링크·백링크·전문검색 기반 지식 그래프가 **실제 작업을 막을 때**. "있으면 좋겠다"는 트리거가 아니다 |
| 2번 (`TASKS.md` 정본) | 인계 지표를 줄 번호가 아닌 방식으로 재설계할 의사가 생겼을 때. 그때 Backlog.md는 위 검증 결과를 재사용한다 |
| 1번 (Gitea) | 유휴 메모리가 실사용에서 예산(≤512MB)을 위협할 때. bleve 이슈 인덱서가 주된 증가 요인이다 |

## 이 결정이 남긴 미확인 — 전부 조건부

| 미확인 | 언제 문제가 되나 |
|---|---|
| Otter Wiki가 백업 디렉터리(`docs/backup/**`)를 위키 노출에서 제외하는 공식 수단 | 결정 3번을 뒤집을 때만. 수단이 없으면 별도 clone이 필수가 되고 "리포 md가 제자리에서 정본"이라는 채택 이유가 약해진다 |
| SilverBullet 유휴 RSS · 대소문자 구분 없는 기본 APFS에서의 실제 실패 양상 | 결정 3번을 뒤집으면서 Otter Wiki를 **안** 고를 때만 |
| `TASKS.md` 308줄의 태스크 분해 규모 · 인계 규약 재작성 분량 | 결정 2번을 뒤집을 때만 |

**미검증 후보를 추가 조사하지 않기로 한 이유**: DokuWiki·Gollum·TiddlyWiki·Trilium·MkDocs·mdBook·Quartz·Obsidian·Logseq·Joplin·Vikunja·Kanboard·Wekan·Leantime·Taskwarrior·dstask·radicle·jj는 3표 검증에 오르지 못했으나, 1순위 후보가 제약(상주 최소·정본 평문 md·오픈소스)을 이미 전부 만족했다. 추가 조사의 기대값보다 결정을 미루는 비용이 크다고 판단했다.

## 시효

Gitea v1.27.3 · Otter Wiki v2.24.0 · SilverBullet push가 모두 2026-08-29, Forgejo v16.0.3이 2026-08-20 — 조사 시점 열흘 내다. **버전·메모리 수치는 수 주 안에 낡는다.** 결정의 구조(네이티브 우선·정본 유지)는 버전과 무관하지만, 165MB 같은 수치를 재인용할 때는 재측정할 것.

---

_2026-08-30 확정. 조사는 3-14 세션 deep-research(에이전트 104개 · 소스 22개 · 주장 110건 → 25건 3표 적대적 검증 → 19건 확정/6건 기각), Gitea 위키 저장 구조와 Backlog.md 검증은 후속 세션에서 소스·실파일로 직접 확인._
