// 다시 시작 주소와 코치 세션 제목 시험 (`TASK-333` N3 · N4). 실행: node --test lib/sessionEntry.test.mts
import assert from "node:assert/strict";
import test from "node:test";

import { entryFromQuery, restartHref } from "./config.ts";
import { sessionTitleFor } from "../app/additionalLearning.ts";

test("진입이 없으면(옛 서버) 다시 시작은 홈으로 감", () => {
  assert.equal(restartHref(undefined), "/");
  assert.equal(restartHref(null), "/");
});

test("Free talk(모드 없는 말하기) 다시 시작은 홈 질의로 같은 학습을 엶", () => {
  const href = restartHref({ mode: "speaking", source: "additional", item: null, pattern: null });
  assert.equal(href, "/?mode=speaking&source=additional");
  // ⛔ 홈이 그 질의를 세션 진입으로 읽어야 함 — 읽지 않으면 홈 대기 화면만 보이고 「← Home」과 같아짐.
  assert.deepEqual(entryFromQuery(href.slice(1)), { mode: "speaking", source: "additional" });
});

test("쉐도잉 다시 시작은 같은 클립을 엶 · 다른 모드에는 클립을 싣지 않음", () => {
  assert.equal(
    restartHref({ mode: "shadowing", source: "additional", item: "c1", pattern: null }),
    "/?mode=shadowing&source=additional&item=c1",
  );
  assert.equal(
    restartHref({ mode: "pronunciation", source: "additional", item: "c1", pattern: null }),
    "/?mode=pronunciation&source=additional",
  );
});

test("패턴으로 연 세션은 그 패턴으로 다시 엶", () => {
  assert.equal(
    restartHref({ mode: "speaking", source: "recommended", item: null, pattern: "article_missing" }),
    "/?mode=speaking&source=recommended&pattern=article_missing",
  );
});

test("세션 제목은 누른 버튼 이름이 이김", () => {
  assert.equal(sessionTitleFor({ source: "additional" }, "Weak spots"), "Weak spots");
});

test("이름 없이 연 세션은 진입으로 목록에서 제목을 고름", () => {
  assert.equal(sessionTitleFor({ source: "additional" }), "Free talk");
  assert.equal(sessionTitleFor({ mode: "speaking", source: "additional" }), "Free talk");
  assert.equal(sessionTitleFor({ mode: "shadowing", source: "additional", itemId: "c1" }), "Shadowing");
  assert.equal(sessionTitleFor({ mode: "scenario_intake", source: "additional" }), "5 questions");
  assert.equal(sessionTitleFor({ patternKey: "article_missing" }), "Practice a pattern");
  assert.equal(sessionTitleFor({ source: "recommended" }), "English talk");
});
