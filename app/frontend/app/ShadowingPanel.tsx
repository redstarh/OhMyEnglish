"use client";

import { type CSSProperties, useCallback, useEffect, useRef, useState } from "react";
import { judgeReadback, type ReadbackJudgment, type ReadbackWord } from "@/lib/api";
import { API_BASE } from "@/lib/config";
import type { ShadowingSetup } from "@/lib/ws";

/**
 * 쉐도잉 클립을 보여 주고 들려주는 최소 화면 (`TASK-66.7` · 결정 90 ·
 * `docs/design/2026-09-14-shadowing-clip-audio-design.md` §6).
 *
 * ⚠️ **낭독 «녹음» 은 2026-09-18 에 들어왔다** (`TASK-179` · 요구의 정본은
 * `docs/design/2026-09-08-shadowing-task-design.md` §12 요구 4). 결정 90 이 「최소 쉐도잉 화면까지」로
 * 범위를 정하면서 「낭독 녹음까지 함께」를 **기각**했고, 그 유예를 사용자가 그날 해제했다.
 *
 * ⚠️ **녹음을 다시 «듣는» 것은 같은 날 결정 128 이 열었다** (`TASK-182`) — 저장만 하고 들려주지
 * 않으면 학습 루프가 닫히지 않는다.
 * ⛔ **「비교」는 여전히 범위 밖이다** — 원본과 나란히 견주기·파형·점수를 만들지 않는다. 이 화면이
 * 하는 것은 **소리 하나를 재생하는 것**까지다.
 *
 * ⛔ **없는 기능을 있다고 알리지 않는다**는 규율은 그대로다(`TASK-128.4` 가 잡은 결함:
 * *"폴백이 사라지면 화면의 진입 안내가 거짓이 된다"*). 그래서 안내 문구는 **저장된다는 사실까지만**
 * 말하고 「발음을 봐 준다」처럼 아직 없는 것을 암시하지 않는다.
 *
 * ⚠️ **재생 속도·반복은 서버가 정한다.** 값의 정본은 `Settings`(캡틴 결정 6 의 값역)이고 화면은
 * payload 로 받아 그대로 적용한다 — 여기에 사용자 조작 UI 를 만들면 결정 6 의 「설정값으로
 * 관리」를 화면이 뒤집는 셈이 된다.
 */

const PLAY_LABEL = "클립 듣기";
const STOP_LABEL = "멈추기";
const NO_AUDIO_NOTICE = "이 클립은 소리가 아직 없어요";
const RECORD_LABEL = "따라 읽기";
const RECORD_END_LABEL = "읽기 끝";
// ⚠️ 「듣는다」까지 말한다 — 결정 128 이 재생을 열었으므로 이 문구가 없는 기능을 말하지 않는다.
const RECORDING_NOTICE = "듣고 있어요. 문장을 읽고 「읽기 끝」을 누르면 다시 들을 수 있어요.";
const PLAY_RECORDING_LABEL = "내 낭독 듣기";
// 낭독 판정 (`TASK-209` · 결정 131). ⛔ **「내 낭독 듣기」를 대신하지 않고 그 옆에 붙는다** —
// 설계서 §7 이 「귀로 견주는 길」을 없애지 않기로 정했다.
const JUDGE_LABEL = "낭독 판정 보기";
const JUDGING_LABEL = "견주는 중...";
// ⛔ **영어 오류 문면을 학습자에게 보이지 않는다** (`TASK-55` 가 세운 규율). 전사를 못 얻은 것과
// 요청이 실패한 것을 «같게» 말하는 이유는 `api/vocab.py` 와 같다 — 그 구분이 학습자에게 값을 주지
// 않고 둘 다 「다시 눌러 볼 일」이다.
const JUDGE_EMPTY_NOTICE = "읽은 소리를 알아듣지 못했어요. 다시 읽고 눌러 주세요.";
const JUDGE_LEGEND = "밑줄은 다르게 읽은 낱말이고 취소선은 빠뜨린 낱말이에요.";
// ⚠️ 전부 맞았을 때 범례를 보이지 않는다 — 화면에 없는 표시를 설명하는 문장이 된다.
const JUDGE_ALL_MATCH_NOTICE = "원본대로 읽었어요.";

/**
 * 낭독 진행도 문구 (`TASK-187` · 결정 129 ④).
 *
 * ⛔ **목표가 1이면 부르지 않는다** — 「1번 중 1번」은 뜻이 없고, 기본값이 1이라 설정을 올리지 않은
 * 사용자의 화면이 바뀌지 않아야 한다(설정이 생기는 것만으로 동작이 달라지지 않는다는 결정 6 의 규율).
 * ⚠️ **도달했다고 무엇이 열리지는 않는다** — 그래서 문구는 「다 읽었다」까지만 말하고 다음 단계를
 * 암시하지 않는다(`TASK-128.4` 가 잡은 「없는 기능의 안내가 거짓이 된다」와 같은 규율).
 */
function readProgressNotice(readTurns: number, target: number): string {
  return readTurns >= target
    ? `${target}번 다 읽었어요`
    : `${target}번 중 ${readTurns}번 읽었어요`;
}

/** 지금 나는 소리가 어느 것인가. ⛔ **한 값으로 두는 것이 「둘이 겹치지 않는다」를 구조로 만든다.** */
type Playing = "clip" | "recording";

/**
 * 낱말 하나를 판정에 맞게 그린다 (`TASK-209`).
 *
 * ⛔ **색 하나로만 가르지 않는다** — `globals.css` 에는 `--danger` 뿐이고(성공 색이 없다) 색만으로
 * 가르면 색을 못 가리는 학습자에게 세 갈래가 한 갈래로 보인다. 그래서 **밑줄과 취소선**으로 함께
 * 가르고 그 뜻을 아래 범례가 말한다.
 */
function wordStyle(verdict: ReadbackWord["verdict"]): CSSProperties {
  if (verdict === "match") return {};
  return {
    color: "var(--danger)",
    textDecoration: verdict === "missing" ? "line-through" : "underline",
  };
}

// 이 패널의 버튼 셋이 공유한다. ⚠️ **컴포넌트로 뽑지 않는 이유**: 세 버튼이 서로 다른 근거 주석을
// 갖고 각각 다른 조건(`has_audio` · 없음 · `recordingUrl`)에 감싸여 있어, 뽑으면 근거가 호출부와
// 갈라진다. 한쪽만 고쳐 모양이 어긋나는 것을 막는 데는 이 상수 하나로 충분하다.
const BUTTON_STYLE = { padding: "0.5rem 1rem" };

export function ShadowingPanel({
  setup,
  recordingUrl,
  recordingIds,
  readTurns = 0,
  onRecordingStart,
  onRecordingEnd,
}: {
  setup: ShadowingSetup;
  /**
   * 방금 저장된 낭독의 주소 (`TASK-182` · 결정 128). `null` 이면 **버튼을 보이지 않는다.**
   *
   * ⛔ **서버가 알린 주소만 온다** — 부모가 `shadowing_recording` 프레임을 받아 조립한다. 화면이
   * 「읽기 끝을 눌렀으니 저장됐다」로 추론하면 저장이 실패한 턴에 404 를 받는 버튼이 뜬다.
   */
  recordingUrl?: string | null;
  /**
   * 방금 저장된 낭독을 가리키는 두 값 (`TASK-209`). `null` 이면 **판정 버튼을 보이지 않는다.**
   *
   * ⛔ **주소를 다시 쪼개 쓰지 않는다** — `recordingUrl` 에서 조각을 뽑으면 주소 형태가 바뀔 때
   * 조용히 어긋난다. 조립하는 자리(부모)가 두 값을 그대로 함께 준다.
   */
  recordingIds?: { sessionId: string; utteranceId: string } | null;
  /**
   * 지금까지 읽은 낭독 회차 (`TASK-187` · 결정 129 ③). 서버가 준 값이고 **화면이 세지 않는다.**
   *
   * ⚠️ 목표는 `setup.repeat_count` 다 — 한 값이 「클립을 몇 번 들려주는가」와 「몇 번 읽게 하는가」를
   * 겸한다(결정 129 ②). 목표가 1이면 진행도를 **보이지 않는다**(결정 129 ④).
   */
  readTurns?: number;
  /** 낭독 턴을 연다 — 서버가 이 신호부터 오디오를 Nova 가 아니라 파일로 보낸다(설계서 §4.5). */
  onRecordingStart?: () => void;
  /** 낭독 턴을 닫는다. ⛔ 열어 둔 채 떠나면 **세션 전체가 녹음된다**(§12 요구 4). */
  onRecordingEnd?: () => void;
}) {
  const [playing, setPlaying] = useState<Playing | null>(null);
  const [recording, setRecording] = useState(false);
  // ⛔ **판정을 자동으로 받지 않는다** — 첫 호출이 Nova 를 한 번 타므로(결정 131) 학습자가 누를
  //    때만 비용이 난다. 그래서 상태를 화면이 들고 있고 렌더마다 받아 오지 않는다.
  // ⛔ **어느 낭독의 판정인지 함께 든다** — 다시 읽으면 발화가 새로 생기는데 판정만 남으면 «앞 낭독의
  //    판정»이 새 낭독의 것처럼 보인다. 키를 함께 들면 effect 로 지우지 않아도 렌더에서 갈린다.
  // ⚠️ `judgment` 가 `null` 이면 요청이 실패한 것이고 `words` 가 비면 전사를 못 얻은 것이다 —
  //    화면은 둘을 같게 말한다(위 문구 상수가 근거를 가진다).
  const [judged, setJudged] = useState<{
    utteranceId: string;
    judgment: ReadbackJudgment | null;
  } | null>(null);
  const [judging, setJudging] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  // ⛔ 정리 함수가 «렌더 시점의» 값을 보지 않게 ref 로도 든다 — 상태만 보면 언마운트 정리가
  //    「녹음 중이 아니었다」고 판단해 열린 턴을 닫지 않는다.
  const recordingRef = useRef(false);
  // 남은 재생 횟수. ⚠️ 상태가 아니라 ref 인 것은 `ended` 핸들러가 **최신 값**을 읽어야 하기
  // 때문이다 — 상태로 두면 핸들러가 만들어진 시점의 값을 보고 반복이 한 번에 끝난다.
  const remainingRef = useRef(0);

  const stop = useCallback(() => {
    const audio = audioRef.current;
    audioRef.current = null;
    if (audio) {
      audio.pause();
      audio.currentTime = 0;
    }
    remainingRef.current = 0;
    setPlaying(null);
  }, []);

  // 최신 「닫기」 콜백을 언마운트 정리가 읽게 한다. ⚠️ 관행은 `page.tsx` 의 `startSessionRef` 와
  // 같다 — effect 본문이 **ref 대입 하나**여서 `set-state-in-effect` 에 걸리지 않는다.
  const endTurnRef = useRef(onRecordingEnd);
  useEffect(() => {
    endTurnRef.current = onRecordingEnd;
  });

  const startRecording = useCallback(() => {
    // ⛔ **클립 소리를 먼저 끈다** — 스피커로 나가는 원본이 마이크로 되돌아오면 녹음이 원본과
    //    섞이고, 그러면 「학습자가 읽은 것」이 아닌 파일이 저장된다.
    stop();
    recordingRef.current = true;
    setRecording(true);
    onRecordingStart?.();
  }, [stop, onRecordingStart]);

  const endRecording = useCallback(() => {
    recordingRef.current = false;
    setRecording(false);
    onRecordingEnd?.();
  }, [onRecordingEnd]);

  // 화면을 벗어나면 소리를 끄고 **열린 낭독 턴도 닫는다.** 소리가 남으면 학습자가 껐다고 믿지
  // 못하고, 턴이 남으면 서버가 세션이 끝날 때까지 오디오를 파일에 쌓는다(설계서 §12 요구 4).
  useEffect(
    () => () => {
      stop();
      if (recordingRef.current) {
        recordingRef.current = false;
        endTurnRef.current?.();
      }
    },
    [stop],
  );

  /**
   * 소리 하나를 재생한다. **클립과 낭독이 이 함수를 공유한다** (`TASK-182`).
   *
   * ⛔ **먼저 `stop()` 을 부르는 것이 계약이다** — 재생 중인 다른 소리를 끄지 않으면 클립과 낭독이
   * 겹쳐 나고, 그러면 학습자는 어느 것이 자기 목소리인지 가릴 수 없다.
   */
  const play = useCallback(
    (kind: Playing, src: string, rate: number, repeat: number) => {
      stop();
      // ⚠️ 브라우저는 미디어 요소의 교차 출처 로드에 CORS 를 요구하지 않으므로 `crossOrigin` 을
      // 붙이지 않는다 — 붙이면 CORS 헤더가 필요해진다.
      const audio = new Audio(src);
      audio.playbackRate = rate;
      remainingRef.current = repeat;
      audio.addEventListener("ended", () => {
        remainingRef.current -= 1;
        if (remainingRef.current > 0) {
          void audio.play();
          return;
        }
        stop();
      });
      // ⚠️ 재생 실패(파일 없음 → 404)를 조용히 넘기지 않고 버튼을 되돌린다 — 「멈추기」가 영원히
      // 남으면 학습자가 소리를 기다린다.
      audio.addEventListener("error", stop);
      audioRef.current = audio;
      setPlaying(kind);
      void audio.play().catch(stop);
    },
    [stop],
  );

  const playClip = useCallback(() => {
    // ⛔ **상대 경로를 쓰지 않는다** — 프런트(:3000)와 백엔드(:8002)가 다른 포트라 상대 경로는
    // Next 개발 서버로 가서 404 가 된다. 주소의 정본은 `lib/config.ts` 의 `API_BASE` 다
    // (`lib/api.ts` 가 세운 규약).
    // 결정 6 의 값역(0.5~2.0배 · 1~10회)을 **브라우저 기능으로** 충족한다.
    play(
      "clip",
      `${API_BASE}/api/shadowing/clips/${setup.item_id}/audio`,
      setup.playback_rate,
      setup.repeat_count,
    );
  }, [play, setup.item_id, setup.playback_rate, setup.repeat_count]);

  const judge = useCallback(async () => {
    if (!recordingIds || judging) return;
    const { sessionId, utteranceId } = recordingIds;
    setJudging(true);
    const result = await judgeReadback(sessionId, utteranceId);
    setJudged({ utteranceId, judgment: result.ok ? result.value : null });
    setJudging(false);
  }, [recordingIds, judging]);

  const playRecording = useCallback(() => {
    if (!recordingUrl) return;
    // ⛔ **결정 6 의 속도·반복을 낭독에 걸지 않는다.** 그 값역은 「따라 읽을 원본을 어떻게 들려줄
    // 것인가」의 설정이고, 자기 목소리를 0.5배로 늘려 두 번 듣는 것은 그 설정이 정한 바가 아니다.
    play("recording", recordingUrl, 1, 1);
  }, [play, recordingUrl]);

  // ⛔ **앞 낭독의 판정을 새 낭독의 것으로 보이지 않게 한다** — 키가 어긋나면 없는 것으로 본다.
  const shown =
    recordingIds && judged?.utteranceId === recordingIds.utteranceId ? judged.judgment : null;
  const shownWords = shown?.words ?? [];

  return (
    <section style={{ marginTop: "1rem" }}>
      <h2 style={{ fontSize: "1rem", marginBottom: "0.25rem" }}>{setup.source_title}</h2>
      <p style={{ color: "var(--foreground-muted)", marginTop: 0, marginBottom: "0.75rem" }}>
        {setup.transcript}
      </p>
      {setup.has_audio ? (
        <button
          type="button"
          onClick={playing === "clip" ? stop : playClip}
          /* ⚠️ 녹음 중에는 잠근다 — 클립을 틀면 그 소리가 마이크로 들어가 녹음이 섞인다.
             `startRecording` 이 이미 재생을 끄지만, 그 뒤에 다시 틀 수 있는 문을 남기지 않는다. */
          disabled={recording}
          style={BUTTON_STYLE}
        >
          {playing === "clip" ? STOP_LABEL : PLAY_LABEL}
        </button>
      ) : (
        /* ⛔ 버튼을 비활성으로 남기지 않고 **숨긴다** — 누를 수 있는 버튼이 404 를 받으면 학습자가
           자기 조작을 의심한다. 색은 `globals.css` 토큰에서만 온다(1차수 `F-1` 재발 방지). */
        <p style={{ color: "var(--foreground-muted)", margin: 0 }}>{NO_AUDIO_NOTICE}</p>
      )}{" "}
      {/* ⚠️ 소리 없는 클립에서도 보인다 — 전사문만 있어도 읽을 수 있고, 녹음은 클립 오디오와
          무관한 경로다(서버가 마이크 프레임을 파일로 쌓는다). */}
      <button
        type="button"
        onClick={recording ? endRecording : startRecording}
        style={BUTTON_STYLE}
      >
        {recording ? RECORD_END_LABEL : RECORD_LABEL}
      </button>{" "}
      {/* ⛔ **저장된 낭독이 있을 때만 «보인다»** — 비활성 버튼으로 남기지 않는 것은 위 「소리 없는
          클립」과 같은 규율이다(`TASK-66.7`): 누를 수 있는 버튼이 404 를 받으면 학습자가 자기
          조작을 의심한다. 녹음 중에 잠그는 이유도 클립 버튼과 같다 — 스피커로 나간 소리가 마이크로
          되돌아오면 저장된 것이 학습자가 읽은 것이 아니게 된다. */}
      {recordingUrl ? (
        <button
          type="button"
          onClick={playing === "recording" ? stop : playRecording}
          disabled={recording}
          style={BUTTON_STYLE}
        >
          {playing === "recording" ? STOP_LABEL : PLAY_RECORDING_LABEL}
        </button>
      ) : null}
      {/* ⛔ **저장된 낭독이 있을 때만 보인다** — 위 두 버튼과 같은 규율이다. 녹음 중에 잠그는 것도
          같은 이유다(읽는 중에 판정을 부르면 방금 것이 아니라 앞 낭독을 견준다). */}
      {recordingIds ? (
        <button
          type="button"
          onClick={() => void judge()}
          disabled={recording || judging}
          style={BUTTON_STYLE}
        >
          {judging ? JUDGING_LABEL : JUDGE_LABEL}
        </button>
      ) : null}
      {recording ? (
        <p role="status" style={{ color: "var(--foreground-muted)", marginBottom: 0 }}>
          {RECORDING_NOTICE}
        </p>
      ) : null}
      {/* ⛔ **판정을 보이는 자리다.** 낱말이 0개면 전사를 못 얻었거나 요청이 실패한 것이고 그 둘을
          같게 말한다 — 학습자에게 「다시 읽고 눌러 보라」는 같은 행동이 남는다. */}
      {judged && recordingIds && judged.utteranceId === recordingIds.utteranceId ? (
        shownWords.length > 0 ? (
          <div style={{ marginTop: "0.5rem" }}>
            <p style={{ margin: 0, lineHeight: 1.8 }}>
              {shownWords.map((word, index) => (
                <span key={`${index}-${word.word}`} style={wordStyle(word.verdict)}>
                  {word.word}{" "}
                </span>
              ))}
            </p>
            <p style={{ color: "var(--foreground-muted)", marginBottom: 0 }}>
              {shownWords.every((word) => word.verdict === "match")
                ? JUDGE_ALL_MATCH_NOTICE
                : JUDGE_LEGEND}
            </p>
          </div>
        ) : (
          <p role="status" style={{ color: "var(--foreground-muted)", marginBottom: 0 }}>
            {JUDGE_EMPTY_NOTICE}
          </p>
        )
      ) : null}
      {/* ⛔ **목표가 2 이상일 때만 보인다** (결정 129 ④) — 기본값 1 에서는 「1번 중 1번」이 뜻이 없고,
          설정을 올리지 않은 사용자의 화면이 바뀌지 않아야 한다. 녹음 중에는 위 안내가 이미 말하고
          있으므로 겹쳐 두지 않는다. */}
      {setup.repeat_count > 1 && !recording ? (
        <p role="status" style={{ color: "var(--foreground-muted)", marginBottom: 0 }}>
          {readProgressNotice(readTurns, setup.repeat_count)}
        </p>
      ) : null}
    </section>
  );
}
