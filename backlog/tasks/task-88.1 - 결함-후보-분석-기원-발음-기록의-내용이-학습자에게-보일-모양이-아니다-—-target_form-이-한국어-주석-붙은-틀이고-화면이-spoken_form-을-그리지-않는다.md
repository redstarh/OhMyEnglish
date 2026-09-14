---
id: TASK-88.1
title: >-
  결함 후보: 분석 기원 발음 기록의 내용이 학습자에게 보일 모양이 아니다 — target_form 이 한국어 주석 붙은 틀이고 화면이
  spoken_form 을 그리지 않는다
status: Done
assignee: []
created_date: '2026-09-14 16:35'
updated_date: '2026-09-14 17:17'
labels: []
dependencies: []
parent_task_id: TASK-88
ordinal: 172000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-88 AC#4 회차(2026-09-15)가 관측했다. 정본은 tests/harness/runs/2026-09-15-task88-p2m-end-to-end/README.md §2 다. 실린 값: target_form = 'I finished the + 업무 산출물 명사 (report / presentation / draft)' · spoken_form = 'the la porte en chaille de lesseps'. ⇒ target_form 이 문장이 아니라 빈칸 채우기 틀이고 한국어 주석이 붙었다. 그리고 결과 화면은 signal_source 가 nova_tool 이 아닌 행을 「관찰된 신호」 갈래로 렌더하며 그 갈래는 spoken_form 을 그리지 않는다 — 학습자가 자기 발화를 못 보고 틀만 본다. ⚠️ 이 판정은 코드를 읽어 얻은 것이고 화면으로 관측하지 않았다(그 회차는 분석 경로만 세웠다). ⛔ TASK-97 과 다른 경로다 — 그쪽은 Nova tool 이 만드는 내용이고 이쪽은 분석기가 만든다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 화면으로 재현한다 — transcript_analysis 행이 결과 화면에서 실제로 어떻게 보이는지 브라우저 레그로 관측한다
- [x] #2 분석 프롬프트가 그 필드에 무엇을 요구하는지 읽고 틀이 나오는 이유를 특정한다 — 문장을 요구하는데 틀이 오는지, 애초에 틀을 허용하는지 가른다
- [x] #3 화면 갈래를 셋으로 가를지 정한다 — 지금 둘(nova_tool 대 그 밖)이라 새 신호가 korean_transcript 와 같은 취급을 받는다. ⛔ 학습자에게 보이는 문구가 바뀌면 사용자 승인 대상이다
- [x] #4 정한 방향을 구현하고 반대 방향 두 단정으로 지킨다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
구현·검증 2026-09-15 (세션 ohmyenglish-65) — 정본은 tests/harness/runs/2026-09-15-task88-1-analysis-row-screen/README.md 임. 실물 모델 사용 0.

AC#1: 화면으로 재현했음 — transcript_analysis 행이 보조 신호와 같은 「관찰된 신호」 갈래로 렌더되고 내 발화도 판정도 안 나왔음(스크린샷 직접 확인).
AC#2: 원인 특정 — 분석 프롬프트(_TARGET_FORM_RULES)가 target_form 을 «일반형»으로 요구하고 자리표시자·한국어를 좋은 예로 든다. 즉 모델은 지시를 지켰고 어긋난 것은 라우팅이었음(같은 이름 두 필드의 계약이 다름).
AC#3: ⚠️ 사용자가 위임했음(자러 가며 권고대로 진행하라 함) — 후보 ③(라우팅 + 화면 갈래 + 라벨 교정문)을 골랐고 그 구분을 결정 99 에 「위임」으로 명시했음.
AC#4: 구현·단정 완료. 기존 테스트가 이 축을 가르지 못했음(픽스처의 target_form 과 correction 이 같은 값) → 가르는 픽스처로 실패를 먼저 보고 고쳤음. tsc 가 프론트 signal_source 값역이 024 이후 낡은 것을 잡아 함께 채웠음. 화면에 옛 행과 새 행을 함께 두고 대조했음.

게이트 넷 다 exit 0(pytest 1200 passed) · 프론트 tsc·eslint 출력 0줄 · 검증 전용 DB 둘 drop · dev DB 불변.
<!-- SECTION:NOTES:END -->
