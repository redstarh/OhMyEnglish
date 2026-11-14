"use client";

// 문장 아래 한국어 번역을 보일지 — 카드의 Auto 옆 KO 켜기/끄기가 정하고 기억함(`TASK-328` 사용자 결정).
// ⛔ 문장 칸(`SentencePractice.tsx`)과 홈 카드(`HomeDashboard.tsx`)가 같은 값을 읽음 — 번역 줄을 켜면 문장
//    칸이 커지므로 대기 카드 높이도 그 값을 따라야 함. 그래서 한 곳(이 모듈)이 값을 갖고 바뀌면 둘 다 다시 그림.
// ⚠️ 처음 값은 끔 — 번역은 필요할 때만 보는 보조이고, 따라 말하기는 영어 문장을 보고 하는 연습임(내가 정한 값).

import { useCallback, useSyncExternalStore } from "react";

const STORAGE_KEY = "omy.course.translation";
const CHANGE_EVENT = "omy-translation-change";

type SettingStorage = Pick<Storage, "getItem" | "setItem">;

// ⛔ 저장소가 막혀도(사생활 모드 · `SecurityError` · `QuotaExceededError`) 홈이 깨지지 않음(`TASK-331` codex
//    리뷰 ①) — 마지막으로 고른 값을 메모리에 두고, 저장이 실패해도 그 값으로 바꾸고 알림.
let remembered: boolean | null = null;

/** 저장된 값. 읽다 예외가 나면 메모리 값(없으면 끔). */
export function readSetting(storage: SettingStorage): boolean {
  try {
    const saved = storage.getItem(STORAGE_KEY);
    if (saved !== null) return saved === "on";
  } catch {
    // 저장소를 못 읽음 — 아래 메모리 값을 씀.
  }
  return remembered ?? false;
}

/** 값을 바꾸고 알림. 저장이 실패해도 메모리 값은 바뀌고 알림은 감. */
export function writeSetting(storage: SettingStorage, next: boolean, notify: () => void): void {
  remembered = next;
  try {
    storage.setItem(STORAGE_KEY, next ? "on" : "off");
  } catch {
    // 저장하지 못함 — 이 탭에서는 메모리 값으로 유지됨.
  }
  notify();
}

// `window.localStorage` 를 꺼내는 것만으로 예외가 나는 브라우저가 있음 — 그때는 늘 실패하는 저장소를 씀.
const unavailable: SettingStorage = {
  getItem: () => {
    throw new Error("storage unavailable");
  },
  setItem: () => {
    throw new Error("storage unavailable");
  },
};

function storage(): SettingStorage {
  try {
    return window.localStorage;
  } catch {
    return unavailable;
  }
}

function read(): boolean {
  return readSetting(storage());
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
    writeSetting(storage(), next, () => window.dispatchEvent(new Event(CHANGE_EVENT)));
  }, []);
  return [show, setShow];
}
