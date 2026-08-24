"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { SessionSocket, type ServerEvent, type Speaker } from "@/lib/ws";

type ScreenState = "idle" | "connecting" | "active" | "ending" | "failed";

interface TranscriptLine {
  id: number;
  speaker: Speaker;
  text: string;
}

const AUDIO_MIME_CANDIDATES = [
  "audio/webm;codecs=opus",
  "audio/webm",
  "audio/ogg;codecs=opus",
  "audio/ogg",
];

const RECORDER_TIMESLICE_MS = 250;

function pickRecorderMimeType(): string | undefined {
  if (typeof MediaRecorder === "undefined") return undefined;
  return AUDIO_MIME_CANDIDATES.find((candidate) => MediaRecorder.isTypeSupported(candidate));
}

function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      const result = reader.result;
      if (typeof result !== "string") {
        reject(new Error("오디오 조각을 읽지 못했습니다"));
        return;
      }
      // data:<mime>;base64,<payload> 형태에서 payload만 취한다.
      resolve(result.slice(result.indexOf(",") + 1));
    };
    reader.onerror = () => reject(reader.error ?? new Error("오디오 조각을 읽지 못했습니다"));
    reader.readAsDataURL(blob);
  });
}

/** 서버 `audio` 프레임(base64 WAV)을 디코딩해 재생한다. 실패해도 세션은 계속된다. */
function playAudioFrame(base64Data: string): void {
  try {
    const binary = atob(base64Data);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i += 1) {
      bytes[i] = binary.charCodeAt(i);
    }
    const url = URL.createObjectURL(new Blob([bytes], { type: "audio/wav" }));
    const audio = new Audio(url);
    audio.addEventListener("ended", () => URL.revokeObjectURL(url));
    void audio.play().catch(() => URL.revokeObjectURL(url));
  } catch {
    // 디코딩 실패는 세션 진행을 막지 않는다 — 전사문 경로가 더 중요하다.
  }
}

export default function SessionPage() {
  const router = useRouter();
  const [state, setState] = useState<ScreenState>("idle");
  const [failureReason, setFailureReason] = useState<string | null>(null);
  const [lines, setLines] = useState<TranscriptLine[]>([]);
  const [partialLine, setPartialLine] = useState<TranscriptLine | null>(null);

  const socketRef = useRef<SessionSocket | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const sessionIdRef = useRef<string | null>(null);
  const terminalHandledRef = useRef(false);
  const nextLineIdRef = useRef(0);

  const stopMedia = useCallback(() => {
    if (recorderRef.current && recorderRef.current.state !== "inactive") {
      recorderRef.current.stop();
    }
    recorderRef.current = null;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  }, []);

  const goToResults = useCallback(
    (sessionId: string) => {
      stopMedia();
      router.push(`/results/${sessionId}`);
    },
    [router, stopMedia],
  );

  const handleServerEvent = useCallback(
    (event: ServerEvent) => {
      switch (event.type) {
        case "session_started":
          sessionIdRef.current = event.session_id;
          break;
        case "partial":
          setPartialLine({ id: -1, speaker: event.speaker, text: event.text });
          break;
        case "final":
          setPartialLine(null);
          nextLineIdRef.current += 1;
          setLines((prev) => [
            ...prev,
            { id: nextLineIdRef.current, speaker: event.speaker, text: event.text },
          ]);
          break;
        case "audio":
          playAudioFrame(event.data);
          break;
        case "session_failed":
          if (terminalHandledRef.current) return;
          terminalHandledRef.current = true;
          stopMedia();
          setFailureReason(event.reason);
          setState("failed");
          break;
        case "session_ended":
          if (terminalHandledRef.current) return;
          terminalHandledRef.current = true;
          goToResults(event.session_id || sessionIdRef.current || "");
          break;
      }
    },
    [goToResults, stopMedia],
  );

  const startSession = useCallback(async () => {
    setFailureReason(null);
    setLines([]);
    setPartialLine(null);
    terminalHandledRef.current = false;
    sessionIdRef.current = null;
    setState("connecting");

    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      setFailureReason("microphone_permission_denied");
      setState("failed");
      return;
    }
    streamRef.current = stream;

    const socket = new SessionSocket({
      onEvent: handleServerEvent,
      onClose: () => {
        if (terminalHandledRef.current) return;
        terminalHandledRef.current = true;
        stopMedia();
        const sessionId = sessionIdRef.current;
        if (sessionId) {
          goToResults(sessionId);
        } else {
          setFailureReason("connection_lost");
          setState("failed");
        }
      },
    });
    socketRef.current = socket;

    const mimeType = pickRecorderMimeType();
    const recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
    recorder.ondataavailable = (chunk: BlobEvent) => {
      if (chunk.data.size === 0) return;
      void blobToBase64(chunk.data).then((base64Data) => {
        socketRef.current?.sendAudio(base64Data);
      });
    };
    recorderRef.current = recorder;
    recorder.start(RECORDER_TIMESLICE_MS);

    setState("active");
  }, [goToResults, handleServerEvent, stopMedia]);

  const endSession = useCallback(() => {
    setState("ending");
    socketRef.current?.endSession();
  }, []);

  // 언마운트 시 마이크·소켓 자원을 반드시 정리한다.
  useEffect(() => {
    return () => {
      stopMedia();
      socketRef.current?.close();
    };
  }, [stopMedia]);

  return (
    <main style={{ maxWidth: 640, margin: "0 auto", padding: "2rem", fontFamily: "sans-serif" }}>
      <h1>OhMyEnglish — 학습 세션</h1>

      {state === "idle" && (
        <button onClick={() => void startSession()} style={{ padding: "0.75rem 1.5rem" }}>
          학습 시작
        </button>
      )}

      {state === "connecting" && <p>마이크 권한을 요청하는 중입니다...</p>}

      {(state === "active" || state === "ending") && (
        <>
          <div
            style={{
              border: "1px solid #ccc",
              borderRadius: 8,
              padding: "1rem",
              minHeight: 220,
              marginTop: "1rem",
            }}
          >
            {lines.length === 0 && !partialLine && <p style={{ color: "#999" }}>대화를 기다리는 중...</p>}
            {lines.map((line) => (
              <p key={line.id} style={{ color: "#111", margin: "0.4rem 0" }}>
                <strong>{line.speaker === "agent" ? "질문" : "답변"}: </strong>
                {line.text}
              </p>
            ))}
            {partialLine && (
              <p style={{ color: "#999", margin: "0.4rem 0" }}>
                <strong>{partialLine.speaker === "agent" ? "질문" : "답변"}: </strong>
                {partialLine.text}
              </p>
            )}
          </div>
          <button
            onClick={endSession}
            disabled={state === "ending"}
            style={{ padding: "0.75rem 1.5rem", marginTop: "1rem" }}
          >
            {state === "ending" ? "종료 중..." : "학습 종료"}
          </button>
        </>
      )}

      {state === "failed" && (
        <div style={{ marginTop: "1rem" }}>
          <p>연결에 실패했습니다.</p>
          {failureReason && <p style={{ color: "#666" }}>사유: {failureReason}</p>}
          <button onClick={() => void startSession()} style={{ padding: "0.75rem 1.5rem" }}>
            다시 시도
          </button>
        </div>
      )}
    </main>
  );
}
