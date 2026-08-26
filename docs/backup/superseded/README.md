# 폐기 문서 보관소 (superseded)

여기 있는 문서는 **현행 정본이 아니다.** 그러나 지우지 않는다 — 승인된 설계서들이 이 문서의
특정 줄을 **요구 근거로 인용**하고 있어서, 지우면 그 근거가 사라진다.

## 규약

1. **파일 내용을 수정하지 않는다.** 인용이 `file:line` 형태라 한 줄만 더해도 근거가 어긋난다.
   폐기 사실·대체 문서·인용처는 이 README에만 적는다.
2. 새로 폐기하는 문서는 여기로 `git mv`하고 아래 표에 한 줄 추가한다.
3. 참조하는 쪽의 **경로만** 갱신한다(줄 번호는 그대로 유효하다).

## 보관 목록

### `voice-architecture.md` — 2026-08-27 이관

| 항목 | 내용 |
|---|---|
| 무엇 | 프로젝트 초기에 쓴 일반 음성 설계(STT/TTS/명령 Router/보안) |
| 왜 폐기 | 문서 스스로 `:3`에서 "현재 채택된 구체 아키텍처는 `nova-sonic-claude-architecture.md`를 우선한다"고 선언한다. 게다가 `:87-92`의 Phase 표가 현행과 어긋난다 — 실제로는 Phase 1에서 이미 Nova 양방향·끼어들기가 관통했고(3차수 N5), 문서는 그것을 Phase 2로 적어 두었다 |
| 대체 문서 | 아키텍처: `docs/nova-sonic-claude-architecture.md` · 요구사항: `docs/PRD.md` · 대화 규칙: `docs/agent-system-prompt.md` |
| ⚠️ 대체 문서가 **덮지 못하는** 내용 | `:41`(부분=회색 / 확정=일반 전사문 표시) · `:42-43`(부분 전사문은 표시용, 확정만 `utterances`에 저장) · `:63`(barge-in은 "즉시") · `:65-68`(쉐도잉 속도 0.75x/1.0x·반복·전사문 숨기기). **이 4건은 `nova-sonic-claude-architecture.md`에 없다** — 그래서 인용이 이 파일을 계속 가리킨다 |

**인용처 (경로 갱신 완료)**

| 인용하는 문서 | 인용 줄 | 무엇을 근거로 삼는가 |
|---|---|---|
| `docs/design/2026-08-25-first-slice-acceptance-criteria.md:91` | `:41` | 전사문 색 구분 (U1 수용 기준) |
| `docs/design/2026-08-24-first-vertical-slice-design.md:299` | `:42-43` | 부분 전사문 미저장 (Boundary lens) |
| `docs/design/2026-08-24-first-vertical-slice-design.md:329` | `:63` | barge-in 즉시 — 상한 1초는 설계서의 발명값 |
| `handoff/HANDOFF.md` | (파일 단위) | 설계 정본 목록 |
| `README.md` | (파일 단위) | 문서 색인 |

`docs/ops/2026-08-26-test-harness-report.html:346`도 `voice-architecture.md:41`을 인용하지만
**갱신하지 않았다** — 그 파일은 1차수 시점의 리포트 스냅샷이고, 스냅샷을 사후 편집하면
"그때 무엇을 보고 판정했는지"가 흐려진다.
