# TASK-59 — 발음 픽스처를 Qwen3-TTS 로 다시 만든 결과: **H1 반증**

> 판정: **도구 품질이 우리 픽스처의 병목이 아님.** 이 목적(강한 한국어 억양 재현)에는
> `say -v Yuna` 가 Qwen3-TTS 보다 **낫음** — 정반대 방향의 실측이 나왔음.
> 원자료: `.harness/evidence/task59/*.json` (스파이크 6회)

---

## 1. 무엇을 재려 했는가

`docs/design/2026-09-09-realtime-meeting-fit-gap.md` 의 **F2** 가 「Qwen3-TTS 를 발음 픽스처
생성에 쓴다」를 가장 값어치 있는 Fit 으로 적었고 **H1** 을 열어 두었음: *「Qwen3-TTS 로 만든
`p1k` 가 Nova 에서 「한국어 억양 영어」로 전사돼 발음 오류가 재현된다」*. 판정선은
**전사가 영어로 정확히 복원되는지** 였음.

근거는 참고 리포(`realtime-meeting`)의 실측이었음 — 같은 문장 3개에서 `say -v Yuna` 는
1문장이 어긋났고 Qwen `Sohee`·`Aiden` 은 3/3 일치했음.

## 2. 어떻게 쟀는가

`Qwen3-TTS`(Apache-2.0)를 임시 venv 로 격리해 설치했음 — 프로젝트 의존성에 넣지 않았음.

```bash
uv venv --python 3.12 /tmp/qwen_tts_env
VIRTUAL_ENV=/tmp/qwen_tts_env uv pip install mlx-audio
/tmp/qwen_tts_env/bin/python -m mlx_audio.tts.generate \
  --model mlx-community/Qwen3-TTS-12Hz-0.6B-CustomVoice-bf16 \
  --voice Sohee --lang_code en --text '<문장>' \
  --output_path /tmp/qwen_out --file_prefix p1_sohee_en --audio_format wav
afconvert -f WAVE -d LEI16@16000 -c 1 /tmp/qwen_out/p1_sohee_en_000.wav p1q.wav
```

`Sohee` 가 한국어 원어민 여성 화자임. `lang_code` 를 **두 갈래로 갈라** 만들었음 —
`en`(한국어 화자가 영어를 읽음) · `ko`(영문자를 한국어 음운으로 읽음. 기존 `say -v Yuna` 에
가까운 쪽). 어느 쪽이 억양을 남기는지 몰랐으므로 둘을 다 만들었음.

**⛔ 길이를 먼저 쟀음**(미설치 음성이 0.016초 빈 파일을 만들고 그것을 앱 결함으로 오인한 사례가
참고 리포에 있음). 전부 실제 음원이었음:

| 픽스처 | 화자·언어코드 | 길이 | 기존 대조 |
|---|---|--:|--:|
| `p1q.wav` | Sohee · `en` | 4.88s | `p1k` 3.05s |
| `p1qk.wav` | Sohee · `ko` | 3.92s | 〃 |
| `p2q.wav` | Sohee · `en` | 4.96s | `p2k` 3.79s |
| `p2qk.wav` | Sohee · `ko` | 5.36s | 〃 |

전부 16kHz · 16bit · mono(Nova 입력 규격).

판정 경로는 **`spike_nova_protocol.py` 직결**임 — 앱 경로가 아님. 이유 둘: 브라우저 캡처·
게이트웨이를 배제해 **오디오만의 차이**를 재려 했고, DB 세션을 만들지 않아 보존 세션
(`browser_leg.md` §9)을 위험에 두지 않음.

## 3. 실측 — 여섯 회 왕복

| # | 픽스처 | 생성 도구 | Nova ASR 전사문 | agent 응답 |
|--:|---|---|---|---|
| 1 | `p1q` | Qwen Sohee·`en` | `i think i found three very useful videos` | 정상 대화 |
| 2 | `p1qk` | Qwen Sohee·`ko` | `i think i found three very useful videos.` | 정상 대화 |
| 3 | **`p1k`** | **`say -v Yuna`** | **`아이싱크 아이파운드 쓰리 베리 유스풀 비디오즈`** | **`I'm sorry, but I can't process that request as it seems unclear.`** |
| 4 | `p2q` | Qwen Sohee·`en` | `i finished the report and shared the results with my team.` | 정상 대화 |
| 5 | `p2qk` | Qwen Sohee·`ko` | `i finished the report and shared the results with my team.` | 정상 대화 |
| 6 | **`p2k`** | **`say -v Yuna`** | **`아이피니시트더리포트엔쉐어드더리절치위드마이팀`** | **`Sorry, I didn't catch that.`** |

두 문장에서 **같은 방향**이 나왔음. Qwen 은 `lang_code` 를 `ko` 로 줘도 영어로 복원됐음.

## 4. 판정

**H1 = 반증. 닫음.** Qwen3-TTS 로 만든 음원은 발음 오류를 **덜** 재현함.

**뒤집힌 것은 F2 의 방향임** — 「우리 픽스처가 막힌 원인의 일부가 도구 품질일 수 있다」가
틀렸음. 두 도구의 우열이 **목적에 따라 뒤집히기** 때문임:

| | `realtime-meeting` 의 목적 | OhMyEnglish P계층의 목적 |
|---|---|---|
| 원하는 것 | 회의록의 **정확한 전사** | 의도한 **발음 오류의 재현** |
| 좋은 음원 | 전사가 원문과 일치하는 음원 | 전사가 **무너지는** 음원 |
| 따라서 나은 도구 | **Qwen3-TTS** (3/3 일치) | **`say -v Yuna`** (한글 전사를 만듦) |

같은 실측표를 두 프로젝트가 **정반대로 읽어야 함.** 참고 리포의 수치는 틀리지 않았고, 그것을
우리 목적에 옮길 때 부호가 바뀌는 것을 F2 가 놓쳤음.

## 5. 함께 얻은 것 — 5차수 `P4` 미재현의 원인이 픽스처가 아님

5차수가 **`P4`(`p1k`) `FAIL` 미재현**(한글이 아니라 영어로 전사)을 적고
*「경로가 달라 「사라졌다」로 단정하지 않음」* 으로 남겼음. **이 회차가 그 유보를 닫음** —
같은 `p1k.wav` 가 **스파이크 경로에서는 지금도 한글로 전사됨**(위 표 3행).

⛔ 즉 **픽스처는 멀쩡하고 갈라지는 것은 경로임.** 앱 경로(브라우저 캡처 → 게이트웨이 →
Nova)에서 무엇이 오디오를 바꾸는지가 미확정이고 그것이 조사 대상임 → **`TASK-65`**.

⚠️ **원인을 단정하지 않음.** 후보는 리샘플·프레임 케이던스·`AudioContext` 디코드 손실 등
여럿이고 이 회차는 그중 무엇도 배제하지 못했음.

## 6. TASK-63 에 넘기는 증거 — Qwen 의 영어 품질

`TASK-63`(쉐도잉 클립을 음성 합성으로) AC#2 가 *「영어 품질을 따로 확인한다」* 를 요구했음.
위 1·2·4·5 행이 그 증거임 — **네 회 모두 Nova ASR 이 원문과 일치했음**(구두점 제외).
⚠️ 이것은 **기계 전사 기준의 명료도**이고 **학습자가 따라 할 원어민 발화로서의 적합성은
판정하지 않았음** — 그 판단은 `TASK-63` AC#3 이 사용자에게 묻는 몫임.

## 7. 남긴 자산

- 픽스처 4개를 `tests/harness/fixtures/voice/` 에 상주시켰음(`p1q`·`p1qk`·`p2q`·`p2qk`).
  ⛔ **기존 `p1k`·`p2k` 를 덮지 않았음** — 덮으면 위 3·6 행의 통제 대조를 다시 만들 수 없음.
  TTS 는 표본마다 출력이 갈리므로 명령만 남겨서는 같은 음원을 되찾지 못함.
- 원자료 6건: `.harness/evidence/task59/{p1q-sohee-en,p1qk-sohee-ko,p1k-say-yuna-control,p2q,p2qk,p2k}.json`
- 임시 venv `/tmp/qwen_tts_env` 와 모델 캐시는 **프로젝트 밖**임. 재부팅하면 venv 가 사라지고
  모델 캐시(`~/.cache/huggingface`, 2.3GB)는 남음.
