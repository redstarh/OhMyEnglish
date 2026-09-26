"use client";

import { useEffect, useRef, useState, type CSSProperties, type ReactNode } from "react";
import type { PronunciationOutcome, Speaker } from "@/lib/ws";

// 학습 세션의 대화 화면 (`TASK-272` · 사용자 요청 2026-09-26 — 채팅 말풍선형 재디자인).
//
// ⛔ **줄마다 `<p>` 하나 · 그 안에 `<strong>질문: </strong>`/`<strong>답변: </strong>` 접두를 둔다.**
// 하네스가 이 모양으로 줄을 고른다(`tests/harness/instrument.js` 의 `LINE_PREFIXES` ·
// `c1_session_walkthrough.py` · `c2_render_hierarchy.py`). 그래서 접두는 지우지 않고 **눈에서만
// 숨긴다** — 화면 낭독기에는 화자 표지로 그대로 읽힌다. `<p>` 안에 다른 글자(시각·버튼)를 넣으면
// `textContent` 가 기대값과 갈리므로 넣지 않는다.
// ⛔ **말풍선 글자색은 `--foreground`·`--foreground-muted` 두 토큰뿐이다** — C2 가 확정 줄은
// foreground, 부분 줄은 muted 인지 잰다. 참고 이미지의 「진한 바탕 + 흰 글자」 학습자 말풍선을
// 따르지 않고 옅은 바탕(`--accent-soft`)을 쓴 이유가 이것이다.
// ⚠️ 발화별 [음성]·[번역] 버튼은 튜터 줄 아래에 두되 백엔드가 생길 때까지 비활성이다
// (`ActionButton` 위 주석). 마이크는 버튼이 아니다: 세션은 누르지 않고 말하는 상시 음성이다.

export interface TranscriptLine {
  id: number;
  speaker: Speaker;
  text: string;
  /** 다시 듣기 재료 — 이번 세션에서 받은 튜터 음성의 PCM 조각(`TASK-274`). 학습자 줄은 빈 배열. */
  audio: Uint8Array[];
  /** 이 줄을 이루는 발화의 DB 순번 — 번역 요청의 키다(`TASK-275`). 부분 전사문은 빈 배열. */
  sequenceNos: number[];
}

/** 한 줄의 번역 상태. `key` 는 번역을 받을 때의 조각 수다 — 뒤에 조각이 더 붙으면 낡은 번역이 된다. */
type Translation =
  | { status: "loading"; key: number }
  | { status: "done"; key: number; text: string }
  | { status: "failed"; key: number };

// 발음 배지 문구 (A-5). **새로 만들지 않고 결과 화면 카드의 어휘를 그대로 쓴다**
// (`app/results/[sessionId]/page.tsx`) — 같은 판정을 두 화면이 다른 말로 부르면
// 학습자가 다른 것으로 읽는다. `pending`만 이 화면에 있는 상태이고 문구는
// `docs/storyboard.html` 03b 를 따른다. 점수·정답률은 쓰지 않는다 — "채점하지
// 않습니다. 시범합니다"가 톤 계약이다.
const PRONUNCIATION_BADGE: Record<PronunciationOutcome, string> = {
  pending: "🔊 발음 교정 중",
  correct: "✓ 좋아요",
  incorrect: "다시 연습해요",
  unclear: "잘 안 들렸어요",
};

// 색은 `app/globals.css`의 토큰만 쓴다 — 하드코딩 색이 다크모드 위계를 뒤집은 1차수 F-1의
// 재발 방지. `unclear`는 오류가 아니라 미판정이라 danger가 아니라 muted다(결과 화면과 동일).
const PRONUNCIATION_BADGE_COLOR: Record<PronunciationOutcome, string> = {
  pending: "var(--foreground-muted)",
  correct: "var(--foreground)",
  incorrect: "var(--danger)",
  unclear: "var(--foreground-muted)",
};

// 접두를 눈에서만 숨기는 표준 기법 — `display: none` 은 낭독기에서도 사라지므로 쓰지 않는다.
const VISUALLY_HIDDEN: CSSProperties = {
  position: "absolute",
  width: 1,
  height: 1,
  overflow: "hidden",
  clip: "rect(0 0 0 0)",
  whiteSpace: "nowrap",
};

const BUBBLE_BASE: CSSProperties = {
  maxWidth: "78%",
  padding: "0.7rem 0.95rem",
  borderRadius: 18,
  lineHeight: 1.5,
  wordBreak: "break-word",
};

function prefixFor(speaker: Speaker): string {
  return speaker === "agent" ? "질문: " : "답변: ";
}

function Avatar() {
  return (
    <div
      aria-hidden
      style={{
        flex: "0 0 auto",
        width: 36,
        height: 36,
        borderRadius: "50%",
        background: "var(--accent)",
        color: "var(--on-accent)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: "0.75rem",
        fontWeight: 700,
      }}
    >
      AI
    </div>
  );
}

// 말풍선 아래 [음성]·[번역] 버튼 (`TASK-273`). [음성]은 그 줄에 받은 음성이 있을 때만 켠다
// (`TASK-274` — 세션 중 브라우저 메모리에서 다시 재생한다). ⛔ **재생할 것이 없는 버튼은 비활성이다**
// — 누르면 아무 일도 없는 활성 버튼을 두면 학습자는 고장으로 읽는다. [번역]은 서버가 한국어 번역을
// 만들어 말풍선 안에 보여 준다(`TASK-275`).
// ⚠️ **버튼을 `<p>` 밖에 둔다** — 안에 두면 줄의 `textContent` 에 버튼 글자가 섞여 하네스 계약이 깨진다.
const PENDING_FEATURE_TITLE = "준비 중이에요";

function SpeakerIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M11 5 6 9H3v6h3l5 4z" />
      <path d="M15.5 8.5a5 5 0 0 1 0 7" />
      <path d="M18.5 5.5a9 9 0 0 1 0 13" />
    </svg>
  );
}

function TranslateIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M4 5h8M8 3v2M6 5c0 4 3 7 6 8M10 5c0 3-3 7-6 8" />
      <path d="m13 21 4-9 4 9M14.5 18h5" />
    </svg>
  );
}

function ActionButton({
  icon,
  label,
  onClick,
  unavailableTitle = PENDING_FEATURE_TITLE,
}: {
  icon: ReactNode;
  label: string;
  /** 없으면 비활성이다. */
  onClick?: () => void;
  unavailableTitle?: string;
}) {
  const enabled = onClick !== undefined;
  return (
    <button
      type="button"
      disabled={!enabled}
      onClick={onClick}
      title={enabled ? undefined : unavailableTitle}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "0.3rem",
        padding: "0.3rem 0.7rem",
        borderRadius: 999,
        border: "1px solid var(--border)",
        background: "var(--background)",
        color: enabled ? "var(--foreground)" : "var(--foreground-muted)",
        fontSize: "0.8rem",
        cursor: enabled ? "pointer" : "not-allowed",
      }}
    >
      {icon}
      {label}
    </button>
  );
}

/** 말풍선 한 줄. `muted` 는 부분 전사문·「듣고 있어요」처럼 아직 확정되지 않은 줄이다.
 *  `actions` 는 확정된 튜터 줄에만 켠다 — 부분 전사문은 아직 발화가 끝나지 않았다. */
function Bubble({
  speaker,
  muted,
  actions = false,
  onReplay,
  onTranslate,
  translation,
  children,
}: {
  speaker: Speaker;
  muted: boolean;
  actions?: boolean;
  onReplay?: () => void;
  onTranslate?: () => void;
  /** 말풍선 안 원문 아래에 보일 번역 줄. 없으면 그리지 않는다. */
  translation?: string | null;
  children: ReactNode;
}) {
  const isAgent = speaker === "agent";
  return (
    <div
      style={{
        display: "flex",
        gap: "0.5rem",
        alignItems: actions ? "flex-start" : "flex-end",
        justifyContent: isAgent ? "flex-start" : "flex-end",
      }}
    >
      {isAgent ? <Avatar /> : null}
      <div
        style={{
          maxWidth: BUBBLE_BASE.maxWidth,
          display: "flex",
          flexDirection: "column",
          alignItems: isAgent ? "flex-start" : "flex-end",
          gap: "0.4rem",
        }}
      >
        {/* ⛔ 번역 줄을 `<p>` «밖»에 둔다 — 안에 두면 줄의 `textContent` 가 하네스 기대값과 갈린다.
            그래서 말풍선 바탕은 이 감싸개가 갖고 `<p>` 는 글만 갖는다. */}
        <div
          style={{
            ...BUBBLE_BASE,
            maxWidth: "100%",
            background: isAgent ? "var(--surface)" : "var(--accent-soft)",
            borderBottomLeftRadius: isAgent ? 6 : 18,
            borderBottomRightRadius: isAgent ? 18 : 6,
          }}
        >
          <p style={{ color: muted ? "var(--foreground-muted)" : "var(--foreground)" }}>
            {children}
          </p>
          {translation ? (
            <div
              lang="ko"
              style={{
                marginTop: "0.5rem",
                paddingTop: "0.5rem",
                borderTop: "1px solid var(--border)",
                color: "var(--foreground-muted)",
                fontSize: "0.9rem",
              }}
            >
              {translation}
            </div>
          ) : null}
        </div>
        {actions ? (
          <div style={{ display: "flex", gap: "0.4rem" }}>
            <ActionButton
              icon={<SpeakerIcon />}
              label="음성"
              onClick={onReplay}
              unavailableTitle="이 말은 다시 들을 음성이 없어요"
            />
            <ActionButton
              icon={<TranslateIcon />}
              label="번역"
              onClick={onTranslate}
              unavailableTitle="번역을 가져오는 중이에요"
            />
          </div>
        ) : null}
      </div>
    </div>
  );
}

function Notice({ strong, children }: { strong: boolean; children: ReactNode }) {
  return (
    <p
      aria-live="polite"
      style={{
        color: strong ? "var(--foreground)" : "var(--foreground-muted)",
        fontWeight: strong ? 600 : 400,
        fontSize: "0.9rem",
        background: "var(--surface)",
        borderRadius: 12,
        padding: "0.55rem 0.8rem",
      }}
    >
      {children}
    </p>
  );
}

export function SessionChat({
  lines,
  partialLine,
  listening,
  pronunciation,
  entryNotice,
  commandNotice,
  pausedNotice,
  ending,
  onEnd,
  onReplay,
  onTranslate,
}: {
  lines: TranscriptLine[];
  partialLine: TranscriptLine | null;
  listening: boolean;
  pronunciation: PronunciationOutcome | null;
  entryNotice: string | null;
  commandNotice: string | null;
  /** 정지 중이면 그 문구, 아니면 `null` (결정 117 — 상태이므로 풀릴 때까지 남는다). */
  pausedNotice: string | null;
  ending: boolean;
  onEnd: () => void;
  onReplay: (line: TranscriptLine) => void;
  onTranslate: (line: TranscriptLine) => Promise<string | null>;
}) {
  const [translations, setTranslations] = useState<Record<number, Translation>>({});

  // [번역]을 누르면 받아 오고, 한 번 더 누르면 접는다. ⚠️ 이 상태는 이 컴포넌트가 들고 있다 — 세션이
  // 바뀌면 화면이 `connecting` 을 거치며 언마운트되므로 앞 세션의 번역이 새 세션 줄 id 에 남지 않는다.
  function toggleTranslation(line: TranscriptLine) {
    const current = translations[line.id];
    const key = line.sequenceNos.length;
    if (current?.status === "done" && current.key === key) {
      setTranslations((prev) => {
        const next = { ...prev };
        delete next[line.id];
        return next;
      });
      return;
    }
    setTranslations((prev) => ({ ...prev, [line.id]: { status: "loading", key } }));
    // ⛔ 거부도 「실패」로 닫는다 — 닫지 않으면 `loading` 에 머물러 버튼이 영원히 비활성이 된다
    // (응답 몸통이 JSON 이 아니면 `postJson` 이 던진다 · `TASK-275` 리뷰).
    void onTranslate(line)
      .catch(() => null)
      .then((text) => {
        setTranslations((prev) => ({
          ...prev,
          [line.id]: text === null ? { status: "failed", key } : { status: "done", key, text },
        }));
      });
  }

  function translationText(line: TranscriptLine): string | null {
    const current = translations[line.id];
    if (!current || current.key !== line.sequenceNos.length) return null;
    if (current.status === "loading") return "번역하는 중...";
    if (current.status === "failed") return "번역을 가져오지 못했어요. 다시 눌러 보세요.";
    return current.text;
  }

  // 새 줄이 오면 맨 아래로 내린다 — 대화가 길어지면 최신 질문이 화면 밖으로 밀려 학습자가
  // 무엇에 답할지 놓친다. ⚠️ 상태를 바꾸지 않고 DOM 스크롤만 옮기므로 effect 가 맞는 자리다.
  // ⛔ **이미 맨 아래 근처에 있을 때만 내린다** — 앞 질문을 다시 읽으려고 올린 학습자를 부분
  // 전사문이 올 때마다 끌어내리면 읽을 수가 없다(`TASK-272` 리뷰). 붙어 있었는지는 스크롤
  // 이벤트에서 기억한다: 새 줄이 붙은 «뒤»에 재면 높이가 이미 늘어 항상 「떨어져 있다」가 된다.
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const pinnedRef = useRef(true);
  useEffect(() => {
    const el = scrollRef.current;
    if (el && pinnedRef.current) el.scrollTop = el.scrollHeight;
  }, [lines, partialLine, listening, pronunciation]);
  const hint = ending
    ? "학습을 마무리하고 있어요"
    : pausedNotice
      ? "일시 정지 중이에요"
      : listening
        ? "말하는 중이에요"
        : "누르지 않고 바로 말하면 돼요";

  return (
    <section
      style={{
        marginTop: "1rem",
        border: "1px solid var(--border)",
        borderRadius: 24,
        overflow: "hidden",
        display: "flex",
        flexDirection: "column",
        background: "var(--background)",
      }}
    >
      <header
        style={{
          display: "flex",
          alignItems: "center",
          gap: "0.5rem",
          padding: "0.9rem 1.1rem",
          borderBottom: "1px solid var(--border)",
        }}
      >
        <span
          aria-hidden
          style={{ width: 10, height: 10, borderRadius: "50%", background: "var(--accent)" }}
        />
        <h2 style={{ fontSize: "1.1rem", fontWeight: 700, flex: 1 }}>영어 대화</h2>
        <button
          onClick={onEnd}
          disabled={ending}
          style={{
            padding: "0.45rem 0.9rem",
            borderRadius: 999,
            border: "1px solid var(--border)",
            background: "var(--surface)",
            color: "var(--foreground)",
            cursor: ending ? "default" : "pointer",
          }}
        >
          {ending ? "종료 중..." : "학습 종료"}
        </button>
      </header>

      {/* 알림 셋. ⛔ **스크롤 영역 밖에 둔다**(`TASK-272` 리뷰 HIGH) — 안에 두면 대화가 길어진 뒤
          뜬 알림이 화면 위로 밀려나고, 코치의 말을 정정하는 줄을 학습자가 못 본다. */}
      {(entryNotice || commandNotice || pausedNotice) && (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "0.5rem",
            padding: "0.75rem 1rem 0",
          }}
        >
          {/* 진입 안내 (`TASK-10.2` AC#2) — 발음 집중을 골랐을 때 무엇을 받았는지 말한다. */}
          {entryNotice && <Notice strong={false}>{entryNotice}</Notice>}
          {/* 음성 명령의 어긋남 (결정 113). ⛔ muted 로 두지 않는다 — 코치의 말을 정정하는 자리다. */}
          {commandNotice && <Notice strong>{commandNotice}</Notice>}
          {pausedNotice && <Notice strong>{pausedNotice}</Notice>}
        </div>
      )}

      <div
        ref={scrollRef}
        onScroll={(event) => {
          const el = event.currentTarget;
          pinnedRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 48;
        }}
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "0.75rem",
          padding: "1rem",
          minHeight: 280,
          maxHeight: "60vh",
          overflowY: "auto",
        }}
      >
        {lines.length === 0 && !partialLine && !listening && (
          <p style={{ color: "var(--foreground-muted)", textAlign: "center", margin: "auto 0" }}>
            대화를 기다리는 중...
          </p>
        )}
        {lines.map((line) => (
          <Bubble
            key={line.id}
            speaker={line.speaker}
            muted={false}
            actions={line.speaker === "agent"}
            onReplay={line.audio.length > 0 ? () => onReplay(line) : undefined}
            onTranslate={
              line.sequenceNos.length > 0 && translations[line.id]?.status !== "loading"
                ? () => toggleTranslation(line)
                : undefined
            }
            translation={translationText(line)}
          >
            <strong style={VISUALLY_HIDDEN}>{prefixFor(line.speaker)}</strong>
            {line.text}
          </Bubble>
        ))}
        {partialLine ? (
          <Bubble speaker={partialLine.speaker} muted>
            <strong style={VISUALLY_HIDDEN}>{prefixFor(partialLine.speaker)}</strong>
            {partialLine.text}
          </Bubble>
        ) : (
          listening && (
            <Bubble speaker="user" muted>
              듣고 있어요...
            </Bubble>
          )
        )}
        {/* 발음 배지 (A-5). 다음 `pronunciation` 프레임이 올 때까지 최신 판정을 남긴다. */}
        {pronunciation && (
          <p
            aria-live="polite"
            style={{
              color: PRONUNCIATION_BADGE_COLOR[pronunciation],
              fontWeight: 600,
              fontSize: "0.9rem",
              alignSelf: "center",
              background: "var(--surface)",
              borderRadius: 999,
              padding: "0.3rem 0.8rem",
            }}
          >
            {PRONUNCIATION_BADGE[pronunciation]}
          </p>
        )}
      </div>

      {/* 마이크 상태. ⛔ 버튼이 아니다 — 세션은 상시 음성이라 누를 것이 없다. */}
      <footer
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: "0.6rem",
          padding: "0.9rem 1rem 1.2rem",
          borderTop: "1px solid var(--border)",
        }}
      >
        <span
          style={{
            fontSize: "0.85rem",
            color: "var(--foreground-muted)",
            background: "var(--surface)",
            borderRadius: 999,
            padding: "0.3rem 0.8rem",
          }}
        >
          {hint}
        </span>
        <div
          aria-hidden
          className={listening ? "omy-mic-listening" : undefined}
          style={{
            width: 56,
            height: 56,
            borderRadius: "50%",
            background: listening ? "var(--accent)" : "var(--surface)",
            color: listening ? "var(--on-accent)" : "var(--accent)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            animation: listening ? "omy-mic-pulse 1.2s ease-out infinite" : undefined,
          }}
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor"
            strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="9" y="3" width="6" height="11" rx="3" />
            <path d="M5 11a7 7 0 0 0 14 0" />
            <line x1="12" y1="18" x2="12" y2="21" />
          </svg>
        </div>
      </footer>
    </section>
  );
}
