"use client";

// 문장 아래 한국어 번역을 보일지 — 카드의 Auto 옆 KO 켜기/끄기가 정하고 기억함(`TASK-328` 사용자 결정).
// ⛔ 문장 칸(`SentencePractice.tsx`)과 홈 카드(`HomeDashboard.tsx`)가 같은 값을 읽음 — 번역 줄을 켜면 문장
//    칸이 커지므로 대기 카드 높이도 그 값을 따라야 함. 그래서 한 곳(이 모듈)이 값을 갖고 바뀌면 둘 다 다시 그림.
// ⚠️ 처음 값은 끔 — 번역은 필요할 때만 보는 보조이고, 따라 말하기는 영어 문장을 보고 하는 연습임(내가 정한 값).

import { useCallback, useSyncExternalStore } from "react";

const STORAGE_KEY = "omy.course.translation";
const CHANGE_EVENT = "omy-translation-change";

function read(): boolean {
  return window.localStorage.getItem(STORAGE_KEY) === "on";
}

function subscribe(onChange: () => void): () => void {
  window.addEventListener(CHANGE_EVENT, onChange);
  window.addEventListener("storage", onChange);
  return () => {
    window.removeEventListener(CHANGE_EVENT, onChange);
    window.removeEventListener("storage", onChange);
  };
}

/** 번역을 보일지와 그 값을 바꾸는 함수. 서버 렌더에서는 끔. */
export function useShowTranslation(): [boolean, (next: boolean) => void] {
  const show = useSyncExternalStore(subscribe, read, () => false);
  const setShow = useCallback((next: boolean) => {
    window.localStorage.setItem(STORAGE_KEY, next ? "on" : "off");
    window.dispatchEvent(new Event(CHANGE_EVENT));
  }, []);
  return [show, setShow];
}
