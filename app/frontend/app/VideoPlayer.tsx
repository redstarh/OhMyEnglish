"use client";

import { useCallback, useEffect, useRef } from "react";
import {
  PLAYER_EMBED_BLOCKED,
  PLAYER_ENDED,
  loadPlayerApi,
  type YouTubePlayer,
} from "@/lib/youtube";

/**
 * YouTube 영상을 앱 안에서 재생하고 **구간을 반복**한다 (`TASK-167`).
 *
 * 설계: `docs/design/2026-09-18-video-learning-design.md` §5.
 *
 * ⛔ **플레이어 컨트롤을 가리지 않는다** — YouTube Developer Policies III.I.6 이 *"must not modify,
 * build upon, or block any portion or functionality of a YouTube player"* 로 그것을 금지한다. 그래서
 * 재생·정지·속도 UI 를 우리가 덧붙이지 않고 플레이어의 것을 쓴다.
 *
 * ⚠️ **구간 반복이 우리가 만드는 유일한 기능이다** — IFrame Player API 에 반복이 없다(`TASK-158` 7항).
 * `cueVideoById` 의 `endSeconds` 는 「그 지점에서 멈춤」이라 반복이 되지 않으므로, 재생 시각을
 * 지켜보다가 끝점을 넘으면 시작점으로 되돌린다.
 *
 * ⛔ **핸들을 `ref` 대신 콜백으로 넘긴다.** 부모가 필요한 것은 「구간을 틀어라」와 「지금 몇 초냐」
 * 둘뿐이고, 그 둘을 콜백으로 주면 React 버전에 따라 갈리는 `ref` 전달 규약에 기대지 않는다.
 */

/** 부모가 플레이어에 시킬 수 있는 것 — 여기 없는 것은 시킬 수 없다. */
export interface VideoPlayerHandle {
  /** 지금 재생 시각(초). 구간 담기의 시작·끝점이 이 값에서 나온다. */
  currentTime(): number;
  /** 그 구간을 **반복** 재생한다. 이미 반복 중이면 새 구간으로 갈아탄다. */
  playSpan(startSec: number, endSec: number): void;
  /** 반복을 끊는다. 재생 자체는 멈추지 않는다 — 사용자가 이어 보고 싶을 수 있다. */
  stopSpan(): void;
}

// 재생 시각을 얼마나 자주 보나. ⚠️ 구간 끝을 최대 이 간격만큼 넘긴 뒤 되돌아간다 — 학습에 지장이
// 없는 오차이고, 더 촘촘히 보면 얻는 것 없이 타이머만 자주 깬다.
const WATCH_INTERVAL_MS = 100;

export function VideoPlayer({
  youtubeId,
  onReady,
  onEmbedBlocked,
}: {
  youtubeId: string;
  onReady?: (handle: VideoPlayerHandle) => void;
  /** 임베드가 막혔을 때 — 화면이 「앱 안에서 재생할 수 없어요」와 외부 링크를 보인다. */
  onEmbedBlocked?: () => void;
}) {
  const hostRef = useRef<HTMLDivElement | null>(null);
  const playerRef = useRef<YouTubePlayer | null>(null);
  const spanRef = useRef<{ start: number; end: number } | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const clearTimer = useCallback(() => {
    if (timerRef.current !== null) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  useEffect(() => {
    let cancelled = false;

    void loadPlayerApi()
      .then((api) => {
        // ⚠️ 적재가 끝나기 전에 화면을 떠났으면 만들지 않는다 — 만들면 붙일 자리가 이미 없다.
        if (cancelled || !hostRef.current) {
          return;
        }
        const player = new api.Player(hostRef.current, {
          videoId: youtubeId,
          events: {
            onReady: () => {
              if (cancelled) {
                return;
              }
              onReady?.({
                currentTime: () => playerRef.current?.getCurrentTime() ?? 0,
                playSpan: (startSec, endSec) => {
                  spanRef.current = { start: startSec, end: endSec };
                  const current = playerRef.current;
                  if (!current) {
                    return;
                  }
                  current.seekTo(startSec, true);
                  current.playVideo();
                  clearTimer();
                  timerRef.current = setInterval(() => {
                    const span = spanRef.current;
                    const live = playerRef.current;
                    if (!span || !live) {
                      return;
                    }
                    if (live.getCurrentTime() >= span.end) {
                      live.seekTo(span.start, true);
                    }
                  }, WATCH_INTERVAL_MS);
                },
                stopSpan: () => {
                  spanRef.current = null;
                  clearTimer();
                },
              });
            },
            onStateChange: (event) => {
              // 영상이 끝까지 갔는데 반복 구간이 살아 있으면 되돌린다 — 끝점이 영상 끝과 같을 때
              // `getCurrentTime()` 감시가 그 자리를 못 잡는 경우가 있다.
              const span = spanRef.current;
              if (event.data === PLAYER_ENDED && span && playerRef.current) {
                playerRef.current.seekTo(span.start, true);
                playerRef.current.playVideo();
              }
            },
            onError: (event) => {
              if (PLAYER_EMBED_BLOCKED.some((code) => code === event.data)) {
                onEmbedBlocked?.();
              }
            },
          },
        });
        playerRef.current = player;
      })
      .catch(() => {
        // 스크립트를 못 실었다. ⚠️ 임베드 차단과 같은 자리로 모은다 — 사용자가 할 수 있는 일이
        // 「YouTube 에서 보기」 하나로 같다.
        if (!cancelled) {
          onEmbedBlocked?.();
        }
      });

    return () => {
      cancelled = true;
      clearTimer();
      spanRef.current = null;
      const player = playerRef.current;
      playerRef.current = null;
      player?.destroy();
    };
    // ⛔ `onReady`·`onEmbedBlocked` 를 의존성에 넣지 않는다 — 부모가 매 렌더에 새 함수를 만들면
    // 플레이어가 그때마다 파괴되고 다시 만들어져 **재생이 끊긴다.** 영상이 바뀔 때만 다시 만든다.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [youtubeId, clearTimer]);

  return <div ref={hostRef} />;
}
