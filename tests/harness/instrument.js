/**
 * 브라우저 레그 계측 — `use_browser`의 `eval`에 이 파일 내용을 그대로 넣는다.
 *
 * **절차 정본은 `tests/harness/browser_leg.md`다.** 여기서 절차를 재서술하지 않는다.
 * 이 파일은 그 문서 §4가 요구하는 계약(반환값·대상 존재 단정·`window.__omy` 키)의 구현이고,
 * 계획서는 `docs/design/2026-09-05-frontend-test-agent-plan.md` §7-1·§7-4·§7-6이다.
 *
 * ## 낡은 판에서 무엇을 고쳤나 (§7-1)
 *
 * 원본은 `docs/ops/2026-08-26-test-harness.html` 「C계층」의 `<pre>` 블록이다. 그 판은
 * 2026-08-26에 옳았고 **그 뒤 앱이 두 번 리팩터되면서 낡았다.**
 *
 * 1. **`window.Audio` 계수를 버렸다.** `lib/audio.ts` 모듈 docstring 제목이 "왜 `MediaRecorder`와
 *    `new Audio()`를 쓰지 않는가"이고 재생은 `VoiceIo.enqueueAudio`가 한다 → 그 계수는 **항상 0**
 *    이고 거짓 FAIL을 낸다. 단정을 완화해 "고치면" 거짓 PASS로 뒤집힌다.
 * 2. ⚠️ **대체물은 `createBufferSource`가 아니라 `start`다.** `enqueueAudio`는 노드 **생성**과 재생
 *    **시작**을 별개 줄에서 부른다 — 생성만 세면 `start` 줄을 지워도 계수가 유지된다(소리는 나지
 *    않는데 통과한다). 2026-09-06 판별력 재설계(`TASK-29`)가 계수 지점을 옮겼다.
 * 3. **주석 "`MediaRecorder`는 실제로 인코딩한다"를 지웠다.** 캡처는 `AudioWorkletNode`다.
 *
 * ⚠️ **`WebSocket.prototype.send` 후킹은 낡은 판이 이미 옳게 하고 있었다.** 낡은 것은 스크립트가
 * 아니라 `browser_leg.md`의 A1-7 서술("계측이 `sendAudio` 호출을 계수")이었다. `sendAudio`를 세면
 * `ws.ts:SessionSocket.send`가 `readyState !== OPEN`에서 조용히 버린 경우까지 세어지지만, 이 후킹은
 * 실제 전송만 센다. **재설계가 A1-7에 더한 것은 계수 지점이 아니라 `end_session` 동반 계수**다
 * (계수 0이 "전송 없음"인지 "후킹 고장"인지 가른다).
 *
 * ## 설계 판단 2개 — 원본과 다르게 한 것
 *
 * * **동기 IIFE다.** 원본은 `(async () => {...})()`였고 그러면 반환값이 Promise라 §4-1의 "반환값이
 *   정확히 `'instrumented'`"를 하네스가 await하는지에 걸린다. **await 여부를 미결로 남기지 않기
 *   위해** 동기로 만들고 `ctx.resume()`은 기다리지 않는다.
 * * **`resume()`을 클릭 시점에 한 번 더 시도한다.** 자동재생 정책 때문에 사용자 제스처 밖의
 *   `resume()`은 실패할 수 있다. `getUserMedia`가 불리는 순간은 "학습 시작" 클릭 안이므로 **그 자리가
 *   제스처 안**이다. `ctx.state`를 `__omy.meta`에 남겨 suspend를 회차가 볼 수 있게 한다
 *   (`browser_leg.md` §11-3의 미결이 이 값으로 닫힌다).
 *
 * ## 후킹 대상의 위치를 추측하지 않는다
 *
 * `start`가 `AudioBufferSourceNode.prototype`에 있는지 `AudioScheduledSourceNode.prototype`에
 * 있는지는 **이 Chrome에서 실측할 일**이다(§11-2). 그래서 프로토타입 체인을 걸어 **소유자를 찾고
 * 그 이름을 `__omy.meta`에 적는다.** 찾지 못하면 throw한다 — 조용히 건너뛰면 계수가 0이 되고
 * **0은 "고장"과 구별되지 않는다**(§4-2).
 */
(() => {
  "use strict";

  // ── 0. 중복 주입 방어 ────────────────────────────────────────────────────────
  // 두 번 걸면 모든 계수가 두 배가 되고, 그 회차는 조용히 틀린 값을 낸다.
  if (window.__omy) {
    throw new Error(
      "instrument.js가 이미 걸려 있다 — 계수가 두 배가 된다. 페이지를 새로 로드하고 한 번만 걸어라."
    );
  }

  // ── 1. 후킹 대상 존재 단정 (§4-2) ───────────────────────────────────────────
  /** 프로토타입 체인을 걸어 그 이름의 **자기 프로퍼티**를 가진 생성자 이름을 찾는다. */
  const findOwner = (ctor, prop) => {
    for (let proto = ctor && ctor.prototype; proto; proto = Object.getPrototypeOf(proto)) {
      if (Object.prototype.hasOwnProperty.call(proto, prop)) {
        return {
          name: (proto.constructor && proto.constructor.name) || "(unknown)",
          proto,
          descriptor: Object.getOwnPropertyDescriptor(proto, prop),
        };
      }
    }
    return null;
  };

  const need = (value, message) => {
    if (!value) throw new Error(`계측 대상 부재: ${message}`);
    return value;
  };

  need(typeof WebSocket === "function", "WebSocket 전역이 없다");
  need(typeof AudioContext === "function", "AudioContext 전역이 없다");
  need(typeof AudioBufferSourceNode === "function", "AudioBufferSourceNode 전역이 없다");
  need(
    navigator.mediaDevices && typeof navigator.mediaDevices.getUserMedia === "function",
    "navigator.mediaDevices.getUserMedia 가 없다"
  );

  // `onmessage`는 **접근자 프로퍼티**다 — `get`/`set`이 없으면 감쌀 수 없다.
  const onmessageOwner = need(
    findOwner(WebSocket, "onmessage"),
    "WebSocket 체인에 onmessage 가 없다"
  );
  need(
    onmessageOwner.descriptor.get && onmessageOwner.descriptor.set,
    "onmessage 가 접근자가 아니다 — get/set 이 없으면 감쌀 수 없다"
  );

  // `send`와 `start`는 **메서드**다.
  const sendOwner = need(findOwner(WebSocket, "send"), "WebSocket 체인에 send 가 없다");
  need(typeof sendOwner.descriptor.value === "function", "send 가 함수가 아니다");

  const startOwner = need(
    findOwner(AudioBufferSourceNode, "start"),
    "AudioBufferSourceNode 체인에 start 가 없다 — 계수 지점을 잃었다"
  );
  need(typeof startOwner.descriptor.value === "function", "start 가 함수가 아니다");

  // ── 2. 상태 (§4-4의 키 계약) ────────────────────────────────────────────────
  const omy = {
    /** 서버 → 클라이언트 프레임 계수. 키가 곧 기대 키다(§4-4). */
    recv: { session_started: 0, partial: 0, final: 0, audio: 0, session_ended: 0, session_failed: 0 },
    /** 클라이언트 → 서버 **실제 전송** 계수를 `type`별로. `audio`와 `end_session`을 따로 담는다. */
    sent: { audio: 0, end_session: 0, unparsed: 0, other: 0 },
    /** 전송한 `audio` 프레임의 base64 길이 합 — 빈 `data`만 보낸 경우를 계수와 가른다. */
    sentAudioBytes: 0,
    /** `start` 호출 계수와 **인자 `when` 배열**(A1-4 대조 ②). */
    started: { count: 0, when: [] },
    /** `session_ended`/`session_failed` 도착 시점의 확정 줄 `textContent` 배열(A1-5 내용 단정). */
    finalLines: null,
    /** 진단용 — `final`마다 찍은 스냅샷. ⚠️ partial 줄이 섞일 수 있어 단정에 쓰지 않는다. */
    snapshots: [],
    /** `inject()`로 넣은 프레임 계수 — `recv`를 오염시키지 않기 위해 따로 센다. */
    injected: 0,
    /** 회차가 읽는 환경 사실. 값을 여기서 단정하지 않는다 — 기록만 한다. */
    meta: {
      hookedAt: new Date().toISOString(),
      onmessageOwner: onmessageOwner.name,
      sendOwner: sendOwner.name,
      /** ⚠️ §11-2가 물은 것 — 정답을 코드에 박지 않고 **찾아서 적는다**. */
      startOwner: startOwner.name,
      createBufferSourceOwner: (findOwner(AudioContext, "createBufferSource") || {}).name || null,
      audioContextState: null,
      resumeAttempts: 0,
      resumeErrors: [],
      appHandlerAttached: false,
    },
    /** 회차가 켜고 끄는 것. 기본은 소리 나는 톤이다. */
    config: {
      /** A1-7 음성 대조 후보 ② — 무음 스트림으로 바꿔 `sent.audio`가 0이 되는지 본다. */
      silentMic: false,
    },
  };
  window.__omy = omy;

  // ── 3. 마이크를 합성 스트림으로 대체 ────────────────────────────────────────
  // ⚠️ 여기서 AudioContext를 만들지만 `resume()`을 기다리지 않는다(위 설계 판단).
  const ctx = new AudioContext();
  omy.meta.audioContextState = ctx.state;

  const tryResume = () => {
    omy.meta.resumeAttempts += 1;
    try {
      const result = ctx.resume();
      if (result && typeof result.catch === "function") {
        result.catch((error) => omy.meta.resumeErrors.push(String(error)));
      }
    } catch (error) {
      omy.meta.resumeErrors.push(String(error));
    }
    omy.meta.audioContextState = ctx.state;
  };
  tryResume();

  const destination = ctx.createMediaStreamDestination();
  // 톤(220Hz)과 무음을 **같은 그래프**로 만든다 — gain만 0으로 내린다. 스트림 자체는 늘 살아
  // 있으므로 `getUserMedia` 성공/실패 경로가 바뀌지 않고, 바뀌는 것은 **실린 소리뿐**이다.
  // 그래야 A1-7의 무음 대조가 "권한 거동"이 아니라 "전송 내용"을 가른다.
  const oscillator = ctx.createOscillator();
  oscillator.frequency.value = 220;
  const micGain = ctx.createGain();
  micGain.gain.value = 1;
  oscillator.connect(micGain);
  micGain.connect(destination);
  oscillator.start();

  navigator.mediaDevices.getUserMedia = async () => {
    // 이 자리는 "학습 시작" 클릭 **안**이라 사용자 제스처 안이다 — 자동재생 정책이 여기서 풀린다.
    tryResume();
    micGain.gain.value = omy.config.silentMic ? 0 : 1;
    return destination.stream;
  };

  // ── 4. 확정 줄 스냅샷 ───────────────────────────────────────────────────────
  // 대상 요소는 **색이 아니라 접두 구조로** 고른다(§7-5 N-1 — 색으로 고르면 재려는 값이 선별
  // 기준이 되어 자기순환이다).
  const LINE_PREFIXES = ["질문: ", "답변: "];
  const prefixedLines = () =>
    Array.from(document.querySelectorAll("p")).filter((p) => {
      const strong = p.querySelector("strong");
      return !!strong && LINE_PREFIXES.indexOf(strong.textContent) !== -1;
    });

  const snapshotNow = () => prefixedLines().map((p) => p.textContent);
  omy.snapshotNow = snapshotNow;

  // ── 5. 수신 프레임 계수 + 앱 핸들러 포획 ────────────────────────────────────
  // 앱은 `socket.onmessage = fn` 으로 붙는다(`lib/ws.ts:SessionSocket`). 그 `fn`을 잡아 두면
  // 주입(§7-6)이 **같은 경로로** 프레임을 넣을 수 있다.
  let appHandler = null;
  const nativeOnmessage = onmessageOwner.descriptor;

  Object.defineProperty(onmessageOwner.proto, "onmessage", {
    configurable: true,
    enumerable: nativeOnmessage.enumerable,
    get() {
      return nativeOnmessage.get.call(this);
    },
    set(fn) {
      appHandler = fn;
      omy.meta.appHandlerAttached = true;
      nativeOnmessage.set.call(this, (event) => {
        try {
          const frame = JSON.parse(event.data);
          if (frame && Object.prototype.hasOwnProperty.call(omy.recv, frame.type)) {
            omy.recv[frame.type] += 1;
          }
          // ⚠️ **여기서 동기로 찍는다.** `session_ended`가 오는 시점에는 확정 줄 6개가 이미
          // 렌더돼 있고 partial 줄은 `setPartialLine(null)`로 사라져 있다. 앱 핸들러가
          // `router.push`로 언마운트하기 **전**이라 이 스냅샷만이 A1-5의 단정 대상이 된다.
          if (frame && (frame.type === "session_ended" || frame.type === "session_failed")) {
            omy.finalLines = snapshotNow();
          } else if (frame && frame.type === "final") {
            // 진단용 — 렌더 후를 보려면 프레임을 두 번 넘긴다. 단정에 쓰지 않는다(partial 혼입).
            requestAnimationFrame(() =>
              requestAnimationFrame(() => omy.snapshots.push(snapshotNow()))
            );
          }
        } catch {
          // 해석할 수 없는 프레임은 세지 않는다 — 앱도 같은 자리에서 무시한다(`ws.ts`).
        }
        return fn(event);
      });
    },
  });

  // ── 6. 실제 전송 계수 (A1-7의 효과 지점) ────────────────────────────────────
  const nativeSend = sendOwner.descriptor.value;
  sendOwner.proto.send = function (data) {
    try {
      const payload = JSON.parse(data);
      const type = payload && payload.type;
      if (type === "audio") {
        omy.sent.audio += 1;
        omy.sentAudioBytes += (payload.data || "").length;
      } else if (type === "end_session") {
        omy.sent.end_session += 1;
      } else {
        omy.sent.other += 1;
      }
    } catch {
      omy.sent.unparsed += 1;
    }
    return nativeSend.call(this, data);
  };

  // ── 7. 재생 시작 계수 (A1-4의 효과 지점) ────────────────────────────────────
  const nativeStart = startOwner.descriptor.value;
  startOwner.proto.start = function (when) {
    omy.started.count += 1;
    omy.started.when.push(typeof when === "number" ? when : 0);
    return nativeStart.apply(this, arguments);
  };

  // ── 8. 프레임 주입 (§7-6 · C2·C5) ───────────────────────────────────────────
  // ⚠️ **이 함수의 검증은 `TASK-20`(T5a) 소유다.** 여기서 되는 것으로 단정하지 않는다.
  // 앱 핸들러를 **직접** 부르므로 `recv`를 오염시키지 않는다 — 서버가 보낸 것과 우리가 넣은
  // 것이 같은 계수에 섞이면 A1-* 단정이 무의미해진다.
  omy.inject = (frame) => {
    if (!appHandler) {
      throw new Error(
        "앱의 onmessage 핸들러가 아직 붙지 않았다 — 세션을 시작한 뒤에 주입해라(계측이 먼저 걸려야 한다)."
      );
    }
    omy.injected += 1;
    appHandler({ data: JSON.stringify(frame) });
    return omy.injected;
  };

  // ── 9. 색 토큰 유도 probe (§7-6 N-2) ───────────────────────────────────────
  // ⚠️ `getPropertyValue('--foreground-muted')`를 직접 비교하지 않는다 — 그쪽은 `#595959` 형태로
  // 측정 대상의 `rgb(89, 89, 89)`와 문자열이 다르다. probe를 거치면 **같은 엔진이 같은 표현으로**
  // 정규화해 준다. 그래서 단정이 모드 무관해진다.
  omy.probeColor = (token) => {
    const probe = document.createElement("span");
    probe.style.color = `var(${token})`;
    probe.style.position = "absolute";
    probe.style.opacity = "0";
    document.body.appendChild(probe);
    try {
      return getComputedStyle(probe).color;
    } finally {
      probe.remove();
    }
  };

  return "instrumented";
})();
