// 기록 화면의 줄 묶기와 날짜 줄 오른쪽 사실 (`TASK-333` N5 · N8). 화면(`app/history/page.tsx`)과 시험이 같은 함수를 봄.
// ⚠️ 값 import 를 두지 않음 — `tsc` 는 `.ts` 확장자 import 를 받지 않고 `node --test` 는 확장자 없는 import 를
//    풀지 못함. 날짜 문구(`gapLabel`)는 그래서 `learnerDate.ts` 에 둠.
import type { HistoryDay } from "./api";

export type HistoryRow =
  | { kind: "day"; row: HistoryDay }
  /** 공부하지 않은 날이 이어진 구간. `from` 이 이른 날, `to` 가 늦은 날임. */
  | { kind: "gap"; from: string; to: string };

/**
 * 공부하지 않은 날이 이어지면 한 줄로 접음 (`TASK-333` N8 · 사용자 결정 2026-11-14).
 * 회차 b18 에서 빈 날 줄이 모두 나와 공부한 두 날이 묻혔음.
 *
 * ⚠️ 입력은 서버 순서(최근 날부터)임. 하루뿐인 빈 날도 같은 모양의 줄로 둠 — 끊긴 자리가 보여야
 *    연속 학습일이 어디서 끊겼는지 읽힘(R15-5).
 */
export function groupHistoryRows(days: readonly HistoryDay[]): HistoryRow[] {
  const rows: HistoryRow[] = [];
  for (const day of days) {
    const last = rows[rows.length - 1];
    if (day.learned) {
      rows.push({ kind: "day", row: day });
    } else if (last?.kind === "gap") {
      rows[rows.length - 1] = { ...last, from: day.day };
    } else {
      rows.push({ kind: "gap", from: day.day, to: day.day });
    }
  }
  return rows;
}

// `TASK-329` — 「Not checked」가 무엇을 확인하지 않았다는 뜻인지 설명이 없었음.
// 규칙의 정본은 백엔드임: 레슨에서 한 말은 차례(턴)가 닫힐 때마다 분석 job 이 걸리고
// (`services/utterances.flush_pending_analysis`), 분석이 저장될 때 그날의 요약 행이 생김
// (`services/daily_summary.refresh_summary_for_utterance`). 그 행이 없는 날이 이 문구임.
export const NOT_ANALYZED = "Not analyzed yet";
// `TASK-333` N5 — 마친 세션이 모두 발화 0건인 날. 「Not analyzed yet」은 나중에 분석될 것처럼 읽혔음.
export const NOTHING_SAID = "Nothing said";

/** 그날 말한 세션이 하나도 없는가. `spoken` 이 없는 옛 서버에서는 거짓(옛 문구)임. */
export function saidNothing(row: HistoryDay): boolean {
  return row.learned && !row.analyzed && row.spoken === false;
}

/**
 * 한 줄의 오른쪽 사실. 넷을 갈라 말한다:
 * 학습이 없던 날 · 학습했고 요약이 있는 날 · 말하지 않은 날 · **말했는데 요약이 없는 날**(012 이전).
 * ⛔ 마지막을 「오류 0건」으로 쓰지 않는다 — 그것은 「분석했고 오류가 없었다」라는 다른 사실이다.
 */
export function dayFact(row: HistoryDay): string {
  if (!row.learned) return "";
  if (saidNothing(row)) return NOTHING_SAID;
  if (!row.analyzed) return NOT_ANALYZED;
  if (row.occurrence_count === 0) return "No mistakes";
  return `Mistakes ${row.occurrence_count} · Patterns ${row.pattern_count}`;
}
