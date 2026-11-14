// 학습자 날짜 문구 시험 (`TASK-329`). 실행: node --test lib/learnerDate.test.mts
import assert from "node:assert/strict";
import test from "node:test";

import { addDays, dayLabel, weekName, weekRangeLabel, weekRelation } from "./learnerDate.ts";

test("날짜는 달 이름과 날로 보임", () => {
  assert.equal(dayLabel("2026-11-01"), "Nov 1");
});

test("주 범위는 월요일부터 일요일까지이고 달을 넘겨도 맞음", () => {
  assert.equal(weekRangeLabel("2026-11-02"), "Nov 2 – Nov 8");
  assert.equal(weekRangeLabel("2026-10-26"), "Oct 26 – Nov 1");
});

test("해를 넘기는 날짜 더하기", () => {
  assert.equal(addDays("2026-12-28", 6), "2027-01-03");
  assert.equal(addDays("2026-11-09", -7), "2026-11-02");
});

test("리포트의 주를 이번 주 · 지난주 · 그 밖으로 가름", () => {
  assert.equal(weekRelation("2026-11-09", "2026-11-09"), "this");
  assert.equal(weekRelation("2026-11-02", "2026-11-09"), "last");
  assert.equal(weekRelation("2026-10-26", "2026-11-09"), "other");
  assert.equal(weekRelation("2026-11-09", undefined), "other", "기준이 없으면 「This week」라고 하지 않음");
});

test("This week 는 이번 주일 때만 씀", () => {
  assert.equal(weekName("this"), "This week");
  assert.equal(weekName("last"), "Last week");
  assert.equal(weekName("other"), null);
});
