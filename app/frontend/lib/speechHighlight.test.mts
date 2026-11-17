// 읽어 주는 낱말 색칠 시험(`TASK-348` · 실시간 표시 설계서 §12).
// 실행: node --test lib/speechHighlight.test.mts
// ⚠️ 낱말 경계 신호(`onboundary`)는 브라우저마다 다르게 오거나 오지 않음 — 그래서 경계 → 낱말 번호 변환과
//    신호가 없을 때의 시간 비례 일정을 순수 함수로 두고 여기서 잼.
import assert from "node:assert/strict";
import test from "node:test";

import { wordCountAt, wordSchedule } from "./speechHighlight.ts";

test("경계 글자 위치는 그 위치에서 시작하는 낱말까지 읽은 수로 바뀜", () => {
  const text = "We used to deploy by hand.";
  assert.equal(wordCountAt(text, 0), 1); // "We" 를 읽기 시작함
  assert.equal(wordCountAt(text, 3), 2); // "used"
  assert.equal(wordCountAt(text, 18), 5); // "by"
  assert.equal(wordCountAt(text, 21), 6); // "hand."
});

test("경계 위치가 낱말 가운데·공백이어도 그 낱말까지로 셈 · 범위 밖은 끝으로 맞춤", () => {
  const text = "We used to deploy by hand.";
  assert.equal(wordCountAt(text, 5), 2);
  assert.equal(wordCountAt(text, 2), 1); // 공백은 앞 낱말까지
  assert.equal(wordCountAt(text, 999), 6);
  assert.equal(wordCountAt(text, -3), 0);
});

test("신호가 없을 때의 일정은 첫 낱말이 0 ms 에 켜지고 글자 수에 비례해 늘어남", () => {
  const plan = wordSchedule("We used to deploy by hand.", 2600);
  assert.equal(plan.length, 6);
  assert.equal(plan[0], 0);
  for (let i = 1; i < plan.length; i += 1) assert.ok(plan[i] > plan[i - 1], `증가해야 함: ${plan.join(",")}`);
  assert.ok(plan.at(-1)! < 2600, "마지막 낱말도 읽는 시간 안에서 켜짐");
  // 긴 낱말 「deploy」 앞뒤 간격이 짧은 낱말 「to」 간격보다 큼.
  assert.ok(plan[4] - plan[3] > plan[3] - plan[2]);
});

test("빈 문장은 빈 일정", () => {
  assert.deepEqual(wordSchedule("   ", 1000), []);
  assert.equal(wordCountAt("", 0), 0);
});
