"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { fetchVideos, removeVideo, storeVideo, type VideoSummary } from "@/lib/api";
import { fetchVideoMeta, thumbnailUrl, watchUrl } from "@/lib/youtube";

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

// ⚠️ 라벨과 레이아웃 값을 기존 화면들에 맞춘다 — `results`·`history` 가 같은 목적지에
// 같은 라벨을 쓰고, 폭·여백은 네 화면이 이미 공유하는 값이다. 새 값을 정하면 같은 앱의
// 화면 폭이 두 벌이 된다.
const HOME_LINK_LABEL = "← 학습 시작 화면으로";
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

// 갱신을 동시에 몇 건까지 도나. 브라우저의 호스트당 연결 상한과 같은 자리에 둔다.
const REFRESH_CONCURRENCY = 6;

const PAGE_STYLE = {
  maxWidth: 640,
  margin: "0 auto",
  padding: "2rem",
  fontFamily: "sans-serif",
} as const;

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
  // ⛔ **화면 상태를 건드리지 않고 「갱신한 것이 있는가」만 돌려준다** — 목록을 다시 읽는 자리는
  //    `reload` 하나여야 한다. 여기서 또 읽으면 그 코드가 두 벌이 된다.
  // ⚠️ 보통 0건이지만 **영상을 몰아 담고 한 달 뒤에 오면 전부 한꺼번에 stale** 이 된다. 그때
  //    직렬로 돌면 건당 약 170 ms(oEmbed 왕복 실측)가 쌓이므로 **조각 병렬**로 돈다.
  // ⚠️ 상한을 두는 이유 둘: 브라우저가 호스트당 연결을 6개 안으로 이미 제한하므로 그 위로는 얻는
  //    것이 없고, 무제한이면 우리 백엔드 커넥션 풀을 한 번에 채운다.
  const refreshStale = useCallback(
    async (rows: VideoSummary[], alive: () => boolean): Promise<boolean> => {
      const stale = rows.filter((row) => row.metadata_stale);
      for (let at = 0; at < stale.length; at += REFRESH_CONCURRENCY) {
        if (!alive()) {
          return false;
        }
        await Promise.all(
          stale.slice(at, at + REFRESH_CONCURRENCY).map(async (row) => {
            const url = watchUrl(row.youtube_id);
            const meta = await fetchVideoMeta(url);
            if (meta) {
              await storeVideo({ url, title: meta.title, channelName: meta.channelName });
            }
          }),
        );
      }
      return stale.length > 0;
    },
    [],
  );

  useEffect(() => {
    // ⚠️ 화면을 떠난 뒤 `setVideos` 를 부르지 않도록 살아 있는지 확인한다 — 갱신 루프가 길어질 수
    //    있고(위 주석), 그 사이에 사용자가 영상 화면으로 들어갈 수 있다.
    let alive = true;
    void (async () => {
      const rows = await reload();
      if (rows && (await refreshStale(rows, () => alive)) && alive) {
        await reload();
      }
    })();
    return () => {
      alive = false;
    };
  }, [reload, refreshStale]);

  // ⛔ `setBusy(true)`/`setBusy(false)` 짝을 손으로 맞추지 않는다 — 쓰기 경로를 새로 붙일 때
  //    `finally` 를 빠뜨리면 화면이 영구히 잠긴다.
  const runBusy = useCallback(async <T,>(fn: () => Promise<T>): Promise<T> => {
    setBusy(true);
    try {
      return await fn();
    } finally {
      setBusy(false);
    }
  }, []);

  const check = useCallback(async () => {
    const trimmed = url.trim();
    if (!trimmed) {
      return;
    }
    setNotice(null);
    const meta = await runBusy(() => fetchVideoMeta(trimmed));
    if (!meta) {
      // ⚠️ oEmbed 는 없는 영상에 **400** 을 준다 — 「링크가 아니다」와 「영상이 없다」를 가르지
      //    않으므로 한 문구로 옮긴다(설계서 §7).
      setNotice(NOT_FOUND_NOTICE);
      return;
    }
    setPreview({ url: trimmed, title: meta.title, channelName: meta.channelName });
  }, [url, runBusy]);

  const store = useCallback(async () => {
    if (!preview) {
      return;
    }
    const result = await runBusy(() =>
      storeVideo({
        url: preview.url,
        title: preview.title,
        channelName: preview.channelName,
      }),
    );
    if (!result.ok) {
      setNotice(result.reason === "refused" ? NOT_FOUND_NOTICE : UNAVAILABLE_NOTICE);
      return;
    }
    setNotice(result.value.created ? STORED_NOTICE : ALREADY_STORED_NOTICE);
    setPreview(null);
    setUrl("");
    await reload();
  }, [preview, reload, runBusy]);

  const remove = useCallback(
    async (videoId: string) => {
      if (!window.confirm(REMOVE_CONFIRM)) {
        return;
      }
      const result = await runBusy(() => removeVideo(videoId));
      if (!result.ok) {
        setNotice(UNAVAILABLE_NOTICE);
        return;
      }
      setNotice(null);
      await reload();
    },
    [reload, runBusy],
  );

  return (
    <main style={PAGE_STYLE}>
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
