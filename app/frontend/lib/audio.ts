/**
 * 음성 입출력 — Nova 2 Sonic의 오디오 규격에 맞춘 캡처·재생 (N-2·N-3).
 *
 * 왜 `MediaRecorder`와 `new Audio()`를 쓰지 않는가:
 *
 * - **입력**: `MediaRecorder`는 `audio/webm;codecs=opus`를 만든다. Nova는 **raw LPCM**
 *   (16kHz·16bit·mono, base64, 32ms=1024바이트 프레임)만 받는다 — 호환되지 않는다.
 *   250ms 타임슬라이스도 Nova의 32ms 케이던스와 맞지 않는다.
 * - **출력**: Nova의 `audioOutput`은 **헤더가 없다**(N-1 실측: 앞 4바이트가 `RIFF`가
 *   아니라 PCM 샘플이었다). `new Blob([...], {type:"audio/wav"})`는 그것을 디코드하지
 *   못한다. 게다가 barge-in은 "이미 받았지만 아직 재생하지 않은 오디오를 버리는 것"이라
 *   **재생 큐를 직접 쥐고 있어야** 한다 — `new Audio()`로는 그 큐가 없다.
 *
 * 스텁 어댑터는 헤더가 유효한 WAV를 보내므로(`app/backend/app/audio_gateway/fixtures.py`)
 * 재생 경로는 둘을 모두 받는다 — 그래야 스텁 회귀와 실연동이 같은 코드를 지나간다.
 */

/** Nova 입력 규격. 리샘플은 `AudioContext({sampleRate})`로 브라우저에 맡긴다. */
export const SAMPLE_RATE_HZ = 16_000;
/** 32ms = 512샘플 = 1024바이트 (16kHz·16bit·mono). */
export const FRAME_SAMPLES = 512;
export const FRAME_BYTES = FRAME_SAMPLES * 2;

const PROCESSOR_NAME = "pcm-capture";

/**
 * AudioWorklet 프로세서 소스. 별도 파일(`public/`)로 서빙하지 않고 Blob URL로 등록한다 —
 * 자산과 이 코드가 갈라지지 않게 하려는 것이다.
 *
 * 16bit 변환에 `DataView.setInt16(..., true)`를 쓰는 이유는 **리틀엔디언을 명시**하기
 * 위해서다. `Int16Array`의 바이트 순서는 플랫폼에 따르므로, Nova가 요구하는 LE를
 * 플랫폼 가정에 맡기지 않는다.
 */
const CAPTURE_WORKLET_SOURCE = `
class PcmCaptureProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.frame = new ArrayBuffer(${FRAME_BYTES});
    this.view = new DataView(this.frame);
    this.filled = 0;
  }

  process(inputs) {
    const channel = inputs[0] && inputs[0][0];
    if (!channel) return true;
    for (let i = 0; i < channel.length; i += 1) {
      let sample = channel[i];
      if (sample > 1) sample = 1;
      else if (sample < -1) sample = -1;
      this.view.setInt16(this.filled * 2, Math.round(sample * 32767), true);
      this.filled += 1;
      if (this.filled === ${FRAME_SAMPLES}) {
        this.port.postMessage(this.frame.slice(0));
        this.filled = 0;
      }
    }
    return true;
  }
}
registerProcessor("${PROCESSOR_NAME}", PcmCaptureProcessor);
`;

export function bytesToBase64(bytes: Uint8Array): string {
  let binary = "";
  for (let i = 0; i < bytes.length; i += 1) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

export function base64ToBytes(base64Data: string): Uint8Array {
  const binary = atob(base64Data);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

function readChunkId(bytes: Uint8Array, offset: number): string {
  return String.fromCharCode(bytes[offset], bytes[offset + 1], bytes[offset + 2], bytes[offset + 3]);
}

/**
 * 재생할 raw LPCM만 남긴다. `RIFF/WAVE`면 `data` 청크를 찾아 그 본문만 돌려주고,
 * 아니면(= Nova 출력) 그대로 돌려준다. 청크를 순회하는 이유는 헤더 길이를 44바이트로
 * 가정할 수 없기 때문이다.
 */
export function pcmFromAudioFrame(bytes: Uint8Array): Uint8Array {
  if (bytes.byteLength < 12 || readChunkId(bytes, 0) !== "RIFF" || readChunkId(bytes, 8) !== "WAVE") {
    return bytes;
  }
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  let offset = 12;
  while (offset + 8 <= bytes.byteLength) {
    const size = view.getUint32(offset + 4, true);
    const body = offset + 8;
    if (readChunkId(bytes, offset) === "data") {
      return bytes.subarray(body, Math.min(body + size, bytes.byteLength));
    }
    offset = body + size + (size % 2); // 청크는 짝수 경계에 맞춰 패딩된다
  }
  return bytes;
}

/**
 * 마이크 캡처 + 응답 재생을 한 `AudioContext` 위에서 다룬다.
 *
 * 재생을 "큐"라고 부르는 것은 스케줄된 `AudioBufferSourceNode` 집합이다. `INTERRUPTED`
 * 통보를 받으면 그 노드들을 전부 `stop()`한다 — 아직 재생 시각이 오지 않은 것은 아예
 * 소리가 나지 않고, 재생 중인 것은 즉시 멈춘다. 그것이 barge-in이다.
 */
export class VoiceIo {
  private nextStartTime = 0;
  private readonly scheduled = new Set<AudioBufferSourceNode>();

  private constructor(
    private readonly context: AudioContext,
    private readonly microphone: MediaStreamAudioSourceNode,
    private readonly capture: AudioWorkletNode,
    private readonly silentSink: GainNode,
  ) {}

  static async start(
    stream: MediaStream,
    onFrame: (frame: Uint8Array) => void,
  ): Promise<VoiceIo> {
    // 16kHz 컨텍스트를 요청하면 마이크 리샘플과 응답 재생 모두 브라우저가 처리한다.
    const context = new AudioContext({ sampleRate: SAMPLE_RATE_HZ });
    if (!context.audioWorklet) {
      await context.close();
      throw new Error("이 브라우저에서는 AudioWorklet을 쓸 수 없습니다");
    }
    const moduleUrl = URL.createObjectURL(
      new Blob([CAPTURE_WORKLET_SOURCE], { type: "text/javascript" }),
    );
    try {
      await context.audioWorklet.addModule(moduleUrl);
    } finally {
      URL.revokeObjectURL(moduleUrl);
    }
    // 사용자 제스처 뒤에 불리므로 여기서 resume이 통한다.
    await context.resume();

    const capture = new AudioWorkletNode(context, PROCESSOR_NAME);
    capture.port.onmessage = (message: MessageEvent<unknown>) => {
      if (message.data instanceof ArrayBuffer) {
        onFrame(new Uint8Array(message.data));
      }
    };
    const microphone = context.createMediaStreamSource(stream);
    microphone.connect(capture);
    // 노드가 destination까지 이어져 있지 않으면 `process()`가 불리지 않는다. gain 0으로
    // 연결해 자기 목소리가 스피커로 되돌아오지 않게 하면서 그래프만 잇는다.
    const silentSink = context.createGain();
    silentSink.gain.value = 0;
    capture.connect(silentSink);
    silentSink.connect(context.destination);

    return new VoiceIo(context, microphone, capture, silentSink);
  }

  /** 응답 오디오 한 조각을 재생 큐 끝에 붙인다. */
  enqueueAudio(frame: Uint8Array): void {
    const pcm = pcmFromAudioFrame(frame);
    const sampleCount = pcm.byteLength >> 1;
    if (sampleCount === 0) return;
    const view = new DataView(pcm.buffer, pcm.byteOffset, pcm.byteLength);
    const buffer = this.context.createBuffer(1, sampleCount, SAMPLE_RATE_HZ);
    const channel = buffer.getChannelData(0);
    for (let i = 0; i < sampleCount; i += 1) {
      // 리틀엔디언 16bit → -1..1 부동소수. 32768로 나눠 -1 아래로 내려가지 않게 한다.
      channel[i] = view.getInt16(i * 2, true) / 32768;
    }
    const source = this.context.createBufferSource();
    source.buffer = buffer;
    source.connect(this.context.destination);
    const startAt = Math.max(this.context.currentTime, this.nextStartTime);
    source.onended = () => {
      this.scheduled.delete(source);
    };
    this.scheduled.add(source);
    source.start(startAt);
    this.nextStartTime = startAt + buffer.duration;
  }

  /** barge-in — 아직 재생하지 않은 오디오를 버린다. */
  dropQueuedAudio(): void {
    for (const source of this.scheduled) {
      source.onended = null;
      try {
        source.stop();
      } catch {
        // 이미 끝난 노드를 멈추는 것은 오류가 아니다.
      }
    }
    this.scheduled.clear();
    this.nextStartTime = 0;
  }

  async close(): Promise<void> {
    this.dropQueuedAudio();
    this.capture.port.onmessage = null;
    this.capture.disconnect();
    this.microphone.disconnect();
    this.silentSink.disconnect();
    await this.context.close();
  }
}
