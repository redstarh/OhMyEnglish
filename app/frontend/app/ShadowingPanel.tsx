"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { API_BASE } from "@/lib/config";
import type { ShadowingSetup } from "@/lib/ws";

/**
 * 쉐도잉 클립을 보여 주고 들려주는 최소 화면 (`TASK-66.7` · 결정 90 ·
 * `docs/design/2026-09-14-shadowing-clip-audio-design.md` §6).
 *
 * ⛔ **낭독 녹음·비교는 이 화면의 범위가 아니다**(결정 90 이 「최소 쉐도잉 화면까지」로 정했다).
 * 그래서 「따라 읽어 보세요」 같은 안내를 넣지 않는다 — 없는 기능을 있다고 알리는 것이
 * `TASK-128.4` 가 잡은 결함(*"폴백이 사라지면 화면의 진입 안내가 거짓이 된다"*)과 같은 부류다.
 *
 * ⚠️ **재생 속도·반복은 서버가 정한다.** 값의 정본은 `Settings`(캡틴 결정 6 의 값역)이고 화면은
 * payload 로 받아 그대로 적용한다 — 여기에 사용자 조작 UI 를 만들면 결정 6 의 「설정값으로
 * 관리」를 화면이 뒤집는 셈이 된다.
 */

const PLAY_LABEL = "클립 듣기";
const STOP_LABEL = "멈추기";
const NO_AUDIO_NOTICE = "이 클립은 소리가 아직 없어요";

export function ShadowingPanel({ setup }: { setup: ShadowingSetup }) {
  const [playing, setPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
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

  // 화면을 벗어나면 소리를 끈다 — 세션이 끝난 뒤에도 소리가 남으면 학습자가 껐다고 믿지 못한다.
  useEffect(() => stop, [stop]);

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
        <button type="button" onClick={playing ? stop : play} style={{ padding: "0.5rem 1rem" }}>
          {playing ? STOP_LABEL : PLAY_LABEL}
        </button>
      ) : (
        /* ⛔ 버튼을 비활성으로 남기지 않고 **숨긴다** — 누를 수 있는 버튼이 404 를 받으면 학습자가
           자기 조작을 의심한다. 색은 `globals.css` 토큰에서만 온다(1차수 `F-1` 재발 방지). */
        <p style={{ color: "var(--foreground-muted)", margin: 0 }}>{NO_AUDIO_NOTICE}</p>
      )}
    </section>
  );
}
