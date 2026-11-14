// `dayStatus` 시험 — 홈 Continue your path 와 코스 목록이 같은 Day 를 같은 상태로 보여야 함(`TASK-322` · 회차 b16 D2).
// 실행: node --test components/home/dashboardData.test.mts (Node 24 의 타입 제거로 .ts 를 바로 불러옴)
import assert from "node:assert/strict";
import test from "node:test";

import { dayStatus } from "./dashboardData.ts";

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
