// 숨긴 추가 학습 입구를 주소로 다시 보이는 스위치 시험 (`TASK-341`).
// 실행: node --test components/home/homeExtras.test.mts
import assert from "node:assert/strict";
import test from "node:test";

import { extrasFromQuery } from "./homeExtras.ts";

test("?extras=1 이면 숨긴 입구를 보임 — 수동 하네스 드라이버가 버튼으로 세션에 들어가는 길", () => {
  assert.equal(extrasFromQuery("?extras=1"), true);
  assert.equal(extrasFromQuery("?mode=speaking&extras=1"), true);
});

test("그 밖에는 숨김(TASK-338 사용자 결정)", () => {
  assert.equal(extrasFromQuery(""), false);
  assert.equal(extrasFromQuery("?extras=0"), false);
  assert.equal(extrasFromQuery("?extras=true"), false);
  assert.equal(extrasFromQuery("?mode=speaking"), false);
});
