/**
 * 읽어 주는 낱말 색칠의 순수 계산(`TASK-348` · 실시간 표시 설계서 §12).
 *
 * ⚠️ 음성 합성의 낱말 경계 신호(`onboundary` · `charIndex`)는 브라우저마다 오거나 오지 않음 — 오면 그 위치를
 * 「읽은 낱말 수」로 바꾸고(`wordCountAt`), 오지 않으면 소리 길이를 글자 수에 비례해 나눈 일정(`wordSchedule`)으로 칠함.
 */

type Word = { start: number; length: number };

function wordsOf(text: string): Word[] {
  return [...text.matchAll(/\S+/g)].map((match) => ({ start: match.index ?? 0, length: match[0].length }));
}

/** 경계 글자 위치 `charIndex` 까지 읽기 시작한 낱말 수 — 그 위치 이전에 시작한 낱말을 모두 셈. */
export function wordCountAt(text: string, charIndex: number): number {
  return wordsOf(text).filter((word) => word.start <= charIndex).length;
}

/** 경계 신호가 없을 때 낱말마다 켜는 시각(ms) — 첫 낱말은 0, 이후는 앞 낱말들의 글자 수에 비례함. */
export function wordSchedule(text: string, totalMs: number): number[] {
  const words = wordsOf(text);
  const total = words.reduce((sum, word) => sum + word.length, 0);
  if (total === 0) return [];
  let before = 0;
  return words.map((word) => {
    const at = Math.round((totalMs * before) / total);
    before += word.length;
    return at;
  });
}
