/**
 * YouTube 쪽 전송과 플레이어 적재 (`TASK-167`).
 *
 * 설계: `docs/design/2026-09-18-video-learning-design.md` §5.
 *
 * ⛔ **여기에 논리를 두지 않는다.** 프런트에는 테스트 러너가 없으므로(`TASK-159` 6항) 판정은
 * 서버가 갖는다 — 특히 **URL 에서 영상 식별자를 뽑지 않는다**(`services/video_url.parse_youtube_id`
 * 가 그 일을 하고, 규칙이 두 곳에 있으면 갈라진다). 이 파일이 하는 것은 전송과 조립뿐이다.
 *
 * ⚠️ **oEmbed 를 브라우저에서 부르는 이유**: 백엔드에 런타임 HTTP 클라이언트가 없고(`httpx` 는 dev
 * 의존성뿐이다) 그것을 늘리는 것은 새 결정이다. oEmbed 는 **API 키 없이** 되고 **CORS 를 허용한다**
 * (2026-09-18 실측: `access-control-allow-origin` 이 요청 Origin 을 반영). ⇒ 백엔드 의존성이 늘지
 * 않고 백엔드 테스트가 밖으로 나가지 않는다.
 */

/** oEmbed 가 주는 것 중 우리가 쓰는 것. 나머지 키는 무시한다. */
export interface VideoMeta {
  title: string;
  channelName: string;
}

/**
 * 붙여넣은 링크의 제목·채널을 받아 온다. 못 받으면 **`null`**.
 *
 * ⚠️ **없는 영상은 404 가 아니라 400 이다**(2026-09-18 실측). 「404 면 없는 영상」으로 판정하면
 * 틀리므로 `response.ok` 하나로 본다 — 어느 쪽이든 화면 문구는 같다(설계서 §7).
 * ⚠️ 그리고 200 을 받았다는 것이 **임베드 가능을 보장하지 않는다** — 임베드를 막은 영상은 플레이어가
 * `onError`(`101`·`150`)로 알린다.
 */
export async function fetchVideoMeta(url: string): Promise<VideoMeta | null> {
  const endpoint = `https://www.youtube.com/oembed?url=${encodeURIComponent(url)}&format=json`;
  try {
    const response = await fetch(endpoint, { cache: "no-store" });
    if (!response.ok) {
      return null;
    }
    const body = (await response.json()) as { title?: unknown; author_name?: unknown };
    if (typeof body.title !== "string" || typeof body.author_name !== "string") {
      return null;
    }
    return { title: body.title, channelName: body.author_name };
  } catch {
    // 네트워크 실패. ⛔ 던지지 않는다 — 화면이 「지금 확인할 수 없어요」를 보이면 되고, 링크가
    // 틀린 것과 구별할 필요가 없다(설계서 §7 이 두 문구를 따로 두지 않는다).
    return null;
  }
}

/**
 * 썸네일 주소. **저장하지 않고 식별자에서 조립한다**(설계서 §2).
 *
 * ⚠️ 이 형태는 oEmbed 응답과 달리 문서화된 계약이 아니다(2026-09-18 실측으로 200 을 확인했다).
 * 패턴이 바뀌면 **썸네일이 안 보이고** 학습은 그대로 된다 — 그래서 화면이 이미지 실패에 대체
 * 표시를 둔다. 저장하지 않는 대신 얻는 것은 정책의 30일 보관 대상이 줄어드는 것이다.
 */
export function thumbnailUrl(youtubeId: string): string {
  return `https://i.ytimg.com/vi/${youtubeId}/hqdefault.jpg`;
}

/** 플레이어 상태값. IFrame Player API 가 정한 것이라 우리가 발명하지 않는다. */
export const PLAYER_ENDED = 0;
export const PLAYER_PLAYING = 1;

/**
 * 임베드를 막은 영상이 내는 오류 코드 — 화면이 이 둘만 따로 안내한다.
 *
 * ⚠️ 나머지 코드(`2` 잘못된 파라미터 · `5` HTML5 오류 · `100` 영상 없음)는 사용자가 손쓸 수 없는
 * 것이라 같은 문구로 모은다.
 */
export const PLAYER_EMBED_BLOCKED = [101, 150] as const;

/**
 * 우리가 실제로 부르는 플레이어 메서드만 담은 최소 타입.
 *
 * ⛔ **`@types/youtube` 를 의존성으로 들이지 않는다** — 쓰는 것이 여섯 개뿐이라 그 패키지의
 * 값어치가 그것을 관리하는 비용을 넘지 않는다. ⚠️ 여기 없는 메서드를 부르려면 이 타입을 먼저
 * 넓혀야 한다 — 그것이 「무엇을 쓰는지」를 한자리에 남기는 장치다.
 */
export interface YouTubePlayer {
  seekTo(seconds: number, allowSeekAhead: boolean): void;
  getCurrentTime(): number;
  getDuration(): number;
  playVideo(): void;
  pauseVideo(): void;
  destroy(): void;
}

interface YouTubePlayerEvent {
  data: number;
}

export interface YouTubePlayerOptions {
  videoId: string;
  events?: {
    onReady?: () => void;
    onStateChange?: (event: YouTubePlayerEvent) => void;
    onError?: (event: YouTubePlayerEvent) => void;
  };
}

interface YouTubeApi {
  Player: new (element: HTMLElement, options: YouTubePlayerOptions) => YouTubePlayer;
}

declare global {
  interface Window {
    YT?: YouTubeApi;
    onYouTubeIframeAPIReady?: () => void;
  }
}

const SCRIPT_SRC = "https://www.youtube.com/iframe_api";

// 적재를 한 번만 한다. ⚠️ 약속을 모듈에 담는 이유는 화면 둘이 같은 스크립트를 요구할 수 있고,
// 두 번 넣으면 `onYouTubeIframeAPIReady` 가 한쪽만 깨우기 때문이다.
let apiPromise: Promise<YouTubeApi> | null = null;

/**
 * IFrame Player API 를 싣고 준비되면 돌려준다.
 *
 * ⚠️ **콜백이 전역 하나뿐이다**(`window.onYouTubeIframeAPIReady`) — 그래서 적재를 모듈 수준에서
 * 한 번만 하고 그 약속을 공유한다. 이미 실려 있으면 즉시 해결한다.
 */
export function loadPlayerApi(): Promise<YouTubeApi> {
  if (apiPromise) {
    return apiPromise;
  }
  apiPromise = new Promise<YouTubeApi>((resolve, reject) => {
    if (window.YT) {
      resolve(window.YT);
      return;
    }
    window.onYouTubeIframeAPIReady = () => {
      if (window.YT) {
        resolve(window.YT);
      } else {
        reject(new Error("YouTube IFrame API loaded without YT"));
      }
    };
    const script = document.createElement("script");
    script.src = SCRIPT_SRC;
    script.async = true;
    script.onerror = () => reject(new Error("failed to load the YouTube IFrame API"));
    document.head.appendChild(script);
  });
  return apiPromise;
}
