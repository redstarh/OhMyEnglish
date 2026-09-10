#!/bin/bash
# TASK-89 — Qwen3-TTS(Sohee · lang_code=en)로 「중간 지대」 발음 픽스처를 만든다.
# ⛔ 기존 픽스처를 덮지 않는다 (AC#3). pq* 는 새 이름이고, 존재 검사를 방어로 둔다.
set -uo pipefail

QPY=/tmp/qwen_tts_env/bin/python
MODEL=mlx-community/Qwen3-TTS-12Hz-0.6B-CustomVoice-bf16
OUT=/tmp/qwen_out_pq
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

# ── 그룹 A — 단일 음소 · 단일 단어 (밀도 D1)
gen pq01 "I sink we need to fix this bug today."
gen pq02 "I need to send the pinal report today."
gen pq03 "The meeting was bery helpful for our team."
gen pq04 "I want to leview the code with you."
gen pq05 "It is eaji to understand the new process."

# ── 그룹 B — 단일 음소 반복 (밀도 D2)
gen pq06 "I sink sree sings are ready for the demo."
gen pq07 "I will leview the lepolt and shale the lesults."
gen pq08 "I pinished the pirst bersion of the pile."

# ── 그룹 C — 기존 p1m·p2m 과 같은 철자 (화자 효과 분리 · 밀도 D3)
gen pq09 "I sink I pound sree bery useful bideos."
gen pq10 "I pinished the leport and shaled the lesults wis my team."

# ── 그룹 D — 대조군 · 정확 철자 (화자 자체가 코칭을 유발하는지 배제)
gen pq11 "I think we need to fix this bug today."
gen pq12 "I think three things are ready for the demo."

echo "=== 생성 끝 — 길이를 잰다 (빈 파일 검출) ==="
for f in "$DEST"/pq*.wav; do
  [ -e "$f" ] || continue
  printf '%s  ' "$(basename "$f")"
  afinfo "$f" 2>/dev/null | awk -F': ' '/estimated duration/ {printf "%s  ", $2} /Data format/ {print $2}'
done
