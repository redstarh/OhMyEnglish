"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  fetchVideos,
  removeVideo,
  storeVideo,
  type VideoSummary,
  type WriteFailure,
} from "@/lib/api";
import { fetchVideoMeta, thumbnailUrl } from "@/lib/youtube";

/**
 * 영상 목록 (`TASK-168` · 스토리보드 S2).
 *
 * 설계: `docs/design/2026-09-18-video-learning-design.md` §5 ·
 * `docs/design/2026-09-18-video-learning-storyboard.md` §4.
 *
 * ⛔ **검색을 두지 않는다** — 사용자가 링크를 붙여넣는 것이 MVP 의 유일한 담기 경로다. 검색을 넣으면
 * API 키·쿼터·`search.list` 일일 100회 제한이 함께 들어온다(스토리보드 §6).
 *
 * ⚠️ **문체를 섞지 않는다** — 이 앱의 화면 문구는 `~어요`·`~습니다` 다(`results` 화면의 주석이
 * 그 규약을 이미 적었다).
 */

const HOME_LINK_LABEL = "← 대시보드";
const HEADING = "영상으로 배우기";
const LEAD =
  "YouTube 링크를 붙여넣어 영상을 담고, 안 들리는 구간을 받아 적어 쉐도잉 연습에 쓸 수 있어요.";
const EMPTY_NOTICE = "아직 담아 둔 영상이 없어요. 아래에 YouTube 링크를 붙여넣어 보세요.";
const LIST_FAILED_NOTICE = "영상 목록을 불러오지 못했어요. 잠시 뒤 다시 시도해 주세요.";
const URL_PLACEHOLDER = "https://www.youtube.com/watch?v=...";
const CHECK_LABEL = "확인";
const STORE_LABEL = "담기";
const CANCEL_LABEL = "취소";
const REMOVE_LABEL = "지우기";

// 설계서 §7 의 문구 표 — ⛔ 화면이 소유한다. HTTP 상태 코드를 사용자에게 보이지 않는다.
const NOT_FOUND_NOTICE = "이 링크에서 영상을 찾지 못했어요.";
const UNAVAILABLE_NOTICE = "지금 확인할 수 없어요. 잠시 뒤 다시 시도해 주세요.";
const ALREADY_STORED_NOTICE = "이미 담아 둔 영상이에요. 정보를 새로 받아 왔어요.";
const STORED_NOTICE = "담았어요.";
const REMOVE_CONFIRM = "이 영상을 목록에서 지울까요? 담아 둔 문장은 그대로 남아요.";

function noticeFor(reason: WriteFailure): string {
  return reason === "refused" ? NOT_FOUND_NOTICE : UNAVAILABLE_NOTICE;
}

interface Preview {
  url: string;
  title: string;
  channelName: string;
}

export default function VideosPage() {
  const [videos, setVideos] = useState<VideoSummary[] | null>(null);
  const [loadFailed, setLoadFailed] = useState(false);
  const [url, setUrl] = useState("");
  const [preview, setPreview] = useState<Preview | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const reload = useCallback(async () => {
    const rows = await fetchVideos();
    if (rows === null) {
      setLoadFailed(true);
      return;
    }
    setLoadFailed(false);
    setVideos(rows);
    return rows;
  }, []);

  // 담은 지 30일이 지난 메타데이터를 조용히 새로 받는다 (설계서 §1 질문 2).
  // ⛔ **사용자에게 알리지 않는다** — 정책을 지키기 위한 내부 동작이고 학습과 무관하다. 실패해도
  //    넘어간다: 낡은 제목이 보이는 것이 목록이 깨지는 것보다 낫다.
  // ⚠️ 보통 0건이다. 담아 둔 영상 전부를 매번 다시 받지 않는 이유가 `metadata_stale` 이다.
  const refreshStale = useCallback(async (rows: VideoSummary[]) => {
    const stale = rows.filter((row) => row.metadata_stale);
    if (stale.length === 0) {
      return;
    }
    for (const row of stale) {
      const watchUrl = `https://www.youtube.com/watch?v=${row.youtube_id}`;
      const meta = await fetchVideoMeta(watchUrl);
      if (meta) {
        await storeVideo({ url: watchUrl, title: meta.title, channelName: meta.channelName });
      }
    }
    const rows2 = await fetchVideos();
    if (rows2 !== null) {
      setVideos(rows2);
    }
  }, []);

  useEffect(() => {
    void (async () => {
      const rows = await reload();
      if (rows) {
        await refreshStale(rows);
      }
    })();
  }, [reload, refreshStale]);

  const check = useCallback(async () => {
    const trimmed = url.trim();
    if (!trimmed) {
      return;
    }
    setBusy(true);
    setNotice(null);
    const meta = await fetchVideoMeta(trimmed);
    setBusy(false);
    if (!meta) {
      // ⚠️ oEmbed 는 없는 영상에 **400** 을 준다 — 「링크가 아니다」와 「영상이 없다」를 가르지
      //    않으므로 한 문구로 옮긴다(설계서 §7).
      setNotice(NOT_FOUND_NOTICE);
      return;
    }
    setPreview({ url: trimmed, title: meta.title, channelName: meta.channelName });
  }, [url]);

  const store = useCallback(async () => {
    if (!preview) {
      return;
    }
    setBusy(true);
    const result = await storeVideo({
      url: preview.url,
      title: preview.title,
      channelName: preview.channelName,
    });
    setBusy(false);
    if (!result.ok) {
      setNotice(noticeFor(result.reason));
      return;
    }
    setNotice(result.value.created ? STORED_NOTICE : ALREADY_STORED_NOTICE);
    setPreview(null);
    setUrl("");
    await reload();
  }, [preview, reload]);

  const remove = useCallback(
    async (videoId: string) => {
      if (!window.confirm(REMOVE_CONFIRM)) {
        return;
      }
      setBusy(true);
      const result = await removeVideo(videoId);
      setBusy(false);
      if (!result.ok) {
        setNotice(UNAVAILABLE_NOTICE);
        return;
      }
      setNotice(null);
      await reload();
    },
    [reload],
  );

  return (
    <main style={{ padding: "2rem", maxWidth: "48rem", margin: "0 auto" }}>
      <Link href="/">{HOME_LINK_LABEL}</Link>
      <h1>{HEADING}</h1>
      <p>{LEAD}</p>

      <section style={{ marginBottom: "2rem" }}>
        <label htmlFor="video-url">YouTube 링크</label>
        <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.25rem" }}>
          <input
            id="video-url"
            value={url}
            placeholder={URL_PLACEHOLDER}
            onChange={(event) => setUrl(event.target.value)}
            style={{ flex: 1 }}
          />
          <button type="button" onClick={() => void check()} disabled={busy || !url.trim()}>
            {CHECK_LABEL}
          </button>
        </div>

        {preview ? (
          <div style={{ marginTop: "0.75rem" }}>
            <p>
              <strong>{preview.title}</strong>
              <br />
              {preview.channelName}
            </p>
            <button type="button" onClick={() => void store()} disabled={busy}>
              {STORE_LABEL}
            </button>{" "}
            <button type="button" onClick={() => setPreview(null)} disabled={busy}>
              {CANCEL_LABEL}
            </button>
          </div>
        ) : null}

        {notice ? <p role="status">{notice}</p> : null}
      </section>

      {loadFailed ? <p role="alert">{LIST_FAILED_NOTICE}</p> : null}

      {videos !== null && videos.length === 0 ? <p>{EMPTY_NOTICE}</p> : null}

      <ul style={{ listStyle: "none", padding: 0 }}>
        {(videos ?? []).map((video) => (
          <li key={video.id} style={{ display: "flex", gap: "1rem", marginBottom: "1rem" }}>
            {/* eslint-disable-next-line @next/next/no-img-element -- 외부 도메인 썸네일이고
                크기가 고정이라 next/image 의 최적화가 값을 주지 않는다. 실패하면 대체 표시로
                바꾼다(썸네일 URL 이 문서화된 계약이 아니라 그 대비가 필요하다 — 설계서 §2). */}
            <img
              src={thumbnailUrl(video.youtube_id)}
              alt=""
              width={160}
              height={90}
              onError={(event) => {
                event.currentTarget.style.visibility = "hidden";
              }}
            />
            <div style={{ flex: 1 }}>
              <Link href={`/videos/${video.id}`}>{video.title}</Link>
              <p style={{ margin: "0.25rem 0" }}>
                {video.channel_name} · 담은 문장 {video.phrase_count}개
              </p>
              <button type="button" onClick={() => void remove(video.id)} disabled={busy}>
                {REMOVE_LABEL}
              </button>
            </div>
          </li>
        ))}
      </ul>
    </main>
  );
}
