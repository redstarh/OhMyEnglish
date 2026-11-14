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

// ── 결과 화면 날짜 문구 (`TASK-331` codex 리뷰 ②) ──
import { sessionWording } from "./learnerDate.ts";

test("오늘과 같은 날의 세션은 today 문구", () => {
  assert.equal(sessionWording("2026-11-14", "2026-11-14"), "today");
});

test("지난 세션은 날짜 문구", () => {
  assert.equal(sessionWording("2026-11-01", "2026-11-14"), "dated");
});

test("오늘을 모르면(하루 요약 실패) 세션 날짜로 씀 — 날짜 문구는 언제나 참임", () => {
  assert.equal(sessionWording("2026-11-01", null), "dated");
});

test("세션 날짜를 모르면(옛 서버) 옛 today 문구로 돌아감", () => {
  assert.equal(sessionWording(null, "2026-11-14"), "today");
  assert.equal(sessionWording(null, null), "today");
});
