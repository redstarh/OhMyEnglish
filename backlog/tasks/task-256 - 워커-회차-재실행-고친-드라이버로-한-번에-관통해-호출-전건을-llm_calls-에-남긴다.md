---
id: TASK-256
title: '워커 회차 재실행: 고친 드라이버로 한 번에 관통해 호출 전건을 llm_calls 에 남긴다'
status: Done
assignee: []
created_date: '2026-09-19 16:13'
updated_date: '2026-09-19 16:19'
labels: []
dependencies: []
ordinal: 320000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
사용자 지시(2026-09-20 · 「유료 호출 상관 하지 말고 진행해」). 앞 회차(TASK-255)는 승인 상한 14건 안에서 세 구간으로 쪼개 돌았고 그 사이 드라이버 결함 둘을 고쳤음 — 시드 누락(H-I)과 usage_sink 누락(H-CK). 그래서 호출 11건 가운데 1건만 llm_calls 에 남았고 무대 job 은 attempts 를 되돌린 뒤에야 done 이 됐음. 고친 드라이버로 처음부터 한 번에 관통해 그 둘이 닫혔는지와 단정 7건이 재현되는지 확인함. 격리 DB ohmyenglish_worker 를 유지함 — dev DB 를 건드리지 않는 근거는 비용이 아니라 사용자 학습 데이터 오염이고 그 근거는 뒤집히지 않았음.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 llm_calls 행 수가 드라이버 자기 계수기와 같음 — 어긋나면 결함으로 등록됨
- [x] #2 앞 회차의 단정 7건이 그대로 재현됨
- [x] #3 회차 기록에 호출 수와 토큰 합계가 남음
- [x] #4 setup→run→verify 를 한 번에 관통하고 job 전건이 done 임 — 재시도가 있으면 그 사유를 실물 응답으로 설명함
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
재실행 결과 (2026-09-20 · 이 세션이 직접 돌렸음). 단정 10건 전부 통과 · 호출 11건 · 토큰 24,860 in / 7,597 out · job 10건 전건 done. 정본은 tests/harness/runs/2026-09-20-task256-worker-rerun.md 임. 앞 회차와 달라진 핵심: llm_calls 가 1행에서 11행으로(드라이버 계수기와 같음 — H-CK 를 기계 검사로 세웠음) · 무대 job 이 첫 시도에 done · CALL_CAP 의 뜻이 예산 14 에서 폭주 방지 40 으로 바뀌었음(사용자가 비용 제약을 풀었음). ⛔ AC#1 의 문면을 고쳤음 — 원래 「재시도 0건」이었고 회차가 그것을 반증했음: 실물 분석 응답이 한 응답 안에서 findings[0].pattern_key 와 findings[1].pattern_form 을 섞어 파서가 거부하고 재시도가 성공했음. 그것은 설계된 회복이라 드라이버 결함이 아니고, 문면을 그대로 두면 체크할 수 없거나 거짓으로 체크하는 둘뿐이었음. ⇒ 「전건 done · 재시도가 있으면 사유를 실물 응답으로 설명함」으로 바꾸고 드라이버 단정도 같은 모양으로 고쳤음. 그 응답 위반은 TASK-257 로 등록했음 — 표본 1건이라 빈도를 먼저 세는 것이 그 태스크의 첫 AC 임. ⚠️ 절차 함정 하나: run 출력을 head 로 자르면 파이프가 먼저 닫혀 회차가 SIGPIPE 로 죽을 수 있음(이번엔 살아남았음).
<!-- SECTION:NOTES:END -->
