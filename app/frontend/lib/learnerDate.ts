// 학습자 날짜 문구 (`TASK-329` · 회차 b16 보고서 §2 B). 홈 · 주간 리포트 · 결과 화면이 함께 씀.
// ⛔ 날짜는 API 가 학습자 타임존(`users.timezone`)으로 준 `YYYY-MM-DD` 만 씀 — 브라우저 시각으로
//    「오늘」·「이번 주」를 구하지 않음. 브라우저와 학습자의 타임존이 다르면 하루가 밀림.
// ⚠️ 계산은 UTC 자정에서 함 — 달력 날짜만 다루므로 서머타임이 끼어들 자리가 없음.

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function toUtc(isoDate: string): Date | null {
  const [y, m, d] = isoDate.split("-").map(Number);
  if (!y || !m || !d) return null;
  return new Date(Date.UTC(y, m - 1, d));
}

/** `2026-11-01` → `Nov 1`. 읽을 수 없는 값은 그대로 돌려줌. */
export function dayLabel(isoDate: string): string {
  const date = toUtc(isoDate);
  return date ? `${MONTHS[date.getUTCMonth()]} ${date.getUTCDate()}` : isoDate;
}

/** `YYYY-MM-DD` 에 `days` 일을 더한 날짜. */
export function addDays(isoDate: string, days: number): string {
  const date = toUtc(isoDate);
  if (!date) return isoDate;
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

/** 월요일부터 그 주 일요일까지 — `Nov 2 – Nov 8`. */
export function weekRangeLabel(weekStart: string): string {
  return `${dayLabel(weekStart)} – ${dayLabel(addDays(weekStart, 6))}`;
}

export type WeekRelation = "this" | "last" | "other";

/** 리포트의 주가 학습자의 이번 주 · 지난주 · 그 밖 가운데 어디인가. 기준이 없으면 `other` 임. */
export function weekRelation(weekStart: string, thisWeekStart: string | undefined): WeekRelation {
  if (!thisWeekStart) return "other";
  if (weekStart === thisWeekStart) return "this";
  if (weekStart === addDays(thisWeekStart, -7)) return "last";
  return "other";
}

/** 기간 이름 — 「This week」는 정말 이번 주일 때만 씀. 그 밖의 주는 이름 없이 날짜만 보임. */
export function weekName(relation: WeekRelation): string | null {
  if (relation === "this") return "This week";
  if (relation === "last") return "Last week";
  return null;
}

/** 결과 화면의 날짜 문구 — `today`(오늘 완료) 인가 `dated`(그 날짜로 씀) 인가 (`TASK-331` codex 리뷰 ②).
 *
 * ⛔ 오늘을 모르면(하루 요약 조회 실패) 세션 날짜로 씀 — 날짜를 박은 문구는 언제나 참이고, 「today」로 두면
 *    지난 세션을 오늘 것처럼 보였음. 세션 날짜를 모르면(옛 서버) 옛 동작(오늘 완료 문구)으로 돌아감.
 */
export function sessionWording(sessionDate: string | null, today: string | null): "today" | "dated" {
  if (sessionDate === null) return "today";
  return today === null || sessionDate !== today ? "dated" : "today";
}

/** 기록의 빈 날 줄 (`TASK-333` N8) — 「No study · Nov 2 – Nov 13」 · 하루면 「No study · Nov 5」. */
export function gapLabel(from: string, to: string): string {
  return from === to ? `No study · ${dayLabel(from)}` : `No study · ${dayLabel(from)} – ${dayLabel(to)}`;
}
