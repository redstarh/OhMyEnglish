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
 * ⚠️ 그리고 200 을 받았다는 것이 **재생 가능을 보장하지 않는다** — 임베드를 막았거나 그 밖의 이유로
 * 재생이 안 되는 것은 플레이어가 `onError` 로 알린다.
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

/**
 * 그 영상의 watch 주소. **화면 둘이 각자 조립하지 않고 여기서 만든다.**
 *
 * ⚠️ 백엔드도 같은 형태를 `services/videos._WATCH_URL_PREFIX` 로 소유하고 `source_url` 에 그 형태로
 * 저장한다 — 화면이 만드는 링크와 저장된 출처가 같은 모양이어야 하므로 프런트 쪽도 한 자리로 모은다.
 */
export function watchUrl(youtubeId: string): string {
  return `https://www.youtube.com/watch?v=${youtubeId}`;
}

/** 플레이어 상태값. IFrame Player API 가 정한 것이라 우리가 발명하지 않는다. */
export const PLAYER_ENDED = 0;
export const PLAYER_PLAYING = 1;

// ⛔ **오류 코드 목록을 두지 않는다.** 이전 판은 `PLAYER_EMBED_BLOCKED = [101, 150]` 을 두고 그
// 둘만 안내했는데, **사용자가 할 수 있는 일이 어느 코드에서나 「YouTube 에서 보기」 하나로 같다.**
// 코드를 가르는 목록이 있으면 목록 밖의 오류에서 화면이 조용해진다 — 실측(2026-09-18 `TASK-176`):
// 없는 영상에 재생을 걸면 플레이어가 **영어로** "An error occurred…" 를 보이는데 우리 안내는
// 0건이었다. 판정은 `VideoPlayer` 의 `onError` 가 코드를 보지 않는 것으로 대신한다.

/**
 * 우리가 실제로 부르는 플레이어 메서드만 담은 최소 타입.
 *
 * ⛔ **`@types/youtube` 를 의존성으로 들이지 않는다** — 그 패키지의 값어치가 관리 비용을 넘지
 * 않는다. ⚠️ 여기 없는 메서드를 부르려면 이 타입을 먼저 넓혀야 한다 — 그것이 「무엇을 쓰는지」를
 * 한자리에 남기는 장치다. ⚠️ **이 목록이 실제 호출과 어긋나면 그 장치가 죽는다** — 처음 판이
 * `getDuration`·`pauseVideo` 를 적어 두고 부르지 않아 「쓰는 것이 여섯」이라는 주석이 거짓이었다.
 */
export interface YouTubePlayer {
  seekTo(seconds: number, allowSeekAhead: boolean): void;
  getCurrentTime(): number;
  playVideo(): void;
  destroy(): void;
}

interface YouTubePlayerEvent {
  data: number;
}

interface YouTubePlayerOptions {
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
