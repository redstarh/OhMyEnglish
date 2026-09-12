---
id: TASK-66
title: '구현: 합성한 쉐도잉 클립 오디오를 담을 자리를 만든다 — 지금 스키마에 자리가 0이다'
status: In Progress
assignee: []
created_date: '2026-09-09 14:16'
updated_date: '2026-09-12 23:39'
labels: []
dependencies:
  - TASK-63
ordinal: 69000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
결정 47 이 「쓴다 · 미리 만들어 저장」으로 확정했다. 그런데 011_shadowing_items.sql 을 직접 읽어 확인한 사실 둘: ① shadowing_items 의 컬럼은 id·source_title·source_url·transcript·clip_start_sec·clip_end_sec·level·created_at 뿐이고 오디오를 담을 자리가 없다. source_url 주석이 「외부 영상은 링크만 보관한다」라 그 자리는 출처 링크이고 로컬 오디오 경로를 넣는 것은 의미 오버로드다 ② utterances.audio_url 은 CHECK utterances_audio_only_for_shadowing 이 speaker='user' 인 학습자 낭독만 받는다 — 합성음은 원리적으로 못 들어간다. 근거와 생성 절차는 docs/design/2026-09-09-shadowing-synthetic-clip-review.md 가 소유한다(§4·§7). ⛔ 결정 47 이 R10-7 예외를 「합성한 쉐도잉 클립 오디오」 하나로 좁혀 열었다 — 그 범위를 넓히지 않는다. ⚠️ 설계서 §9 의 data-first 규율을 지킨다: 소비자(재생 경로)와 같은 커밋에서 나간다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 오디오를 어디에 두고 무엇으로 가리키는지 정한다 — 컬럼 추가인지 별도 표인지, 파일이 리포 안인지 밖인지. 발명하지 않고 기존 학습자 낭독 저장 방식과 대조해 근거를 든다
- [ ] #2 R10-7 예외 범위를 스키마에 새긴다 — 011 의 CHECK 주석이 「다른 오디오가 조용히 쌓이는 길을 막는다」고 한 의도를 유지한다. 합성 클립 외의 오디오가 새 자리로 들어오지 못하게 한다
- [x] #3 시드 1건의 clip_end_sec 을 실측값으로 고친다 — 지금 30.00 을 선언했으나 그 전사문의 합성음은 16.64초다(2026-09-09 실측). 합성음에서는 시간 창이 곧 오디오 전체다
- [ ] #4 재생 경로(소비자)와 같은 커밋으로 낸다 — 소비자 0곳이면 진행하지 않는다(설계서 §9)
- [ ] #5 클립 생성 절차 문서의 마지막 줄을 채운다 — 파일을 어디에 두는가가 정해지면 review 문서 §7.4 가 닫힌다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
착수 전 조사 2026-09-13 (세션 ohmyenglish-f4) — ⛔ 착수하지 않았음. 다음 세션이 다시 조사하지 않게 확인한 사실만 남김.

선행이 풀렸음: TASK-63 이 Done 임.

⛔ AC#1 의 판단을 가르는 사실 셋을 직접 확인했음.
1. `assets/audio/` 가 **.gitignore:32 로 무시됨**. 그런데 합성 클립은 사용자 데이터가 아니라 «제품 자산»(미리 만들어 저장 · 결정 47)이므로 그 자리에 두면 리포와 함께 배포되지 않음 ⇒ 「리포 안인가 밖인가」가 배포 방식에 걸리는 진짜 결정임. 지금 추적되는 것은 `assets/.gitkeep` 하나뿐임.
2. `settings.shadowing_audio_root`(기본 `../../assets/audio`)는 **학습자 낭독**의 루트임 — `pending_recording_path` · `purge_expired_recordings` · `sweep_orphan_recording_files` 가 그 수명주기를 가짐. 합성 클립은 만료·정리 대상이 아니므로 같은 루트에 섞으면 그 스윕이 제품 자산을 지울 수 있음.
3. **클립 오디오를 내려주는 엔드포인트가 0곳임.** `api/results.py` 는 `next-plan` · `results` · `recordings/{utterance_id}`(학습자 낭독) 셋뿐임 ⇒ AC#4(소비자와 같은 커밋)를 지키려면 엔드포인트와 프런트 재생을 함께 만들어야 함.

⇒ 범위가 「마이그레이션 + CHECK + 시드 수정 + 엔드포인트 + 프런트 재생 + 문서 한 줄」이고 그 안에 배포 방식이 걸린 결정이 하나 있음. ⛔ TASK-62 처럼 brainstorming → writing-plans 를 태우는 것이 맞음(CLAUDE.md 의 절차 규칙 · 신규 기능).

⚠️ AC#3 은 그 주기와 «독립» 임 — 시드 1건의 clip_end_sec 을 30.00 에서 실측 16.64 로 고치는 것이고 마이그레이션이 아니라 시드 상수 수정임(019 가 display_order 를 그렇게 갱신하는 것과 같은 경로). 먼저 떼어 닫을 수 있음.

⛔ AC#3 도 «독립이 아니었음» — 세 값이 부딪힘. 앞 노트에서 「먼저 떼어 닫을 수 있음」이라 적은 것을 정정함.

직접 읽은 세 값:
1. **PRD:101** — 「**30~90초**의 짧은 오디오·영상 클립을 문장 단위로 제공한다」. 30초가 하한임.
2. **시드의 30.00 은 발명값이 아님** — `scripts/migrate.py` 주석이 *"PRD §7 의 하한 30초를 그대로 썼다(요구사항 값이고 내가 고른 숫자가 아니다)"* 로 그 출처를 적어 뒀음.
3. **실측은 16.64초**(그 review 문서 §의 2026-09-09 실측 · Sohee·en · 6문장 37낱말).

⇒ 16.64 로 고치면 시드가 **PRD 하한을 깨는 값**이 됨. 그렇다고 문장을 늘리는 것은 **결정 25**(*"학습 1회가 성립하는 최소"* · 그 주석이 *"분량은 늘리지 않는다"* 로 못박음)와 부딪힘.

⇒ 이것은 제품 판단임(요구 준수 대 앞선 결정). 후보 둘:
① 16.64 로 고치고 **시드가 PRD 하한 미달임을 알려진 격차로 기록** — 값이 정직해지지만 요구를 깸.
② 전사문을 늘려 30초를 넘기고 **새 실측값**으로 고침 — 요구를 지키지만 결정 25 를 뒤집어야 하고 TTS 회차가 한 번 필요함(그 문서 §이 「90초를 채우려면」 계산을 이미 해 뒀음).

⛔ 결정 없이 값을 고치지 않음 — 어느 쪽이든 요구나 결정 하나를 뒤집으므로 사용자 판단 사안임.

AC#3 닫음 2026-09-13 (세션 ohmyenglish-f4 · 사용자 결정 88).

사용자가 후보 넷 중 「실측 16.64 로 고침」을 골랐음. 기각한 셋은 전사문 확장 · PRD 하한 개정 · TASK-66 미룸임. 결정 원문과 기각 근거는 `docs/ops/captain-instruction-register.md` 의 결정 88 이 소유함.

고친 것 넷:
1. `scripts/migrate.py` 의 `SEED_SHADOWING_ITEMS` — `clip_end_sec` 을 `Decimal("30.00")` → `Decimal("16.64")` 로. 그 위 주석이 「PRD 하한을 그대로 썼다」에서 「실측이고 하한 미달은 결정 88 로 기록한다」로 바뀜.
2. `tests/unit/test_shadowing_seed.py` — 하한 단정을 지우지 않고 **id 면제**로 바꿈(`KNOWN_SUB_MIN_CLIP_IDS`). 단정 둘이 양방향으로 물림: 목록에 없는 짧은 클립은 실패 · 목록에 남은 긴 클립도 실패(면제가 영구 통행권이 되는 것을 막음).
3. 설계서 §7.2 에 「닫혔음」 절을 더하고 낡은 줄 번호 참조(`migrate.py:146~147`)를 이름 참조로 바꿈.
4. 결정 대장에 결정 88 을 등재함.

판별력 확인: 면제 목록을 `frozenset()` 으로 비워 `test_only_a_recorded_clip_falls_short_of_the_prd_lower_bound` 가 red(1 failed, 7 passed)가 되는 것을 보고, 되돌려 `diff -q` 로 원본 동일을 확인한 뒤 8 passed 를 다시 읽었음. 변이 적용 여부는 `s2 != s` 단정으로 먼저 확정했음.

게이트(고친 뒤 직접 돌림 · 전부 exit 0): `pytest` 1134 passed(변경 전 1132 · 새 단정 둘) · `ruff check` · `ruff format` 212 files · `ty check`.

⚠️ 남은 것 하나 — **dev DB 행은 아직 `0.00|30.00` 임**(직접 조회로 확인). 시드 상수가 정본이고 upsert 가 `do update` 라 `seed()` 재실행이 동기화하지만 그것은 dev DB 쓰기라 승인 사안으로 사용자에게 올림. ⛔ `scripts/migrate.py` 를 스크립트로 통째 실행하면 미적용 마이그레이션 020·021 까지 적용될 수 있으므로 그 경로로 돌리지 않음.

AC#1·#2·#4·#5 는 그대로 열려 있고 새 설계 주기(brainstorming → writing-plans)가 필요함 — 앞 노트의 사실 셋이 근거임.
<!-- SECTION:NOTES:END -->
