"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { VideoPlayer, type VideoPlayerHandle } from "@/app/VideoPlayer";
import { fetchVideo, removePhrase, storePhrase, type VideoDetail } from "@/lib/api";
import { watchUrl } from "@/lib/youtube";
import { WordLookup } from "./WordLookup";

/**
 * 영상 학습 (`TASK-168` · 스토리보드 S3).
 *
 * 설계: `docs/design/2026-09-18-video-learning-design.md` §5 ·
 * `docs/design/2026-09-18-video-learning-storyboard.md` §4.
 *
 * ⛔ **자막을 보여 주지 않는다** — 남의 공개 영상 자막을 얻는 합법적 경로가 없다(`TASK-158`). 그
 * 자리를 **사용자가 듣고 받아 적는 것**이 대신하고, 그것이 이 화면의 중심 동작이다(결정 126).
 *
 * ⚠️ **구간 상한을 여기서 정하지 않는다** — 서버가 응답에 실어 준다(`clip_max_span_sec`). 정본은
 * 스키마의 `shadowing_items_span_within_limit` 이고, 화면이 자기 사본을 두면 **그 사본만 대조 장치가
 * 없어** 조용히 갈라진다.
 */

const BACK_LINK_LABEL = "← 영상 목록";
const SPAN_START_LABEL = "구간 시작";
const SPAN_END_LABEL = "구간 끝";
const SPAN_REDO_LABEL = "구간 다시 잡기";
const STORE_LABEL = "담기";
const CANCEL_LABEL = "취소";
const LISTEN_LABEL = "그 구간 듣기";
const PRACTISE_LABEL = "연습하기";
const REMOVE_LABEL = "지우기";
const TRANSCRIPT_LABEL = "들은 대로 적어 보세요";
const TRANSCRIPT_PLACEHOLDER = "확신이 없어도 들리는 대로 적어요";
const PHRASES_HEADING = "담은 문장";
const EMPTY_PHRASES = "아직 담은 문장이 없어요. 안 들리는 자리에서 구간을 잡아 보세요.";

const LOAD_FAILED_NOTICE = "이 영상을 찾을 수 없어요.";
const UNAVAILABLE_NOTICE = "지금 저장할 수 없어요. 잠시 뒤 다시 시도해 주세요.";
const REFUSED_NOTICE = "이 구간이나 문장을 담을 수 없어요. 구간과 문장을 다시 확인해 주세요.";
// ⚠️ **「지금」을 빼지 않는다** — 임베드 차단은 영구적이지만 없는 영상·일시 오류도 이 문구로
// 모이므로(`VideoPlayer` 의 `onUnplayable`), 영구적이라고 단정하면 틀리는 경우가 생긴다.
const UNPLAYABLE_NOTICE = "지금 이 영상을 앱 안에서 재생할 수 없어요.";
const OPEN_ON_YOUTUBE_LABEL = "YouTube 에서 보기";
const SPAN_BACKWARDS_NOTICE = "구간 끝이 시작보다 뒤여야 해요.";

// ⚠️ 라벨·레이아웃 값을 기존 화면들과 맞춘다 (`app/videos/page.tsx` 의 같은 주석).
const PAGE_STYLE = {
  maxWidth: 640,
  margin: "0 auto",
  padding: "2rem",
  fontFamily: "sans-serif",
} as const;

/**
 * 담는 중인 구간 하나. ⛔ **셋을 따로 들지 않는 이유**: 언제나 함께 세워지고 함께 비워지는데 따로
 * 두면 `end` 만 있고 `start` 가 없는 **성립할 수 없는 조합**이 타입에 남는다. `VideoPlayer` 의
 * `spanRef` 가 같은 갈래에서 이미 이 모양을 쓴다.
 */
interface Draft {
  start: number;
  /** `null` 이면 아직 끝점을 찍지 않았다 — 화면의 둘째 단계다. */
  end: number | null;
  transcript: string;
}

/** `0:42` 꼴로 보인다 — 초만 보이면 사용자가 영상 어디인지 감을 못 잡는다. */
function asClock(seconds: number): string {
  const whole = Math.floor(seconds);
  const minutes = Math.floor(whole / 60);
  return `${minutes}:${String(whole % 60).padStart(2, "0")}`;
}

export default function VideoLearningPage() {
  const params = useParams<{ videoId: string }>();
  const videoId = params.videoId;
  const router = useRouter();

  const [detail, setDetail] = useState<VideoDetail | null>(null);
  const [loadFailed, setLoadFailed] = useState(false);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [unplayable, setUnplayable] = useState(false);
  const [busy, setBusy] = useState(false);

  // ⛔ 플레이어 핸들을 상태가 아니라 ref 에 담는다 — 상태로 두면 핸들이 도착할 때 화면이 다시
  //    그려지고, 그 렌더가 `VideoPlayer` 에 새 콜백을 주어 플레이어가 파괴·재생성된다.
  const playerRef = useRef<VideoPlayerHandle | null>(null);

  // ⛔ `setBusy` 짝을 손으로 맞추지 않는다 — 빠뜨리면 화면이 영구히 잠긴다.
  const runBusy = useCallback(async <T,>(fn: () => Promise<T>): Promise<T> => {
    setBusy(true);
    try {
      return await fn();
    } finally {
      setBusy(false);
    }
  }, []);

  const reload = useCallback(async () => {
    const found = await fetchVideo(videoId);
    if (found === null) {
      setLoadFailed(true);
      return;
    }
    setDetail(found);
  }, [videoId]);

  // ⚠️ **비동기 함수로 감싼다** — `void reload()` 로 직접 부르면 `react-hooks/set-state-in-effect`
  // 가 막는다(실측). 그 규칙이 겨누는 것은 effect 첫머리의 **동기** setState 다.
  useEffect(() => {
    void (async () => {
      await reload();
    })();
  }, [reload]);

  const onPlayerReady = useCallback((handle: VideoPlayerHandle) => {
    playerRef.current = handle;
  }, []);

  const onUnplayable = useCallback(() => setUnplayable(true), []);

  const markStart = useCallback(() => {
    setDraft({ start: playerRef.current?.currentTime() ?? 0, end: null, transcript: "" });
    setNotice(null);
  }, []);

  const markEnd = useCallback(() => {
    if (draft === null) {
      return;
    }
    const at = playerRef.current?.currentTime() ?? 0;
    // ⛔ **저장될 정밀도로 접은 뒤 비교한다** (`TASK-170`). 원본으로만 보면 `5.0 → 5.001` 같은 구간이
    //    통과하고 서버가 그것을 거부해, 사용자는 「구간 끝이 시작보다 뒤여야 해요」가 아니라 일반 실패
    //    문구를 본다. ⚠️ 정밀도도 서버가 준 값이다 — 화면이 자기 상수를 두면 그것만 갈라진다.
    const precision = detail?.clip_precision_sec;
    const fold = (value: number) =>
      precision === undefined || precision <= 0
        ? value
        : Math.round(value / precision) * precision;
    const start = fold(draft.start);
    const end = fold(at);
    if (end <= start) {
      setNotice(SPAN_BACKWARDS_NOTICE);
      return;
    }
    // ⚠️ 상한도 서버가 준 값이다. 아직 안 왔으면(로드 전) 서버 검사에만 맡긴다.
    const limit = detail?.clip_max_span_sec;
    if (limit !== undefined && end - start > limit) {
      setNotice(`구간은 ${limit}초까지 담을 수 있어요.`);
      return;
    }
    setDraft({ ...draft, end: at });
    setNotice(null);
    playerRef.current?.playSpan(draft.start, at);
  }, [draft, detail]);

  const resetDraft = useCallback(() => {
    playerRef.current?.stopSpan();
    setDraft(null);
    setNotice(null);
  }, []);

  const store = useCallback(async () => {
    if (draft === null || draft.end === null || !draft.transcript.trim()) {
      return;
    }
    const result = await runBusy(() =>
      storePhrase(videoId, {
        transcript: draft.transcript.trim(),
        clipStartSec: draft.start,
        clipEndSec: draft.end as number,
      }),
    );
    if (!result.ok) {
      setNotice(result.reason === "refused" ? REFUSED_NOTICE : UNAVAILABLE_NOTICE);
      return;
    }
    resetDraft();
    await reload();
  }, [draft, videoId, resetDraft, reload, runBusy]);

  const listen = useCallback((startSec: number, endSec: number) => {
    playerRef.current?.playSpan(startSec, endSec);
  }, []);

  // ⛔ 연습은 대시보드가 소켓을 연다 — 세션 화면을 여기 복제하지 않는다. `item` 이 어느 문장을
  //    연습할지 정하고 그 배선은 `TASK-166` 이 만들었다.
  const practise = useCallback(
    (phraseId: string) => {
      router.push(`/?mode=shadowing&source=additional&item=${phraseId}`);
    },
    [router],
  );

  const remove = useCallback(
    async (phraseId: string) => {
      const result = await runBusy(() => removePhrase(videoId, phraseId));
      if (!result.ok) {
        setNotice(UNAVAILABLE_NOTICE);
        return;
      }
      await reload();
    },
    [videoId, reload, runBusy],
  );

  /**
   * ⚠️ 목록을 `useMemo` 로 묶는 이유: 받아쓰기 textarea 가 이 화면의 상태를 바꾸므로 **타이핑 한
   * 글자마다** 문장 목록 전체가 다시 만들어진다. 아래 의존은 타이핑에 바뀌지 않는다.
   */
  const phraseList = useMemo(
    () => (
      <ul style={{ listStyle: "none", padding: 0 }}>
        {(detail?.phrases ?? []).map((phrase) => (
          <li key={phrase.id} style={{ marginBottom: "1rem" }}>
            {/* 문장을 낱말 단위로 눌러 뜻을 본다 (`TASK-195` · 결정 130).
                ⚠️ **조회 상태는 이 컴포넌트 안에 있다** — 위 `useMemo` 의 의존을 늘리지 않으려는
                것이고, 그 이유는 이 목록이 타이핑마다 다시 만들어지지 않아야 하기 때문이다. */}
            <WordLookup sentence={phrase.transcript} />
            <p style={{ margin: "0 0 0.25rem" }}>
              {asClock(phrase.clip_start_sec)}~{asClock(phrase.clip_end_sec)}
            </p>
            <button
              type="button"
              onClick={() => listen(phrase.clip_start_sec, phrase.clip_end_sec)}
              disabled={busy}
            >
              {LISTEN_LABEL}
            </button>{" "}
            <button type="button" onClick={() => practise(phrase.id)} disabled={busy}>
              {PRACTISE_LABEL}
            </button>{" "}
            <button type="button" onClick={() => void remove(phrase.id)} disabled={busy}>
              {REMOVE_LABEL}
            </button>
          </li>
        ))}
      </ul>
    ),
    [detail?.phrases, busy, listen, practise, remove],
  );

  return (
    <main style={PAGE_STYLE}>
      <Link href="/videos">{BACK_LINK_LABEL}</Link>

      {loadFailed ? (
        <p role="alert">{LOAD_FAILED_NOTICE}</p>
      ) : (
        <>
          <h1>{detail?.title ?? ""}</h1>
          <p>{detail?.channel_name ?? ""}</p>

          {detail ? (
            <VideoPlayer
              youtubeId={detail.youtube_id}
              onReady={onPlayerReady}
              onUnplayable={onUnplayable}
            />
          ) : null}

          {unplayable && detail ? (
            <p role="alert">
              {UNPLAYABLE_NOTICE}{" "}
              <a href={watchUrl(detail.youtube_id)} target="_blank" rel="noreferrer">
                {OPEN_ON_YOUTUBE_LABEL}
              </a>
            </p>
          ) : null}

          <section style={{ margin: "1.5rem 0" }}>
            {draft === null ? (
              <button type="button" onClick={markStart} disabled={busy}>
                {SPAN_START_LABEL}
              </button>
            ) : draft.end === null ? (
              <>
                <p>구간 시작 {asClock(draft.start)}</p>
                <button type="button" onClick={markEnd} disabled={busy}>
                  {SPAN_END_LABEL}
                </button>{" "}
                <button type="button" onClick={resetDraft} disabled={busy}>
                  {SPAN_REDO_LABEL}
                </button>
              </>
            ) : (
              <>
                <p>
                  구간 {asClock(draft.start)}~{asClock(draft.end)} 을 반복해 들려주고 있어요.
                </p>
                <label htmlFor="phrase-transcript">{TRANSCRIPT_LABEL}</label>
                <br />
                <textarea
                  id="phrase-transcript"
                  value={draft.transcript}
                  placeholder={TRANSCRIPT_PLACEHOLDER}
                  onChange={(event) => setDraft({ ...draft, transcript: event.target.value })}
                  rows={3}
                  style={{ width: "100%" }}
                />
                <button
                  type="button"
                  onClick={() => void store()}
                  disabled={busy || !draft.transcript.trim()}
                >
                  {STORE_LABEL}
                </button>{" "}
                <button type="button" onClick={resetDraft} disabled={busy}>
                  {CANCEL_LABEL}
                </button>
              </>
            )}
            {notice ? <p role="status">{notice}</p> : null}
          </section>

          <h2>{PHRASES_HEADING}</h2>
          {detail && detail.phrases.length === 0 ? <p>{EMPTY_PHRASES}</p> : null}
          {phraseList}
        </>
      )}
    </main>
  );
}
