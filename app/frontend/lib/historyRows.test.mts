// 기록 줄 묶기와 날짜 줄 사실 시험 (`TASK-333` N5 · N8). 실행: node --test lib/historyRows.test.mts
import assert from "node:assert/strict";
import test from "node:test";

import { dayFact, groupHistoryRows } from "./historyRows.ts";
import { gapLabel } from "./learnerDate.ts";

const day = (iso: string, learned: boolean, extra: object = {}) =>
  ({ day: iso, learned, completed_scenarios: learned ? 1 : 0, analyzed: false, occurrence_count: 0, pattern_count: 0, ...extra }) as never;

test("이어진 빈 날은 한 줄로 접히고 공부한 날은 그대로 남음", () => {
  const rows = groupHistoryRows([
    day("2026-11-14", true),
    day("2026-11-13", false),
    day("2026-11-12", false),
    day("2026-11-02", false),
    day("2026-11-01", true),
    day("2026-10-31", false),
  ]);
  assert.deepEqual(
    rows.map((row) => (row.kind === "day" ? row.row.day : `${row.from}..${row.to}`)),
    ["2026-11-14", "2026-11-02..2026-11-13", "2026-11-01", "2026-10-31..2026-10-31"],
  );
});

test("빈 날 줄의 문구", () => {
  assert.equal(gapLabel("2026-11-02", "2026-11-13"), "No study · Nov 2 – Nov 13");
  assert.equal(gapLabel("2026-10-31", "2026-10-31"), "No study · Oct 31");
});

test("말한 세션이 없는 날은 Nothing said · 말했는데 요약이 없으면 Not analyzed yet", () => {
  assert.equal(dayFact(day("2026-11-14", true, { spoken: false })), "Nothing said");
  assert.equal(dayFact(day("2026-11-14", true, { spoken: true })), "Not analyzed yet");
  // 옛 서버(키 없음)는 옛 문구로 감.
  assert.equal(dayFact(day("2026-11-14", true)), "Not analyzed yet");
  assert.equal(dayFact(day("2026-11-14", true, { spoken: true, analyzed: true })), "No mistakes");
  assert.equal(dayFact(day("2026-11-14", false)), "");
});

// ── codex 리뷰 ① (`TASK-334`) ──
test("말한 세션이 없는 날은 요약이 있어도 No mistakes 가 아니라 Nothing said", () => {
  // 실패·진행 중 세션이 만든 요약이 있어도 마친 세션에 학습 발화가 없으면 「오류 0건」이라 말하지 않음.
  assert.equal(dayFact(day("2026-11-14", true, { spoken: false, analyzed: true, occurrence_count: 0 })), "Nothing said");
});

test("말한 세션이 없어도 요약에 실수가 잡혔으면 그 사실을 보임", () => {
  assert.equal(
    dayFact(day("2026-11-14", true, { spoken: false, analyzed: true, occurrence_count: 2, pattern_count: 1 })),
    "Mistakes 2 · Patterns 1",
  );
});
