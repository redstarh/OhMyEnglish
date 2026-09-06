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
 * * **동기 IIFE다.** 원본은 `(async () => {...})()`였다.
 *   ⚠️ **처음 적은 근거는 거짓이었다 — 2026-09-06 T5a에서 실측으로 뒤집혔다.** 그 근거는
 *   "async면 반환값이 Promise라 §4-1의 반환값 검사가 하네스의 await 여부에 걸린다"였는데,
 *   **`use_browser`의 `eval`은 promise를 await한다**(팀리드 직접 측정: 250ms sleep이
 *   `elapsed: 254`로 돌아왔다 — T5a 에이전트도 같은 값을 봤다). 즉 그 미결은 존재하지 않았다.
 *   **결정은 유지한다** — 동기가 더 단순하고, 반환값이 곧 문자열이라 하네스 동작에 의존하지
 *   않는다. 바뀐 것은 근거이고, **거짓 근거를 남기면 다음 세션이 그것을 믿고 판단한다.**
 *   `ctx.resume()`은 기다리지 않는다(아래).
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
    /** 클라이언트 → 서버 **실제 전송** 계수를 `type`별로. `audio`와 `end_session`을 따로 담는다.
     *
     * ⚠️ **`foreign`은 앱 소켓이 아닌 전송이다** — T5a 실측: `sent.other = 1`의 정체가
     * `ws://localhost:3000/_next/hmr?...`(Next dev HMR)였다. 전역 프로토타입을 감싸므로 앱과
     * 무관한 소켓이 섞이고, 그러면 `other`·`unparsed`가 앱 신호가 아니게 된다. URL로 가른다.
     */
    sent: { audio: 0, end_session: 0, unparsed: 0, other: 0, foreign: 0 },
    /** 전송한 `audio` 프레임의 base64 길이 합 — 빈 `data`를 보낸 경우를 가른다. */
    sentAudioBytes: 0,
    /**
     * 전송한 `audio` 프레임 중 **PCM에 0이 아닌 샘플이 하나라도 있는** 프레임 수.
     *
     * ⚠️ **`sentAudioBytes`만으로는 무음과 유음을 가를 수 없다** — T5a·T2 실측: 무음·유음 모두
     * 프레임 **146**건 · 바이트 **199,728**로 완전히 같았다. `lib/audio.ts`의 캡처 워클렛
     * `process()`가 **진폭과 무관하게** 512샘플마다 `postMessage`하기 때문이다(무음 게이트 없음).
     * **다른 것은 PCM 내용뿐이므로 그것을 세야** A1-7의 무음 대조가 성립한다.
     */
    sentAudioNonZeroFrames: 0,
    /**
     * `start` 호출 기록. `count`·`when`은 그대로 두고 **`calls`가 프레임 태깅을 담는다**.
     *
     * ⚠️ **태깅이 없으면 "어느 프레임이 통과했는지"가 추론에 머문다** — T2에서 실제로 그랬다
     * (`count`가 0/1로 흔들렸는데 어느 `audio` 프레임에서 났는지 알 수 없어 순서에서 역추론했다).
     * `afterRecvAudio`는 그 `start`가 불린 시점까지 **수신한** `audio` 프레임 수다.
     */
    started: { count: 0, when: [], calls: [] },
    /** 종단 프레임 도착 시점의 동기 스냅샷. ⚠️ **진단용이다** — 단정은 `snapshots`로 한다(아래). */
    finalLinesAtTerminal: null,
    /**
     * **A1-5 단정의 정본.** MutationObserver가 DOM이 바뀔 때마다 적립한다.
     *
     * ⚠️ **동기 스냅샷도 rAF 스냅샷도 회차 운에 걸린다** — T2는 동기가 React commit 전이라 `[]`를
     * 봤고, rAF는 `router.push` 이후에 떠서 `[]`를 봤다(둘이 **서로 반대로** 실패했다). T5a는
     * 여유가 9.7초라 동기가 통했다. **타이밍에 걸리지 않는 유일한 방법은 "언제 찍을까"를 고르지
     * 않고 바뀔 때마다 전부 적립하는 것**이다.
     *
     * 항목: `{ ts, count, texts }`. **직전과 같으면 적립하지 않는다**(중복 억제).
     *
     * ⚠️ **"기대값과 같은 스냅샷이 하나 있다"만으로 단정하지 않는다** — 그것은 골라내기다.
     * 세 개를 함께 본다: ① 관측된 **최대 개수가 정확히 기대 개수**(초과가 없다) ② **그 최대
     * 지점의 `texts`가 기대와 순서까지 일치** ③ `count`가 **비감소**(전사문은 append-only이고
     * 병합은 개수를 늘리지 않는다 — `page.tsx`의 계약). 셋을 함께 걸면 골라내기가 막힌다.
     */
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
      /**
       * ⚠️ **이 필드는 "그 시점의 기록"이고 현재 상태가 아니다.** T5a 관측: `tryResume()` 안에서만
       * 갱신되므로 async `resume()`이 끝나기 전 값이 남는다. **현재 상태는 `omy.contextState()`로
       * 읽어라** — 그것이 살아 있는 값이다. 이 필드는 이력의 마지막 항목이다.
       */
      audioContextState: null,
      /** `resume()` 시도마다 `{ at, before, afterSync, afterAwait }`. `afterAwait`가 진짜 결과다. */
      resumeLog: [],
      resumeAttempts: 0,
      resumeErrors: [],
      appHandlerAttached: false,
      /** 앱 세션 소켓으로 인정한 URL 조각. `sent.foreign` 판정의 기준이다. */
      appSocketPath: "/ws/session",
      /** 관측한 소켓 URL 전부 — `foreign`이 왜 생겼는지 사후에 알 수 있게 한다. */
      socketUrls: [],
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
  // ⚠️ 살아 있는 값을 읽는 경로를 따로 둔다 — 스냅샷 필드는 시점 기록이라 §11-3을 판정할 수 없다.
  omy.contextState = () => ({ state: ctx.state, currentTime: ctx.currentTime });

  const tryResume = () => {
    omy.meta.resumeAttempts += 1;
    const entry = { at: Date.now(), before: ctx.state, afterSync: null, afterAwait: null };
    omy.meta.resumeLog.push(entry);
    try {
      const result = ctx.resume();
      if (result && typeof result.then === "function") {
        // **여기가 진짜 결과다.** 동기 직후 값은 resume 이전 상태일 수 있다(T5a 관측).
        result.then(
          () => {
            entry.afterAwait = ctx.state;
            omy.meta.audioContextState = ctx.state;
          },
          (error) => {
            entry.afterAwait = `error: ${error}`;
            omy.meta.resumeErrors.push(String(error));
          }
        );
      }
    } catch (error) {
      omy.meta.resumeErrors.push(String(error));
      entry.afterAwait = `throw: ${error}`;
    }
    entry.afterSync = ctx.state;
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

  // ── 4-b. 스냅샷 적립 — "언제 찍을까"를 고르지 않는다 ────────────────────────
  // ⚠️ 동기(종단 프레임)와 rAF 둘 다 회차 운에 걸렸다(T2에서 **서로 반대로** 실패했다).
  // 타이밍에서 벗어나는 유일한 방법은 **DOM이 바뀔 때마다 전부 적립**하는 것이다.
  const record = () => {
    const texts = snapshotNow();
    const last = omy.snapshots[omy.snapshots.length - 1];
    // 직전과 같으면 적립하지 않는다 — MutationObserver는 같은 상태로도 여러 번 부른다.
    // ⚠️ 구분자는 NUL 이고 **이스케이프 표기로 적는다** — 리터럴 NUL 을 넣으면 이 파일이
    //    바이너리로 판정되어 `-a` 없는 grep 이 전부 무효가 된다(함정 H-AG, 2026-09-06 실측).
    //    공백으로 되돌리지 마라: 줄 텍스트에 공백이 들어 있어 경계가 모호해진다.
    if (last && last.count === texts.length && last.texts.join("\u0000") === texts.join("\u0000")) {
      return;
    }
    omy.snapshots.push({ ts: Math.round(performance.now()), count: texts.length, texts });
  };
  const observer = new MutationObserver(record);
  observer.observe(document.body, { childList: true, subtree: true, characterData: true });
  record(); // 시작 상태(보통 0줄)를 첫 항목으로 남긴다 — 0에서 출발했음을 증거로 만든다.
  /** 관측을 멈춘다. 회차 끝에서 부른다 — 안 불러도 무해하지만 스냅샷이 계속 쌓인다. */
  omy.stopRecording = () => {
    observer.disconnect();
    return omy.snapshots.length;
  };
  /**
   * A1-5 판정을 **골라내기 없이** 낸다. 기대 배열을 넣으면 셋을 함께 재서 돌려준다.
   * ⚠️ 이 함수는 판정을 **계산**할 뿐이고 기대값을 만들지 않는다 — 기대값은 호출자가
   * `fixtures.py:FIXTURE_TURNS`에서 연역해 넘긴다.
   *
   * ## 2026-09-06 재설계 (T13 회차) — 내용·순서 판정을 **종단 스냅샷**으로 옮겼다
   *
   * ⛔ **이전 판은 `snapshots.find(s => s.count === maxCount)`로 「첫」 최대치를 골라 거짓 FAIL을
   * 냈다.** 같은 코드·같은 픽스처·같은 어댑터로 돌린 2회차가 갈렸다(`snapshotCounts`
   * `0,1,2,2,2,3,4,4,4,5,6,0` = pass 대 `0,1,2,2,2,3,4,4,4,5,6,6,0` = fail). 후자의 첫 `6`은
   * **확정 5줄 + partial 1줄**이었다 — partial 줄이 확정 줄과 **같은 접두 구조**를 쓰기 때문이다
   * (`page.tsx:313~317` 대 `:307~311`). 즉 `count`는 "확정 줄 수"가 아니라 "확정 + partial"이다.
   * **뿌리는 `find`가 아니라 선별이 과도 상태를 계수에 넣는 것이고 `find`는 방아쇠였다.**
   *
   * ⛔ **"최대치 지점 전부를 후보로 두고 하나라도 일치하면 통과"로 고치지 않았다** — 그것은 거짓
   * PASS를 만든다. `page.tsx:123~124`의 I-8 병합은 **개수를 바꾸지 않고 텍스트만** 바꾸므로,
   * 병합이 망가져 뒤쪽이 오염돼도 앞쪽의 올바른 최대치 하나로 통과한다. 그러면 이 파일이
   * 스스로 금지한 **"골라내기"를 최대치 부분집합 안에서 되살리는** 셈이다.
   *
   * ⛔ **색으로 확정/partial을 가르지도 않았다** — 둘의 유일한 구조적 차이가 색이고
   * (`--foreground` 대 `--foreground-muted`), `browser_leg.md` §6이 색을 선별에 쓰는 것을 금지한다.
   *
   * **채택한 방법**: 내용·순서는 **`finalLinesAtTerminal`**(종단 프레임을 앱이 처리하기 직전의
   * 동기 스냅샷)로 재고, 적립(`snapshots`)은 **초과 검출과 단조성**에만 쓴다. 근거는 T13 실측이다 —
   * 실제 서버 경로에서 그 동기 스냅샷이 **2회 모두** 픽스처 6줄과 정확히 일치했고, 그것은 우연이
   * 아니다: WebSocket `message`는 프레임마다 **별개 task**로 디스패치되고 React는 task 경계에서
   * flush하므로 **커밋 개입이 구조적**이다. 프레임이 같은 tick에 몰리는 것은 **주입만** 하는 일이고
   * 주입 시나리오(C2·C5)는 이 판정을 쓰지 않는다.
   *
   * ⚠️ **`finalLinesAtTerminal`이 없으면 통과시키지 않는다**(`terminalPresent`). 종단 프레임이 오지
   * 않았거나 `inject()`로만 프레임을 넣은 회차에서는 이 값이 `null`인데, 그때 조용히 통과하면
   * **"0은 고장과 구별되지 않는다"**가 된다.
   */
  omy.judgeFinalLines = (expected) => {
    const counts = omy.snapshots.map((s) => s.count);
    const maxCount = counts.length ? Math.max(...counts) : 0;
    // 0으로의 낙하는 언마운트다 — **마지막에 오는 0만** 허용한다. 중간에 0으로 떨어졌다가 다시
    // 오르는 것은 컨테이너가 언마운트·재마운트된 것이므로 이상이고, 이전 판의 `|| c === 0`은
    // 그것까지 통과시켰다(2026-09-06 독립 리뷰가 지적한 구멍을 여기서 닫는다).
    const nonDecreasing = counts.every((c, i) => {
      if (i === 0) return true;
      if (c >= counts[i - 1]) return true;
      return c === 0 && counts.slice(i).every((later) => later === 0);
    });
    const terminal = omy.finalLinesAtTerminal;
    const terminalPresent = Array.isArray(terminal);
    const terminalMatches =
      terminalPresent &&
      terminal.length === expected.length &&
      terminal.every((t, i) => t === expected[i]);
    return {
      maxCount,
      expectedCount: expected.length,
      // 초과 검출 — 과도 상태에도 최대치가 기대값을 넘지 않는 것이 계약이다.
      noExcess: maxCount === expected.length,
      terminalPresent,
      terminalMatches,
      nonDecreasing,
      snapshotCount: omy.snapshots.length,
      finalLinesAtTerminal: terminal,
      // **진단용이다 — 판정에 쓰지 않는다.** 이전 판이 이것으로 판정해 거짓 FAIL을 냈다.
      atMaxDiagnostic: omy.snapshots.find((s) => s.count === maxCount) || null,
      // 넷 전부 참이어야 PASS 다. 하나라도 거짓이면 그 항목이 사유다.
      pass: terminalPresent && terminalMatches && maxCount === expected.length && nonDecreasing,
    };
  };

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
          // ⚠️ **이 동기 스냅샷은 진단용이다 — A1-5의 단정 대상이 아니다.**
          // 처음에는 이것이 단정 정본이었는데 **React commit 전에 찍히면 `[]`가 된다**(T2 실측).
          // 반대로 rAF로 옮기면 `router.push` **이후**에 떠서 역시 `[]`가 됐다 — 두 방식이
          // 서로 반대로 실패한다. 그래서 단정은 §4-b의 MutationObserver 적립(`snapshots`)이
          // 소유하고, 이 값은 "종단 프레임 시점에 무엇이 보였나"의 기록으로만 남긴다.
          if (frame && (frame.type === "session_ended" || frame.type === "session_failed")) {
            omy.finalLinesAtTerminal = snapshotNow();
          }
        } catch {
          // 해석할 수 없는 프레임은 세지 않는다 — 앱도 같은 자리에서 무시한다(`ws.ts`).
        }
        return fn(event);
      });
    },
  });

  // ── 6. 실제 전송 계수 (A1-7의 효과 지점) ────────────────────────────────────
  /** base64 PCM(16bit LE)에 0이 아닌 샘플이 하나라도 있는지. **무음과 유음을 가르는 유일한 값이다.** */
  const hasNonZeroPcm = (base64) => {
    if (!base64) return false;
    let bytes;
    try {
      bytes = atob(base64);
    } catch {
      return false; // base64가 아니면 판정하지 않는다 — false 로 세는 편이 안전하다.
    }
    // 16bit LE 두 바이트가 **둘 다 0이 아닐 때만** 0이 아닌 샘플이다. 바이트 단위로 훑어도
    // 같은 결과가 나온다(0 샘플은 두 바이트가 모두 0이다).
    for (let i = 0; i < bytes.length; i += 1) {
      if (bytes.charCodeAt(i) !== 0) return true;
    }
    return false;
  };

  const nativeSend = sendOwner.descriptor.value;
  sendOwner.proto.send = function (data) {
    // ⚠️ **앱 소켓만 센다.** 전역 프로토타입을 감싸므로 Next dev HMR 소켓이 섞인다(T5a 실측:
    // `sent.other = 1`의 정체가 `ws://localhost:3000/_next/hmr?...`였다).
    const url = typeof this.url === "string" ? this.url : "";
    if (omy.meta.socketUrls.indexOf(url) === -1) omy.meta.socketUrls.push(url);
    if (url.indexOf(omy.meta.appSocketPath) === -1) {
      omy.sent.foreign += 1;
      return nativeSend.call(this, data);
    }
    try {
      const payload = JSON.parse(data);
      const type = payload && payload.type;
      if (type === "audio") {
        omy.sent.audio += 1;
        omy.sentAudioBytes += (payload.data || "").length;
        if (hasNonZeroPcm(payload.data)) omy.sentAudioNonZeroFrames += 1;
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
    const at = typeof when === "number" ? when : 0;
    omy.started.count += 1;
    omy.started.when.push(at);
    // ⚠️ **프레임 태깅** — 어느 `audio` 프레임에서 이 재생이 났는지를 남긴다. 없으면 "몇 번째가
    // 통과했는가"가 순서에서의 추론에 머문다(T2에서 실제로 그랬다).
    omy.started.calls.push({
      ts: Math.round(performance.now()),
      when: at,
      afterRecvAudio: omy.recv.audio,
      contextState: omy.contextState().state,
    });
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
