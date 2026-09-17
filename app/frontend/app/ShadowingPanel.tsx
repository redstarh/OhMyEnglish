"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { API_BASE } from "@/lib/config";
import type { ShadowingSetup } from "@/lib/ws";

/**
 * 쉐도잉 클립을 보여 주고 들려주는 최소 화면 (`TASK-66.7` · 결정 90 ·
 * `docs/design/2026-09-14-shadowing-clip-audio-design.md` §6).
 *
 * ⚠️ **낭독 «녹음» 은 2026-09-18 에 들어왔다** (`TASK-179` · 요구의 정본은
 * `docs/design/2026-09-08-shadowing-task-design.md` §12 요구 4). 결정 90 이 「최소 쉐도잉 화면까지」로
 * 범위를 정하면서 「낭독 녹음까지 함께」를 **기각**했고, 그 유예를 사용자가 그날 해제했다.
 * ⛔ **비교·재생은 여전히 범위 밖이다** — 녹음한 것을 들려주거나 원본과 견주는 UI 를 만들지 않는다.
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
// ⚠️ 「저장된다」까지만 말한다 — 저장한 녹음으로 무엇을 하는지는 아직 없으므로 암시하지 않는다.
const RECORDING_NOTICE = "듣고 있어요. 문장을 읽고 「읽기 끝」을 누르면 녹음이 저장돼요.";

export function ShadowingPanel({
  setup,
  onRecordingStart,
  onRecordingEnd,
}: {
  setup: ShadowingSetup;
  /** 낭독 턴을 연다 — 서버가 이 신호부터 오디오를 Nova 가 아니라 파일로 보낸다(설계서 §4.5). */
  onRecordingStart?: () => void;
  /** 낭독 턴을 닫는다. ⛔ 열어 둔 채 떠나면 **세션 전체가 녹음된다**(§12 요구 4). */
  onRecordingEnd?: () => void;
}) {
  const [playing, setPlaying] = useState(false);
  const [recording, setRecording] = useState(false);
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
    setPlaying(false);
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

  const play = useCallback(() => {
    // ⛔ **상대 경로를 쓰지 않는다** — 프런트(:3000)와 백엔드(:8002)가 다른 포트라 상대 경로는
    // Next 개발 서버로 가서 404 가 된다. 주소의 정본은 `lib/config.ts` 의 `API_BASE` 다
    // (`lib/api.ts` 가 세운 규약). ⚠️ 브라우저는 미디어 요소의 교차 출처 로드에 CORS 를 요구하지
    // 않으므로 `crossOrigin` 을 붙이지 않는다 — 붙이면 CORS 헤더가 필요해진다.
    const audio = new Audio(`${API_BASE}/api/shadowing/clips/${setup.item_id}/audio`);
    // 결정 6 의 값역(0.5~2.0배 · 1~10회)을 **브라우저 기능으로** 충족한다.
    audio.playbackRate = setup.playback_rate;
    remainingRef.current = setup.repeat_count;
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
    setPlaying(true);
    void audio.play().catch(stop);
  }, [setup.item_id, setup.playback_rate, setup.repeat_count, stop]);

  return (
    <section style={{ marginTop: "1rem" }}>
      <h2 style={{ fontSize: "1rem", marginBottom: "0.25rem" }}>{setup.source_title}</h2>
      <p style={{ color: "var(--foreground-muted)", marginTop: 0, marginBottom: "0.75rem" }}>
        {setup.transcript}
      </p>
      {setup.has_audio ? (
        <button
          type="button"
          onClick={playing ? stop : play}
          /* ⚠️ 녹음 중에는 잠근다 — 클립을 틀면 그 소리가 마이크로 들어가 녹음이 섞인다.
             `startRecording` 이 이미 재생을 끄지만, 그 뒤에 다시 틀 수 있는 문을 남기지 않는다. */
          disabled={recording}
          style={{ padding: "0.5rem 1rem" }}
        >
          {playing ? STOP_LABEL : PLAY_LABEL}
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
        style={{ padding: "0.5rem 1rem" }}
      >
        {recording ? RECORD_END_LABEL : RECORD_LABEL}
      </button>
      {recording ? (
        <p role="status" style={{ color: "var(--foreground-muted)", marginBottom: 0 }}>
          {RECORDING_NOTICE}
        </p>
      ) : null}
    </section>
  );
}
