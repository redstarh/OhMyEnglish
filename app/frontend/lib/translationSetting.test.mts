// KO 설정 시험 (`TASK-331` codex 리뷰 ①) — 저장소가 막혀도 홈이 깨지지 않고 값이 바뀜.
// 실행: node --test lib/translationSetting.test.mts
import assert from "node:assert/strict";
import test from "node:test";

import { readSetting, writeSetting } from "./translationSetting.ts";

const throwing = {
  getItem(): string | null {
    throw new Error("SecurityError");
  },
  setItem(): void {
    throw new Error("QuotaExceededError");
  },
};

test("저장소를 읽다 예외가 나도 끔으로 읽힘", () => {
  assert.equal(readSetting(throwing), false);
});

test("저장이 실패해도 값은 바뀌고 알림이 감", () => {
  let notified = 0;
  writeSetting(throwing, true, () => {
    notified += 1;
  });
  assert.equal(readSetting(throwing), true, "메모리 값이 남음");
  assert.equal(notified, 1);
  writeSetting(throwing, false, () => {
    notified += 1;
  });
  assert.equal(readSetting(throwing), false);
});

test("저장소가 되면 그 값을 읽음", () => {
  const store = new Map<string, string>();
  const ok = { getItem: (k: string) => store.get(k) ?? null, setItem: (k: string, v: string) => void store.set(k, v) };
  writeSetting(ok, true, () => {});
  assert.equal(readSetting(ok), true);
});
