"use client";

// 홈에 숨긴 추가 학습 입구(More practice · Practice a pattern)를 주소로 다시 보이는 스위치(`TASK-341`).
// ⛔ 기본은 숨김 — 「일단 매일매일 연습하는 것만 있으면 될 것 같아」(`TASK-338` 사용자 결정 2026-11-15).
// ⛔ `?extras=1` 일 때만 보임 — 수동 하네스 드라이버(`tests/harness/c1·c2·c5·p_app_path·p_readback_leg`)가
//    버튼을 눌러 세션에 들어가야 하기 때문임. 질의로 바로 진입하면 마이크 대체를 심을 틈이 없음(`H-CC`).

import { useSyncExternalStore } from "react";

/** 주소 질의가 숨긴 입구를 켜는가. 값은 정확히 `1` 일 때만 켬. */
export function extrasFromQuery(search: string): boolean {
  return new URLSearchParams(search).get("extras") === "1";
}

// 주소 질의는 이 화면에서 바뀌지 않으므로 구독할 것이 없음.
const noSubscribe = () => () => {};

/** `?extras=1` 로 연 홈인가. 서버 렌더에서는 숨김 — 하이드레이션 뒤에 켜짐. */
export function useExtrasFromQuery(): boolean {
  return useSyncExternalStore(
    noSubscribe,
    () => extrasFromQuery(window.location.search),
    () => false,
  );
}
