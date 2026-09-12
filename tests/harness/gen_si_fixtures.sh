#!/bin/bash
# `TASK-102.1` AC#2 — 무대 정하기(scenario_intake) 회차용 «답» 픽스처를 만든다.
#
# ⛔ **왜 새 ID 인가**: 기존 `pq*` 는 발음 회차용 문장이라 **질문의 답이 아니다**. 그것으로 돌린
# 1회차에서 코치의 첫 턴이 질문 없이 방향을 잡는 데 쓰였다(회차 §4-2) — 지시문의 결함이 아니라
# 입력의 성질이었다. 다섯 축을 순서대로 재려면 **그 질문에 답하는 발화**가 필요하다.
#
# ⛔ **기존 픽스처를 덮지 않는다** — `gen_pq_fixtures.sh` 와 같은 규약이고 존재 검사를 방어로 둔다.
# ⚠️ **목소리·포맷을 그 스크립트와 같게 둔다**(Sohee · `LEI16@16000` · 모노) — 화자가 달라지면
# 앞 회차와 비교할 때 화자 효과가 섞인다.
#
# ⚠️ **`si04` 가 「모르겠다」인 것이 의도다.** 설계서 §3 이 *"답을 못 받아도 계속 진행한다 · 비면
# 그 축을 빼고 만든다"* 를 요구하고 지시문이 *"Do not invent an answer for them."* 으로 그것을
# 말한다. 그 경로는 **학습자가 실제로 모른다고 말해야** 관측된다.
set -uo pipefail

QPY=/tmp/qwen_tts_env/bin/python
MODEL=mlx-community/Qwen3-TTS-12Hz-0.6B-CustomVoice-bf16
OUT=/tmp/qwen_out_si
DEST=/Users/redstar/MyProject/OhMyEnglish/tests/harness/fixtures/voice
mkdir -p "$OUT"

gen() {
  local id="$1"; shift
  local text="$*"
  if [ -e "$DEST/$id.wav" ]; then
    echo "SKIP $id — 이미 있음 (덮지 않는다)"
    return
  fi
  $QPY -m mlx_audio.tts.generate --model "$MODEL" --voice Sohee --lang_code en \
    --text "$text" --output_path "$OUT" --file_prefix "$id" --audio_format wav \
    >/dev/null 2>&1
  if [ ! -e "$OUT/${id}_000.wav" ]; then
    echo "FAIL $id — 생성물 없음"
    return
  fi
  afconvert -f WAVE -d LEI16@16000 -c 1 "$OUT/${id}_000.wav" "$DEST/$id.wav"
  echo "OK $id"
}

# ⚠️ `si00` 은 답이 아니라 **여는 인사**다. Nova 는 오디오가 오기 전에 말하지 않으므로(1회차 실측)
# 학습자가 먼저 한마디 하는 것이 제품의 실제 경로다 — 그 자리를 이 픽스처가 채운다.
gen si00 "Hello."
# 축 1 무대 · 2 상대 · 3 목표 · 4 초점(모르겠다) · 5 어조 — 설계서 §3 의 순서 그대로다.
gen si01 "I need English in our weekly team meeting."
gen si02 "My manager and two colleagues."
gen si03 "I want to report my project status clearly."
gen si04 "I don't know."
gen si05 "It is quite formal."

echo "=== 생성 끝 — 길이를 잰다 (빈 파일 검출) ==="
for f in "$DEST"/si*.wav; do
  [ -e "$f" ] || continue
  printf '%s  ' "$(basename "$f")"
  afinfo "$f" 2>/dev/null | awk -F': ' '/estimated duration/ {printf "%s  ", $2} /Data format/ {print $2}'
done
