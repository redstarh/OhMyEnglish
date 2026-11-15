// 서버 주소 고르기 시험 (`TASK-325` 아이폰) — localhost 가 아닌 주소로 열면 같은 출처를 씀.
// 실행: node --test lib/apiBase.test.mts
import assert from "node:assert/strict";
import test from "node:test";

import { resolveApiBase } from "./config.ts";

test("맥에서 localhost 로 열면 환경 변수의 서버 주소를 씀", () => {
  assert.equal(resolveApiBase("http://localhost:8002", { hostname: "localhost", origin: "http://localhost:3000" }), "http://localhost:8002");
  assert.equal(resolveApiBase("http://localhost:8002", { hostname: "127.0.0.1", origin: "http://127.0.0.1:3000" }), "http://localhost:8002");
});

test("tailnet 주소(HTTPS)로 열면 그 출처를 씀 — tailscale serve 가 /api · /ws 를 서버로 넘김", () => {
  const origin = "https://redstarui-macbookair.tailf9cacf.ts.net";
  assert.equal(resolveApiBase("http://localhost:8002", { hostname: "redstarui-macbookair.tailf9cacf.ts.net", origin }), origin);
});

test("서버 렌더(창 없음)는 환경 변수 · 없으면 기본값", () => {
  assert.equal(resolveApiBase("http://localhost:8002", null), "http://localhost:8002");
  assert.equal(resolveApiBase(undefined, null), "http://localhost:8000");
});
