"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { VoiceIo, base64ToBytes, bytesToBase64 } from "@/lib/audio";
import { SessionSocket, type ServerEvent, type Speaker } from "@/lib/ws";

type ScreenState = "idle" | "connecting" | "active" | "ending" | "failed";

interface TranscriptLine {
  id: number;
  speaker: Speaker;
  text: string;
}

/**
 * 서버 `audio` 프레임을 재생 큐에 붙인다. 디코딩 실패는 세션 진행을 막지 않는다 —
 * 프레임 하나를 잃는 것이 대화를 끊는 것보다 낫고, 전사문 경로가 더 중요하다.
 */
function enqueueAudioFrame(voice: VoiceIo | null, base64Data: string): void {
  if (!voice) return;
  try {
    voice.enqueueAudio(base64ToBytes(base64Data));
  } catch {
    // 무시한다 (위 주석).
  }
}

export default function SessionPage() {
  const router = useRouter();
  const [state, setState] = useState<ScreenState>("idle");
  const [failureReason, setFailureReason] = useState<string | null>(null);
  const [lines, setLines] = useState<TranscriptLine[]>([]);
  const [partialLine, setPartialLine] = useState<TranscriptLine | null>(null);
  // Nova는 **사용자 부분 전사문을 주지 않는다** — 사용자 ASR은 `generationStage: FINAL`
  // 한 블록으로만 온다(N-1 실측). 그래서 부분 전사문 자리를 `userSpeechStart`~`End`
  // 구간의 "듣고 있어요"로 대체한다. 스텁 어댑터는 그 경계를 보내지 않으므로 스텁 모드의
  // 부분 전사문 거동(1·2차수 C2가 검증하는 회색→확정 전환)은 그대로 남는다.
  const [listening, setListening] = useState(false);

  const socketRef = useRef<SessionSocket | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const voiceRef = useRef<VoiceIo | null>(null);
  const sessionIdRef = useRef<string | null>(null);
  const terminalHandledRef = useRef(false);
  const nextLineIdRef = useRef(0);

  const stopMedia = useCallback(() => {
    const voice = voiceRef.current;
    voiceRef.current = null;
    void voice?.close();
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
          setListening(false);
          nextLineIdRef.current += 1;
          setLines((prev) => [
            ...prev,
            { id: nextLineIdRef.current, speaker: event.speaker, text: event.text },
          ]);
          break;
        case "speech_start":
          setListening(true);
          break;
        case "speech_end":
          setListening(false);
          break;
        case "audio":
          enqueueAudioFrame(voiceRef.current, event.data);
          break;
        case "interrupted":
          // barge-in — 이미 받았지만 아직 재생하지 않은 응답 오디오를 버린다.
          voiceRef.current?.dropQueuedAudio();
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
    setListening(false);
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

    // Nova는 raw LPCM(16kHz·16bit·mono, 32ms 프레임)만 받는다 — `MediaRecorder`의
    // webm/opus로는 붙일 수 없다. AudioWorklet으로 원시 PCM을 그대로 캡처해 보낸다.
    try {
      voiceRef.current = await VoiceIo.start(stream, (frame) => {
        socketRef.current?.sendAudio(bytesToBase64(frame));
      });
    } catch {
      // 캡처를 못 만들면 세션은 성립하지 않는다 — 조용히 무음 세션을 만들지 않고 알린다.
      terminalHandledRef.current = true;
      socket.close();
      stopMedia();
      setFailureReason("audio_capture_unavailable");
      setState("failed");
      return;
    }

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
            {lines.length === 0 && !partialLine && !listening && (
              <p style={{ color: "var(--foreground-muted)" }}>대화를 기다리는 중...</p>
            )}
            {/* 확정 전사문이 강조 대상이다 — 부분 전사문(muted)보다 배경 대비가 높아야
                AC U1의 위계가 성립한다. 색은 테마 토큰에서만 온다(globals.css). */}
            {lines.map((line) => (
              <p key={line.id} style={{ color: "var(--foreground)", margin: "0.4rem 0" }}>
                <strong>{line.speaker === "agent" ? "질문" : "답변"}: </strong>
                {line.text}
              </p>
            ))}
            {partialLine ? (
              <p style={{ color: "var(--foreground-muted)", margin: "0.4rem 0" }}>
                <strong>{partialLine.speaker === "agent" ? "질문" : "답변"}: </strong>
                {partialLine.text}
              </p>
            ) : (
              listening && (
                <p style={{ color: "var(--foreground-muted)", margin: "0.4rem 0" }}>
                  듣고 있어요...
                </p>
              )
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
          {failureReason && (
            <p style={{ color: "var(--foreground-muted)" }}>사유: {failureReason}</p>
          )}
          <button onClick={() => void startSession()} style={{ padding: "0.75rem 1.5rem" }}>
            다시 시도
          </button>
        </div>
      )}
    </main>
  );
}
