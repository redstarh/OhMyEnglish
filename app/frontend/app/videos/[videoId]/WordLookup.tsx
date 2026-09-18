"use client";

import { useCallback, useState } from "react";
import { lookupWord } from "@/lib/api";

/**
 * 담은 문장을 낱말 단위로 보이고, 누른 낱말의 뜻을 한 줄로 말한다 (`TASK-195` · 캡틴 결정 130).
 *
 * ⛔ **상태를 이 컴포넌트 안에 갇히게 두는 것이 설계다.** 부모(`page.tsx`)의 `phraseList` 는
 * `useMemo` 로 묶여 있고 그 주석이 이유를 갖는다 — 받아쓰기 textarea 가 같은 화면의 상태를 바꾸므로
 * **타이핑 한 글자마다** 문장 목록 전체가 다시 만들어진다. 조회 상태를 부모에 두면 그 의존이 늘어
 * 그 최적화가 깨진다.
 *
 * ⚠️ **저장하지 않는다** (결정 130) — 같은 낱말을 두 번 누르면 두 번 묻는다. 캐시를 두면 「어디에
 * 얼마나 두는가」가 따라오고, 그것이 §6 이 「재생목록 담기」를 뺀 근거와 같은 부류의 복잡도다.
 */

const LOOKUP_HINT = "낱말을 누르면 이 문장에서 쓰인 뜻을 알려 줘요";
const LOOKING_UP = "찾고 있어요…";
// ⚠️ **실패와 「뜻을 모른다」를 같은 문구로 말한다** — 그 구분이 학습자에게 값을 주지 않는다.
// 서버도 같은 판단으로 둘을 `meaning: null` 로 합쳤다(`api/vocab.py` 의 docstring).
const NO_MEANING = "뜻을 가져오지 못했어요. 다시 눌러 보세요.";

/** 조회에 보낼 낱말. ⛔ **구두점을 떼는 이유**: `book.` 을 그대로 보내면 모델이 문장 부호를 낱말의 일부로 읽는다. */
function cleanWord(token: string): string {
  return token.replace(/^[^\p{L}\p{N}'-]+|[^\p{L}\p{N}'-]+$/gu, "");
}

/**
 * 조회 상태. ⛔ **한 값으로 두는 것이 「닿을 수 없는 조합」을 없앤다** — `selected`·`meaning`·`looking`
 * 세 변수로 두었던 첫 판은 셋을 매 호출에 올바른 순서로 맞춰야 했고, 그 규율을 타입이 아니라 관행이
 * 지켰다(2026-09-18 `/simplify` 가 잡았다).
 */
type Lookup =
  | { kind: "idle" }
  | { kind: "looking"; word: string }
  | { kind: "done"; word: string; meaning: string | null };

export function WordLookup({ sentence }: { sentence: string }) {
  const [lookup, setLookup] = useState<Lookup>({ kind: "idle" });

  const ask = useCallback(
    async (token: string) => {
      const word = cleanWord(token);
      // 구두점만 있는 조각은 조회하지 않는다 — 돈을 쓰면서 뜻 없는 답을 받는다.
      if (!word) return;
      setLookup({ kind: "looking", word });
      const result = await lookupWord({ word, sentence });
      // ⛔ 실패(`ok: false`)와 「뜻을 못 얻었다」(`meaning: null`)를 같은 값으로 모은다.
      setLookup({ kind: "done", word, meaning: result.ok ? result.value.meaning : null });
    },
    [sentence],
  );

  return (
    <div>
      {/* ⚠️ 공백으로 쪼갠다 — 문장을 낱말로 가르는 규칙을 발명하지 않는다. 화면이 하는 일은
          「누를 수 있게 만드는 것」까지이고, 무엇이 한 낱말인지는 모델이 문맥으로 판단한다. */}
      <p style={{ margin: "0 0 0.25rem" }}>
        {sentence.split(/(\s+)/).map((token, index) =>
          token.trim() === "" ? (
            token
          ) : (
            <button
              key={index}
              type="button"
              onClick={() => void ask(token)}
              /* 낱말을 버튼으로 두면서 문장처럼 보이게 한다 — 색은 `globals.css` 토큰에서만 온다. */
              style={{
                background: "none",
                border: "none",
                padding: 0,
                font: "inherit",
                color: "inherit",
                cursor: "pointer",
                textDecoration:
                  lookup.kind !== "idle" && lookup.word === cleanWord(token)
                    ? "underline"
                    : "none",
              }}
            >
              {token}
            </button>
          ),
        )}
      </p>
      {/* ⛔ 아직 누르지 않았으면 **안내만** 보인다 — 없는 뜻을 빈 줄로 그리지 않는다. */}
      <p role="status" style={{ margin: "0 0 0.25rem", color: "var(--foreground-muted)" }}>
        {lookup.kind === "idle"
          ? LOOKUP_HINT
          : lookup.kind === "looking"
            ? `${lookup.word} — ${LOOKING_UP}`
            : `${lookup.word} — ${lookup.meaning ?? NO_MEANING}`}
      </p>
    </div>
  );
}
