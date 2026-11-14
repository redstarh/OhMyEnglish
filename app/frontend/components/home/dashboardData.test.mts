// `dayStatus` 시험 — 홈 Continue your path 와 코스 목록이 같은 Day 를 같은 상태로 보여야 함(`TASK-322` · 회차 b16 D2).
// 실행: node --test components/home/dashboardData.test.mts (Node 24 의 타입 제거로 .ts 를 바로 불러옴)
import assert from "node:assert/strict";
import test from "node:test";

import { dayStatus, learnedInLastWeek } from "./dashboardData.ts";

const day = (progress: object | null) =>
  ({ day: 2, first_unit: 22, last_unit: 41, duration_sec: 3780, youtube_id: "x", progress }) as never;
const atStart = { unit: 22, sentence_index: 0, position_sec: 0, completed_count: 2, last_completed_date: "2026-11-01" };

test("지난 회차에 마치고 시작 위치에 있는 Day 는 이번 회차에 시작하지 않은 것임", () => {
  assert.equal(dayStatus(day(atStart), 3), "new");
});

test("진도 행이 없으면 시작하지 않은 것임", () => {
  assert.equal(dayStatus(day(null), 3), "new");
});

test("시작 위치를 벗어났으면 진행 중임", () => {
  assert.equal(dayStatus(day({ ...atStart, sentence_index: 1 }), 3), "started");
  assert.equal(dayStatus(day({ ...atStart, unit: 23 }), 3), "started");
  assert.equal(dayStatus(day({ ...atStart, position_sec: 5 }), 3), "started");
});

test("이번 회차 완료 수에 닿았으면 끝난 것임", () => {
  assert.equal(dayStatus(day({ ...atStart, completed_count: 3 }), 3), "done");
});

// ── `TASK-335` This week — 연속 학습일·기록 Nothing said 와 같은 기준(학습 발화가 있는 날만) ──
const hDay = (day: string, learned: boolean, spoken?: boolean) =>
  ({ day, learned, completed_scenarios: learned ? 1 : 0, analyzed: false, occurrence_count: 0, pattern_count: 0, ...(spoken === undefined ? {} : { spoken }) }) as never;

test("마쳤어도 학습 발화가 없는 날(spoken 거짓)은 This week 에 세지 않음", () => {
  const history = {
    streak: { current: 1, longest: 1, today_done: true },
    days: [hDay("2026-11-15", true, false), hDay("2026-11-14", true, true), hDay("2026-11-13", false, false)],
  } as never;
  assert.deepEqual(learnedInLastWeek(history), { learned: 1, window: 3 });
});

test("spoken 이 없는 옛 서버에서는 마친 날을 그대로 셈", () => {
  const history = {
    streak: { current: 2, longest: 2, today_done: true },
    days: [hDay("2026-11-15", true), hDay("2026-11-14", true), hDay("2026-11-13", false)],
  } as never;
  assert.deepEqual(learnedInLastWeek(history), { learned: 2, window: 3 });
});
