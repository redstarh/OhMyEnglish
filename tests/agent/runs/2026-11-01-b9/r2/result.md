# 회차 2026-11-01-b9r — D1 · O1 수정 재검증

- 측정 대상: HEAD `f6fe294` + 미커밋 작업 트리 diff(`evidence/worktree.diff` · sha1 `3f0065fd…`, 회차 끝까지 같음). 두 파일 mtime 04:52:30.
- 스택은 b9 와 같음(stub · 격리 DB · 재기동 없음). Chrome 은 :9335(가짜 장치) · :9336(장치 없음)으로 새로 띄우고 끝에 끔.

| # | 항목 | 판정 | 근거 |
|---|---|---|---|
| 1 | D1 재현 — 쉐도잉 · 발음 실패 → Try again | 통과 | 소켓 `mode=shadowing&source=additional` · `mode=pronunciation&source=additional`. DB `shadowing`(+ `shadowing_item_id`) · `pronunciation`, 둘 다 `additional` (`RETRY-quick-shadowing.json` · `RETRY-practice-pronunciation.json` · `RETRY-db-rows.json`) |
| 2 | 추천 학습 실패 → Try again | 통과 | 소켓 `?source=recommended` · DB `speaking`/`recommended`. 첫 시도 소켓(b9 `SESSION-rec2.json`)과 같음 (`RETRY-start-session.json`) |
| 2+ | 쉐도잉 실패 → Home → 추천 실패 → Try again | 통과 | 앞 진입이 남지 않고 `?source=recommended` 로 엶 (`STALE-quick-shadowing.json`) |
| 3 | `session-failed-home` | 통과 | 실제 권한 거부(:9336) → Try again 이 같은 거부를 받음 → Home → `/` · 덮개 없음 · 칸 5개가 ready/empty (`DENY.json`) |
| 4 | 코스 수동 Next · 자동 | 통과 | Day 5: 503 안내 → Next → 문장 2 안내 `null`. Back 으로도 `null`. 자동은 done(안내) → 1.5초 뒤 문장 2 listen(안내 비어 있음) → repeat 로 b9 와 같음 (`COURSE-r2-day5.json`) |

- 콘솔: 증거 6개 모두 비네트워크 기록 0건.
- dev DB 끝: 18 · 144 · 0 · 0 (`devdb-end.json`). 격리 DB 에 세션 4건이 더해졌고 그대로 둠. 이번에는 Day 를 마치지 않았음.
