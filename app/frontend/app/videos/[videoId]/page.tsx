"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { VideoPlayer, type VideoPlayerHandle } from "@/app/VideoPlayer";
import {
  fetchVideo,
  removePhrase,
  storePhrase,
  type VideoDetail,
  type WriteFailure,
} from "@/lib/api";

/**
 * 영상 학습 (`TASK-168` · 스토리보드 S3).
 *
 * 설계: `docs/design/2026-09-18-video-learning-design.md` §5 ·
 * `docs/design/2026-09-18-video-learning-storyboard.md` §4.
 *
 * ⛔ **자막을 보여 주지 않는다** — 남의 공개 영상 자막을 얻는 합법적 경로가 없다(`TASK-158`). 그
 * 자리를 **사용자가 듣고 받아 적는 것**이 대신하고, 그것이 이 화면의 중심 동작이다(결정 126).
 *
 * ⚠️ **구간 상한 90초와 순서는 서버가 다시 잰다.** 여기서 미리 막는 것은 사용자를 위한 것이고
 * (버튼을 눌러 실패를 보지 않게) 값역의 정본은 스키마와 서버다(설계서 §7).
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
const EMBED_BLOCKED_NOTICE = "이 영상은 앱 안에서 재생할 수 없어요.";
const OPEN_ON_YOUTUBE_LABEL = "YouTube 에서 보기";
const SPAN_TOO_LONG_NOTICE = "구간은 90초까지 담을 수 있어요.";
const SPAN_BACKWARDS_NOTICE = "구간 끝이 시작보다 뒤여야 해요.";

// 설계서 §2 — 스키마의 `shadowing_items_span_within_limit` 이 정본이고 이 값은 사용자를 미리
// 막기 위한 사본이다. ⚠️ 갈리면 서버가 이긴다(사용자는 `422` 를 본다).
const MAX_SPAN_SECONDS = 90;

function noticeFor(reason: WriteFailure): string {
  return reason === "refused" ? REFUSED_NOTICE : UNAVAILABLE_NOTICE;
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
  const [spanStart, setSpanStart] = useState<number | null>(null);
  const [spanEnd, setSpanEnd] = useState<number | null>(null);
  const [transcript, setTranscript] = useState("");
  const [notice, setNotice] = useState<string | null>(null);
  const [embedBlocked, setEmbedBlocked] = useState(false);
  const [busy, setBusy] = useState(false);

  // ⛔ 플레이어 핸들을 상태가 아니라 ref 에 담는다 — 상태로 두면 핸들이 도착할 때 화면이 다시
  //    그려지고, 그 렌더가 `VideoPlayer` 에 새 콜백을 주어 플레이어가 파괴·재생성된다.
  const playerRef = useRef<VideoPlayerHandle | null>(null);

  const reload = useCallback(async () => {
    const found = await fetchVideo(videoId);
    if (found === null) {
      setLoadFailed(true);
      return;
    }
    setDetail(found);
  }, [videoId]);

  // ⚠️ **비동기 함수로 감싼다** — `void reload()` 로 직접 부르면 `react-hooks/set-state-in-effect`
  // 가 막는다(실측). 그 규칙이 겨누는 것은 effect 첫머리의 **동기** setState 이고, 조회가 끝난 뒤의
  // 갱신은 그 대상이 아니다. `app/videos/page.tsx` 가 같은 형태를 쓴다.
  useEffect(() => {
    void (async () => {
      await reload();
    })();
  }, [reload]);

  const onPlayerReady = useCallback((handle: VideoPlayerHandle) => {
    playerRef.current = handle;
  }, []);

  const onEmbedBlocked = useCallback(() => setEmbedBlocked(true), []);

  const markStart = useCallback(() => {
    const at = playerRef.current?.currentTime() ?? 0;
    setSpanStart(at);
    setSpanEnd(null);
    setNotice(null);
  }, []);

  const markEnd = useCallback(() => {
    if (spanStart === null) {
      return;
    }
    const at = playerRef.current?.currentTime() ?? 0;
    if (at <= spanStart) {
      setNotice(SPAN_BACKWARDS_NOTICE);
      return;
    }
    if (at - spanStart > MAX_SPAN_SECONDS) {
      setNotice(SPAN_TOO_LONG_NOTICE);
      return;
    }
    setSpanEnd(at);
    setNotice(null);
    playerRef.current?.playSpan(spanStart, at);
  }, [spanStart]);

  const resetSpan = useCallback(() => {
    playerRef.current?.stopSpan();
    setSpanStart(null);
    setSpanEnd(null);
    setTranscript("");
    setNotice(null);
  }, []);

  const store = useCallback(async () => {
    if (spanStart === null || spanEnd === null || !transcript.trim()) {
      return;
    }
    setBusy(true);
    const result = await storePhrase(videoId, {
      transcript: transcript.trim(),
      clipStartSec: spanStart,
      clipEndSec: spanEnd,
    });
    setBusy(false);
    if (!result.ok) {
      setNotice(noticeFor(result.reason));
      return;
    }
    resetSpan();
    await reload();
  }, [spanStart, spanEnd, transcript, videoId, resetSpan, reload]);

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
      setBusy(true);
      const result = await removePhrase(videoId, phraseId);
      setBusy(false);
      if (!result.ok) {
        setNotice(UNAVAILABLE_NOTICE);
        return;
      }
      await reload();
    },
    [videoId, reload],
  );

  if (loadFailed) {
    return (
      <main style={{ padding: "2rem", maxWidth: "48rem", margin: "0 auto" }}>
        <Link href="/videos">{BACK_LINK_LABEL}</Link>
        <p role="alert">{LOAD_FAILED_NOTICE}</p>
      </main>
    );
  }

  return (
    <main style={{ padding: "2rem", maxWidth: "48rem", margin: "0 auto" }}>
      <Link href="/videos">{BACK_LINK_LABEL}</Link>
      <h1>{detail?.title ?? ""}</h1>
      <p>{detail?.channel_name ?? ""}</p>

      {detail ? (
        <VideoPlayer
          youtubeId={detail.youtube_id}
          onReady={onPlayerReady}
          onEmbedBlocked={onEmbedBlocked}
        />
      ) : null}

      {embedBlocked && detail ? (
        <p role="alert">
          {EMBED_BLOCKED_NOTICE}{" "}
          <a
            href={`https://www.youtube.com/watch?v=${detail.youtube_id}`}
            target="_blank"
            rel="noreferrer"
          >
            {OPEN_ON_YOUTUBE_LABEL}
          </a>
        </p>
      ) : null}

      <section style={{ margin: "1.5rem 0" }}>
        {spanStart === null ? (
          <button type="button" onClick={markStart} disabled={busy}>
            {SPAN_START_LABEL}
          </button>
        ) : spanEnd === null ? (
          <>
            <p>구간 시작 {asClock(spanStart)}</p>
            <button type="button" onClick={markEnd} disabled={busy}>
              {SPAN_END_LABEL}
            </button>{" "}
            <button type="button" onClick={resetSpan} disabled={busy}>
              {SPAN_REDO_LABEL}
            </button>
          </>
        ) : (
          <>
            <p>
              구간 {asClock(spanStart)}~{asClock(spanEnd)} 을 반복해 들려주고 있어요.
            </p>
            <label htmlFor="phrase-transcript">{TRANSCRIPT_LABEL}</label>
            <br />
            <textarea
              id="phrase-transcript"
              value={transcript}
              placeholder={TRANSCRIPT_PLACEHOLDER}
              onChange={(event) => setTranscript(event.target.value)}
              rows={3}
              style={{ width: "100%" }}
            />
            <button type="button" onClick={() => void store()} disabled={busy || !transcript.trim()}>
              {STORE_LABEL}
            </button>{" "}
            <button type="button" onClick={resetSpan} disabled={busy}>
              {CANCEL_LABEL}
            </button>
          </>
        )}
        {notice ? <p role="status">{notice}</p> : null}
      </section>

      <h2>{PHRASES_HEADING}</h2>
      {detail && detail.phrases.length === 0 ? <p>{EMPTY_PHRASES}</p> : null}
      <ul style={{ listStyle: "none", padding: 0 }}>
        {(detail?.phrases ?? []).map((phrase) => (
          <li key={phrase.id} style={{ marginBottom: "1rem" }}>
            <p style={{ margin: "0 0 0.25rem" }}>{phrase.transcript}</p>
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
    </main>
  );
}
