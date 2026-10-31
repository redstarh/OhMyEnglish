// 추가 학습 목록과 음성 명령의 대상 조회 (`TASK-295` · 리디자인 설계서
// `docs/design/2026-11-01-v0-home-redesign-design.md` §4). 홈 화면(`page.tsx`)에서 옮겨 왔고 거동은 같음.
// ⚠️ 홈의 세션 화면과 이후의 대시보드가 같은 목록을 읽음 — 두 곳에 적으면 버튼과 음성 명령이 갈림.

import type { SessionEntry } from "@/lib/config";
import type { AdditionalTarget } from "@/lib/ws";

/** 항목의 고정 키. 화면 문구가 바뀌어도 그대로 남음 — `data-testid="practice-<key>"` 와 React key 가 이 값을 씀. */
export type AdditionalLearningKey =
  | "free_talk"
  | "weak_patterns"
  | "five_questions"
  | "pronunciation"
  | "shadowing"
  | "videos"
  | "course"
  | "roleplay";

export type AdditionalLearningItem = {
  key: AdditionalLearningKey;
  label: string;
  entry: SessionEntry | null;
  href?: string;
  target?: AdditionalTarget;
  note?: string;
};

/** 항목이 눌릴 수 있는가. `entry` 도 `href` 도 없으면 비활성임(「업무 역할극」 · 아래 목록 주석). */
export function isAdditionalLearningEnabled(item: AdditionalLearningItem): boolean {
  return item.entry !== null || item.href !== undefined;
}

// 추가 학습 메뉴 (`TASK-10.2` · 진입점 설계서
// `docs/design/2026-09-12-additional-learning-entry-design.md` §2).
//
// ⛔ **항목이 다섯이 아니라 여섯이다.** PRD §7(:74)은 다섯을 열거하는데 R10-5(:145)가
// *"발음 집중 연습은 §7 Additional Learning 메뉴의 «독립 항목»으로 둔다"*를 글자로 요구한다.
// 설계서 §1 이 그 어긋남을 적었고 여기서 여섯으로 둔다 — 접으면 그 요구가 조용히 사라진다.
//
// ⛔ **`entry: null` 은 「아직 표면이 없다」다.** 항목을 지우지 않는 이유가 설계서 §2 에 있다:
// 지우면 다음 사람이 「원래 다섯이었다」로 읽고 위 어긋남이 되살아난다. 비활성 버튼이 그 사실을
// 화면에서도 말한다.
//
// ⚠️ **셋이 같은 표면(모드 없음)을 쓰는 것은 의도다** — 그 셋의 차이는 지시문이 아니라 **계획
// 데이터**에 있다(초점·질문·무대). 모드로 갈라도 조립되는 지시문이 같으므로 값역만 늘어난다.
// ⚠️ **`target` 은 음성 명령이 이 목록을 가리키는 키다** (`TASK-61.8` · 결정 110 ②). 매핑을 따로
// 두지 않고 이 목록에서 유도한다 — 두 곳에 적으면 화면 버튼과 음성 명령이 서로 다른 세션을 연다.
// ⚠️ 앞 두 항목이 **같은 `target`** 인 것은 의도다(entry 가 같고 차이가 계획 데이터에 있다 — 위 주석).
// ⛔ 「업무 역할극」에는 `target` 을 주지 않는다 — 열 수 없는 것을 음성으로 고를 수 있게 하면 안 된다.
// ⚠️ **`href` 는 `TASK-168` 이 더했다 — 세션을 열지 않고 «화면으로 가는» 항목의 자리다.** 영상 학습은
// 지시문이 달라지는 갈래가 아니라 화면과 자산 관리가 다른 갈래라서 세션 모드를 새로 만들지 않았다
// (`docs/design/2026-09-18-video-learning-design.md` §1 질문 5).
// ⛔ 그래서 항목의 상태가 셋이 됐다: `entry` 가 있으면 세션 · `href` 가 있으면 이동 · 둘 다 없으면
// 비활성(「업무 역할극」). 위 `isAdditionalLearningEnabled` 와 홈 렌더의 `disabled` 가 그 셋을 가른다.
export const ADDITIONAL_LEARNING: ReadonlyArray<AdditionalLearningItem> = [
  { key: "free_talk", label: "자유 대화", target: "conversation", entry: { source: "additional" } },
  { key: "weak_patterns", label: "약점 패턴 집중", target: "conversation", entry: { source: "additional" } },
  // `TASK-5` Task 6(사용자 결정 79) — 이 항목이 **무대 정하기 진입**이다. ⛔ 이전에는 `mode` 가 없어
  // 위 둘과 구별되지 않았고, 그래서 백엔드가 이 세션을 가릴 수단이 없었다(그 설계서 §5).
  {
    key: "five_questions",
    label: "질문 답변 5개",
    target: "scenario_intake",
    entry: { mode: "scenario_intake", source: "additional" },
  },
  {
    key: "pronunciation",
    label: "발음 집중",
    target: "pronunciation",
    entry: { mode: "pronunciation", source: "additional" },
  },
  { key: "shadowing", label: "쉐도잉", target: "shadowing", entry: { mode: "shadowing", source: "additional" } },
  // ⛔ **「업무 역할극」의 빈 칸을 재사용하지 않았다** — 그 칸은 무대 선택 화면의 부재를 가리키는
  // 표식이고 소유가 `TASK-102`·`TASK-5` 다. 영상 학습은 **일곱째** 로 붙는다.
  // ⛔ `target` 을 주지 않는다 — 음성 명령으로 이 화면에 가려면 `AdditionalTarget` 값역과 백엔드
  // `ADDITIONAL_TARGETS` 를 함께 열어야 하고, 그것은 이 갈래의 요구가 아니다(설계서 §1 질문 5).
  { key: "videos", label: "영상으로 배우기", entry: null, href: "/videos" },
  // 문법 코스 (`TASK-286`) — 영상 학습처럼 화면으로 가는 항목이라 `target` 을 주지 않는다.
  { key: "course", label: "문법 코스", entry: null, href: "/course" },
  { key: "roleplay", label: "업무 역할극", entry: null, note: "무대를 고르는 화면이 아직 없어요" },
];

/** 음성 명령이 고른 대상의 진입 정보. 없으면 `null` — 화면은 그때 새 세션을 열지 않는다.
 *
 * ⛔ **`via: "voice_command"` 를 여기서 붙인다** (`TASK-242` · 결함 `TASK-234`). 이 함수가 **음성
 * 명령으로만 불리는 유일한 자리**이므로, 표(`ADDITIONAL_LEARNING`)의 `entry` 에 넣지 않고 여기서
 * 덧붙인다 — 표에 넣으면 같은 항목을 누르는 **화면 버튼도** 음성으로 기록돼 결함의 반대 방향이 된다.
 * ⚠️ 표의 객체를 고치지 않고 새 객체를 만든다 — 그 상수는 모듈 수준에서 공유되므로 제자리에서
 * 바꾸면 이후의 화면 진입까지 오염된다.
 */
export function entryForTarget(target: AdditionalTarget): SessionEntry | null {
  const entry = ADDITIONAL_LEARNING.find((item) => item.target === target)?.entry;
  return entry ? { ...entry, via: "voice_command" } : null;
}
