"use client";

// 문법 코스의 영상 — 저장된 위치부터 이어 재생한다 (`TASK-286` · 설계서 §7).
//
// ⛔ **`app/VideoPlayer.tsx` 를 넓히지 않고 따로 둔다** — 그 플레이어는 「구간 반복」이 계약이고
// (`playSpan`), 이쪽은 「이어 듣기」가 계약이다. 한 컴포넌트에 두 계약을 얹으면 한쪽을 고칠 때
// 다른 쪽이 조용히 바뀐다.
// ⚠️ 재생은 YouTube 임베드가 맡는다 — 앱은 영상의 소리를 받지도 저장하지도 않는다(설계서 §2).

import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";
import { loadPlayerApi, PLAYER_ENDED, PLAYER_PLAYING, type YouTubePlayer } from "@/lib/youtube";

export interface CoursePlayerHandle {
  currentTime(): number;
  pause(): void;
}

interface Props {
  youtubeId: string;
  startAt: number;
  onPlaying: () => void;
  onEnded: () => void;
  onUnavailable: () => void;
}

export const CoursePlayer = forwardRef<CoursePlayerHandle, Props>(function CoursePlayer(
  { youtubeId, startAt, onPlaying, onEnded, onUnavailable },
  ref,
) {
  const mountRef = useRef<HTMLDivElement | null>(null);
  const playerRef = useRef<YouTubePlayer | null>(null);
  // 콜백은 ref 로 잡는다 — 플레이어를 콜백이 바뀔 때마다 다시 만들면 재생이 끊긴다.
  const handlers = useRef({ onPlaying, onEnded, onUnavailable });
  useEffect(() => {
    handlers.current = { onPlaying, onEnded, onUnavailable };
  }, [onPlaying, onEnded, onUnavailable]);
  // 시작 위치는 처음 한 번만 쓴다 — 저장이 갱신될 때마다 되감으면 듣던 자리가 튄다.
  const startRef = useRef(startAt);

  useImperativeHandle(
    ref,
    () => ({
      currentTime: () => playerRef.current?.getCurrentTime() ?? startRef.current,
      pause: () => playerRef.current?.pauseVideo(),
    }),
    [],
  );

  useEffect(() => {
    let cancelled = false;
    let player: YouTubePlayer | null = null;
    loadPlayerApi()
      .then((api) => {
        if (cancelled || !mountRef.current) return;
        const target = document.createElement("div");
        mountRef.current.replaceChildren(target);
        player = new api.Player(target, {
          videoId: youtubeId,
          events: {
            onReady: () => {
              if (startRef.current > 0) player?.seekTo(startRef.current, true);
            },
            onStateChange: (event) => {
              if (event.data === PLAYER_PLAYING) handlers.current.onPlaying();
              if (event.data === PLAYER_ENDED) handlers.current.onEnded();
            },
            onError: () => handlers.current.onUnavailable(),
          },
        });
        playerRef.current = player;
      })
      .catch(() => {
        if (!cancelled) handlers.current.onUnavailable();
      });
    return () => {
      cancelled = true;
      playerRef.current = null;
      player?.destroy();
    };
  }, [youtubeId]);

  return (
    <div
      ref={mountRef}
      data-testid="course-player"
      style={{ aspectRatio: "16 / 9", width: "100%", background: "#111", borderRadius: 10, overflow: "hidden" }}
    />
  );
});
