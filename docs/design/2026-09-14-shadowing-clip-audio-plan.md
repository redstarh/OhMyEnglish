# 합성 쉐도잉 클립 오디오 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 합성한 쉐도잉 클립 오디오를 스키마·파일·엔드포인트·화면까지 한 커밋 흐름으로 내서
학습자가 클립 소리를 실제로 듣게 함.

**Architecture:** `shadowing_items` 에 `audio_filename` 컬럼 하나를 더하고 CHECK 둘로 R10-7 예외
경계를 새김. 파일은 `assets/clips/<item id>.wav` 로 git 이 추적하고, 새 엔드포인트
`GET /api/shadowing/clips/{item_id}/audio` 가 바이트를 내주며, 프런트는 `new Audio()` 의
`playbackRate` 와 `ended` 반복으로 결정 6 의 값역을 충족함.

**Tech Stack:** PostgreSQL 17 · asyncpg · FastAPI · pydantic-settings · pytest ·
Next.js(app router · 인라인 style + CSS 변수) · Qwen3-TTS(mlx-audio · 오프라인 생성 전용).

**Spec:** `docs/design/2026-09-14-shadowing-clip-audio-design.md`

## Global Constraints

- 태스크는 `TASK-66` 이고 AC#1·#2·#4·#5 가 이 계획의 범위임. AC#3 은 결정 88 로 이미 닫혔음.
- 게이트는 **cwd `app/backend`** 에서 돌림(`H-A`·`H-BN`). 전체는 `.venv/bin/pytest -q`,
  **부분 실행에는 `-c pyproject.toml` 을 붙임**(`H-AJ`). `ty` 는 절대경로
  `/Users/redstar/.local/bin/ty` 로 부름(이름만으로는 exit 127).
- ⛔ **`pytest` 를 돌리기 전에 발음 축 세션(`ohmyenglish-d9`)에 알림**(`H-X`) — 테스트 DB 가 실행마다
  재생성됨.
- ⛔ `git add <디렉터리>` 를 쓰지 않음(`H-BE`). 커밋 **전** `git diff --cached --name-only` 로 index 를
  확인하고, push **전** `git log --oneline origin/<브랜치>..HEAD` 를 봄(`H-BO`).
- ⛔ 커밋 메시지 끝에 `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>` 를 넣음.
- 마이그레이션 번호는 **적용 직전 조회로 발급**함(`H-AL`). 이 계획을 쓴 시점의 파일 최대는 `021` 임.
- ⛔ **dev DB 적용은 승인 사안임**(Task 9). 그 전까지 dev DB 를 건드리지 않음 — 지금 dev DB 는 `019`
  까지 적용돼 있고 020·021 이 미적용임.
- 파일명 규약은 **`<item id>.wav`** 하나임. 시드 클립의 id 는
  `00000000-0000-0000-0000-000000000201` 이므로 파일명은
  `00000000-0000-0000-0000-000000000201.wav` 임.
- 오디오 규격은 **WAV 16kHz mono 16-bit** 임(선행 검토 §7.2 의 「앱 재생 규격」).

---

## Task 1: 마이그레이션 022 — 컬럼 하나와 CHECK 둘

**Files:**
- Create: `db/migrations/022_shadowing_clip_audio.sql`
- Test: `tests/unit/test_schema.py` (기존 쉐도잉 절 뒤에 022 절을 붙임)

**Interfaces:**
- Consumes: 없음(첫 태스크임).
- Produces: `shadowing_items.audio_filename text` 컬럼 · 제약 이름 둘
  (`shadowing_items_audio_filename_matches_id` · `shadowing_items_audio_only_for_synthetic`).

- [ ] **Step 1: 실패하는 스키마 단정 둘을 쓴다**

`tests/unit/test_schema.py` 의 맨 끝에 붙인다. ⚠️ 이 파일은 `db_conn`(롤백 트랜잭션)을 쓰므로
행을 남기지 않는다.

```python
# ⑥ 022 — 합성 클립 오디오의 자리와 예외 경계 (`TASK-66` · 결정 90 ·
#    설계서 `2026-09-14-shadowing-clip-audio-design.md` §3).
@pytest.mark.asyncio
async def test_shadowing_clip_audio_filename_must_equal_the_row_id(
    db_conn: asyncpg.Connection,
):
    """파일명 규약을 스키마가 강제한다 — 경로 구분자와 확장자 변경이 같은 CHECK 에 걸린다.

    ⛔ **이 단정이 경로 이탈 방어의 첫 겹이다.** 서버는 경로를 `item_id` 로 조립하지만(둘째 겹),
    DB 에 `../` 가 들어갈 수 있으면 그 조립을 신뢰하는 다음 사람이 뚫린다.
    """
    item_id = await db_conn.fetchval(
        "insert into shadowing_items (source_title, transcript, clip_start_sec, "
        "clip_end_sec, level) values ('Morning', 'I wake up at seven.', 0, 16.64, 'A2') "
        "returning id"
    )

    # 규약대로면 받는다.
    await db_conn.execute(
        "update shadowing_items set audio_filename = $2 where id = $1", item_id, f"{item_id}.wav"
    )
    assert await db_conn.fetchval(
        "select audio_filename from shadowing_items where id = $1", item_id
    ) == f"{item_id}.wav"

    # 확장자가 다르거나 경로가 섞이거나 남의 id 면 거부된다.
    for bad in (f"{item_id}.opus", f"clips/{item_id}.wav", "../secrets.wav", "x.wav"):
        with pytest.raises(asyncpg.CheckViolationError):
            async with db_conn.transaction():
                await db_conn.execute(
                    "update shadowing_items set audio_filename = $2 where id = $1", item_id, bad
                )


@pytest.mark.asyncio
async def test_shadowing_clip_audio_is_rejected_when_the_clip_has_a_source_url(
    db_conn: asyncpg.Connection,
):
    """R10-7 예외의 경계 — 출처 링크가 있는 클립에는 오디오가 붙지 않는다.

    결정 47 이 연 범위는 「합성한 쉐도잉 클립 오디오」 하나이고, 출처 링크가 있는 것은 외부
    저작물이라 PRD §5(*"저작물 전체를 저장하지 않는다"*)가 막는다. 011 의
    `utterances_audio_only_for_shadowing` 이 학습자 낭독 자리에서 한 일과 같다.
    """
    item_id = await db_conn.fetchval(
        "insert into shadowing_items (source_title, source_url, transcript, clip_start_sec, "
        "clip_end_sec, level) values ('Talk', 'https://example.com/v', 'I wake up.', 0, 40, 'A2') "
        "returning id"
    )

    with pytest.raises(asyncpg.CheckViolationError):
        async with db_conn.transaction():
            await db_conn.execute(
                "update shadowing_items set audio_filename = $2 where id = $1",
                item_id,
                f"{item_id}.wav",
            )
```

- [ ] **Step 2: 돌려서 실패를 확인한다**

Run: `cd app/backend && .venv/bin/pytest -c pyproject.toml ../../tests/unit/test_schema.py -q -k clip_audio`
Expected: FAIL — `asyncpg.exceptions.UndefinedColumnError: column "audio_filename" of relation "shadowing_items" does not exist`

⛔ **실패 메시지가 위와 다르면 멈춘다.** `-k` 필터가 새 테스트를 걸러 「0 selected」가 나오는 것을
「통과」로 읽지 않는다(그 실패를 이 리포가 이미 밟았음).

- [ ] **Step 3: 마이그레이션을 쓴다**

```sql
-- 022_shadowing_clip_audio.sql
-- 합성한 쉐도잉 클립 오디오의 자리 — 파일명 컬럼 + 예외 경계 CHECK 둘
-- 설계: docs/design/2026-09-14-shadowing-clip-audio-design.md §3
-- 캡틴 결정: 47(쓴다·미리 만들어 저장 · R10-7 예외를 이 하나로 엶) · 90(리포 추적 · 접근 A)
-- 소유 태스크: TASK-66
--
-- 번호: `ls db/migrations/` 실측 최대가 021 이므로 022 다. ⛔ 적용 직전에 다시 확인한다(H-AL).
-- ⛔ 소비자와 같은 커밋 흐름으로 나간다 — 011 이 세운 data-first 규약이고 결정 90 이 그것을
--    유예하는 안을 기각했다.

alter table shadowing_items
  add column audio_filename text;

-- 파일명은 **id 로 결정된다.** 뿌리는 설정값(`shadowing_clip_audio_root`)이고 이 컬럼은 파일명만
-- 담는다. ⛔ 이 CHECK 가 경로 구분자를 원리적으로 배제한다 — 값역이 방어의 첫 겹이다.
-- ⚠️ 포맷을 바꾸려면 이 제약을 고쳐야 한다. **그것이 의도다** — 값역이 계약이고, 011 이
--    `utterance_type` 값역으로 같은 일을 했다.
alter table shadowing_items
  add constraint shadowing_items_audio_filename_matches_id
  check (audio_filename is null or audio_filename = id::text || '.wav');

-- R10-7 예외의 경계. 결정 47 이 연 것은 「합성한 쉐도잉 클립 오디오」 하나이고, 출처 링크가 있는
-- 클립은 외부 저작물이라 PRD §5 가 막는다.
-- ⛔ 011 의 `utterances_audio_only_for_shadowing` 주석이 적은 의도를 이 표에서 잇는다:
--    **다른 오디오가 조용히 쌓이는 길을 스키마가 막는다.**
alter table shadowing_items
  add constraint shadowing_items_audio_only_for_synthetic
  check (audio_filename is null or source_url is null);
```

- [ ] **Step 4: 돌려서 통과를 확인한다**

Run: `cd app/backend && .venv/bin/pytest -c pyproject.toml ../../tests/unit/test_schema.py -q -k clip_audio`
Expected: PASS 2건. 테스트 DB 는 실행마다 마이그레이션으로 재생성되므로 별도 적용이 필요 없다.

- [ ] **Step 5: 판별력을 확인한다 — 변이가 적용됐는지 먼저 단정한다**

CHECK 하나를 지운 판을 만들어 red 를 본 뒤 되돌린다.

```bash
cd /Users/redstar/MyProject/OhMyEnglish
cp db/migrations/022_shadowing_clip_audio.sql /tmp/022.bak
/usr/bin/python3 - <<'PY'
import pathlib
p = pathlib.Path("db/migrations/022_shadowing_clip_audio.sql"); s = p.read_text()
s2 = s.replace("or audio_filename = id::text || '.wav'", "or true")
assert s2 != s, "⛔ 변이가 적용되지 않았다 — 대상 문자열이 안 맞았다"
p.write_text(s2)
PY
cd app/backend && .venv/bin/pytest -c pyproject.toml ../../tests/unit/test_schema.py -q -k clip_audio
# Expected: FAIL (파일명 단정이 무너진다)
cd /Users/redstar/MyProject/OhMyEnglish && cp /tmp/022.bak db/migrations/022_shadowing_clip_audio.sql
diff -q /tmp/022.bak db/migrations/022_shadowing_clip_audio.sql && echo "원본과 동일함"
cd app/backend && .venv/bin/pytest -c pyproject.toml ../../tests/unit/test_schema.py -q -k clip_audio
# Expected: PASS 2건
```

- [ ] **Step 6: 커밋한다**

```bash
git add db/migrations/022_shadowing_clip_audio.sql tests/unit/test_schema.py
git diff --cached --name-only
git commit -m "$(cat <<'EOF'
feat(TASK-66): 022 로 합성 클립 오디오의 자리와 예외 경계를 새겼음

audio_filename 컬럼 하나에 CHECK 둘을 걸었음 — 파일명을 id 로 강제해 경로 이탈을 값역에서
막고, source_url 이 있는 클립에는 오디오가 붙지 못하게 해 R10-7 예외를 합성 클립 하나로
좁혔음(결정 47·90).

⛔ dev DB 에 적용하지 않았음 — 승인 사안임. 테스트 DB 는 실행마다 재생성되므로 단정이 이미
그 스키마를 재고 있음. 판별력은 CHECK 를 `or true` 로 무력화해 red 를 보고 되돌려 확인했음.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: 설정 키 `shadowing_clip_audio_root`

**Files:**
- Modify: `app/backend/app/config.py` (`shadowing_audio_root` 선언 바로 뒤)
- Test: `tests/unit/test_config.py` (`test_declared_defaults_are_immune_to_the_environment` 에 한 줄 +
  새 테스트 하나)

**Interfaces:**
- Consumes: 없음.
- Produces: `Settings.shadowing_clip_audio_root: Path`(기본 `Path("../../assets/clips")`) ·
  환경변수 이름 `SHADOWING_CLIP_AUDIO_ROOT`.

- [ ] **Step 1: 실패하는 단정을 쓴다**

`tests/unit/test_config.py` 의 `test_declared_defaults_are_immune_to_the_environment` 안에 한 줄을
더한다.

```python
    assert declared["shadowing_clip_audio_root"] == Path("../../assets/clips")
```

그리고 `test_shadowing_audio_root_defaults_outside_the_backend_tree` 바로 뒤에 새 테스트를 붙인다.

```python
def test_shadowing_clip_audio_root_is_a_separate_root_from_learner_recordings(_no_settings_env):
    """⛔ **두 오디오의 뿌리가 달라야 한다** (설계서 §4).

    `sweep_orphan_recording_files` 가 `shadowing_audio_root` 를 `iterdir()` 로 순회하며 걷으므로
    같은 자리에 두면 **제품 자산이 스윕 대상이 된다.** 그리고 학습자 녹음 뿌리는 `.gitignore` 에
    걸려 있어 그 아래 두면 클립이 **배포되지 않는다** — 두 성질이 같은 방향을 가리킨다.
    """
    settings = _settings_with_credentials()

    assert settings.shadowing_clip_audio_root == Path("../../assets/clips")
    assert settings.shadowing_clip_audio_root != settings.shadowing_audio_root
    # 학습자 녹음 뿌리의 **아래**가 아니다 — 스윕의 순회 범위 밖이라는 뜻이다.
    assert not (BACKEND_ROOT / settings.shadowing_clip_audio_root).resolve().is_relative_to(
        (BACKEND_ROOT / settings.shadowing_audio_root).resolve()
    )
```

- [ ] **Step 2: 돌려서 실패를 확인한다**

Run: `cd app/backend && .venv/bin/pytest -c pyproject.toml ../../tests/unit/test_config.py -q -k clip_audio_root`
Expected: FAIL — `KeyError: 'shadowing_clip_audio_root'` 또는 `AttributeError`

- [ ] **Step 3: 설정을 더한다**

`app/backend/app/config.py` 의 `shadowing_audio_root` 선언 **바로 뒤**에 붙인다.

```python
    # 합성 클립 오디오의 뿌리 (`TASK-66` · 결정 90 · 설계서 §4). ⛔ **`shadowing_audio_root` 를
    # 재사용하지 않는다**: `sweep_orphan_recording_files` 가 그 뿌리를 순회하며 걷으므로 제품
    # 자산이 스윕 대상이 된다. 학습자 녹음은 당일이 지나면 지워지는 개인정보이고 이쪽은 리포와
    # 함께 배포되는 제품 자산이라 **수명주기가 반대다.**
    # ⚠️ `.gitignore` 는 `assets/audio/` 만 무시하므로 이 형제 자리는 **추적된다** — 그것이
    #    결정 90 의 「리포에 추적한다」이고, 학습자 녹음 뿌리와 정반대의 이유로 이 경로다.
    shadowing_clip_audio_root: Path = Path("../../assets/clips")
```

- [ ] **Step 4: 돌려서 통과를 확인한다**

Run: `cd app/backend && .venv/bin/pytest -c pyproject.toml ../../tests/unit/test_config.py -q`
Expected: PASS(파일 전체) — 선언 기본값 tripwire 가 함께 통과해야 한다.

- [ ] **Step 5: 커밋한다**

```bash
git add app/backend/app/config.py tests/unit/test_config.py
git diff --cached --name-only
git commit -m "$(cat <<'EOF'
feat(TASK-66): 클립 오디오 뿌리를 학습자 녹음과 «다른» 설정 키로 뒀음

sweep_orphan_recording_files 가 shadowing_audio_root 를 순회하며 걷으므로 같은 자리에 두면
제품 자산이 스윕 대상이 됨. 그리고 그 뿌리는 .gitignore 에 걸려 클립이 배포되지 않음 —
두 성질이 같은 방향을 가리켜 뿌리를 갈랐음(결정 90 · 설계서 §4).

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: 오디오 파일 생성·추적 + 시드가 그것을 가리킴

**Files:**
- Create: `assets/clips/00000000-0000-0000-0000-000000000201.wav` (바이너리 · git 추적)
- Modify: `scripts/migrate.py` (`SEED_SHADOWING_ITEMS` · `seed()` 의 insert 절)
- Test: `tests/unit/test_shadowing_seed.py`

**Interfaces:**
- Consumes: Task 1 의 `audio_filename` 컬럼 · Task 2 의 `shadowing_clip_audio_root`.
- Produces: `ShadowingSeedClip.audio_filename: str | None` 필드(insert 컬럼 순서와 묶임) ·
  추적되는 오디오 파일 1개.

- [ ] **Step 1: 오디오를 생성하고 규격으로 변환한다**

⚠️ 선행 검토 §7.1 의 절차를 그대로 쓴다. 전사문은 시드 상수의 것을 **그대로** 복사한다(문장을
바꾸면 결정 25 를 건드린다).

```bash
uv venv --python 3.12 /tmp/qwen_tts_env
VIRTUAL_ENV=/tmp/qwen_tts_env uv pip install mlx-audio
/tmp/qwen_tts_env/bin/python -m mlx_audio.tts.generate \
  --model mlx-community/Qwen3-TTS-12Hz-0.6B-CustomVoice-bf16 \
  --voice Sohee --lang_code en \
  --text 'I usually wake up at seven. First, I check my phone for messages. Then I make a cup of coffee. After that, I get ready for work. The bus stop is close to my house. It takes about thirty minutes to get to the office.' \
  --output_path /tmp/qwen_out --file_prefix 00000000-0000-0000-0000-000000000201 --audio_format wav
afinfo /tmp/qwen_out/00000000-0000-0000-0000-000000000201.wav | grep -i duration
```

⛔ **길이가 1초 미만이면 생성 실패다**(미설치 음성·실패한 생성이 0.016초 빈 파일을 만든다 —
선행 검토 §7.2). 다시 만든다.
⚠️ **잰 길이를 적어 둔다.** 16.64초와 다르면 그것이 새 실측이고 Step 4 에서 시드의
`clip_end_sec` 을 그 값으로 고친다 — 값을 고르지 않고 **잰 것을 쓴다**(결정 88 의 규율).

```bash
mkdir -p assets/clips
afconvert -f WAVE -d LEI16@16000 -c 1 \
  /tmp/qwen_out/00000000-0000-0000-0000-000000000201.wav \
  assets/clips/00000000-0000-0000-0000-000000000201.wav
afinfo assets/clips/00000000-0000-0000-0000-000000000201.wav | grep -iE 'duration|sample rate|channels'
ls -l assets/clips/
git check-ignore -v assets/clips/00000000-0000-0000-0000-000000000201.wav; echo "check-ignore exit=$?"
```

⛔ **`check-ignore` 의 exit 이 1 이어야 한다**(= 무시되지 않음). 0 이면 `.gitignore` 가 이 자리를
덮고 있다는 뜻이고, 그러면 파일이 배포되지 않으므로 **자리를 고치기 전에 진행하지 않는다.**

- [ ] **Step 2: 실패하는 시드 단정 둘을 쓴다**

`tests/unit/test_shadowing_seed.py` 에 붙인다. 파일 맨 위 import 에 `from pathlib import Path` 와
`from app.config import get_settings` 를 더한다.

```python
def test_every_seeded_clip_names_its_audio_by_the_id_convention() -> None:
    """시드가 파일명을 규약대로 갖는다 — 022 의 CHECK 와 같은 규약을 상수에서도 지킨다.

    ⚠️ DB 를 거치지 않고 상수를 직접 읽는 소비자가 있으므로(이 파일이 그렇다) 상수에도 단정을 둔다.
    """
    named = [clip for clip in SEED_SHADOWING_ITEMS if clip.audio_filename is not None]

    assert named, "시드에 오디오를 가진 클립이 0건이다 — 화면에 들려줄 소리가 없다"
    for clip in named:
        assert clip.audio_filename == f"{clip.id}.wav"


def test_seeded_clip_audio_files_exist_in_the_repository() -> None:
    """⛔ **이것이 「제품 자산이 배포되는가」를 재는 유일한 단정이다** (설계서 §7).

    파일이 있는 것과 **추적되는 것**은 다르므로 둘을 함께 잰다 — `.gitignore` 된 자리에 두면
    clone 한 환경에서 소리가 사라지고, 그 실패는 배포 뒤에야 드러난다.
    """
    root = (BACKEND_ROOT / get_settings().shadowing_clip_audio_root).resolve()

    for clip in SEED_SHADOWING_ITEMS:
        if clip.audio_filename is None:
            continue
        path = root / clip.audio_filename
        assert path.is_file(), f"{path} 가 없다 — 생성 절차는 선행 검토 §7.1 이 소유한다"
        ignored = subprocess.run(
            ["git", "check-ignore", "-q", str(path)],
            cwd=REPO_ROOT,
            check=False,
        )
        assert ignored.returncode == 1, f"{path} 가 .gitignore 에 걸려 있다 — 배포되지 않는다"
```

파일 맨 위에 경로 상수와 import 를 더한다.

```python
import subprocess
from pathlib import Path

# 이 파일에서 리포·백엔드 뿌리를 계산한다 — 설정의 상대경로가 백엔드 cwd 기준이기 때문이다.
BACKEND_ROOT = Path(__file__).resolve().parents[2] / "app" / "backend"
REPO_ROOT = Path(__file__).resolve().parents[2]
```

- [ ] **Step 3: 돌려서 실패를 확인한다**

Run: `cd app/backend && .venv/bin/pytest -c pyproject.toml ../../tests/unit/test_shadowing_seed.py -q`
Expected: FAIL — `AttributeError: 'ShadowingSeedClip' object has no attribute 'audio_filename'`

- [ ] **Step 4: 시드 상수와 insert 를 고친다**

`scripts/migrate.py` 의 `ShadowingSeedClip` 에 필드를 **`level` 앞**에 더하지 말고 **맨 뒤**에
더한다 — 필드 순서가 insert 컬럼 순서와 묶여 있으므로 컬럼 목록도 같은 자리에 더한다.

```python
class ShadowingSeedClip(NamedTuple):
    ...
    id: UUID
    source_title: str
    source_url: str | None
    transcript: str
    clip_start_sec: Decimal
    clip_end_sec: Decimal
    level: str
    # 합성음 파일명. `None` = 오디오가 아직 없는 클립. ⛔ 값역은 `<id>.wav` 이고 022 의
    # `shadowing_items_audio_filename_matches_id` 가 그것을 강제한다(`TASK-66` · 결정 90).
    audio_filename: str | None
```

상수의 그 행에 값을 넣는다. ⚠️ Step 1 에서 잰 길이가 16.64 와 다르면 `clip_end_sec` 도 그 값으로
고치고, 그 사실을 커밋 메시지와 태스크 노트에 적는다.

```python
        clip_start_sec=Decimal("0.00"),
        clip_end_sec=Decimal("16.64"),
        level="A2",
        audio_filename="00000000-0000-0000-0000-000000000201.wav",
```

`seed()` 의 쉐도잉 insert 를 고친다 — 컬럼 목록과 `values` 자리표시자, `do update` 절 셋 다.

```python
    for clip in SEED_SHADOWING_ITEMS:
        await conn.execute(
            """
            insert into shadowing_items
                (id, source_title, source_url, transcript,
                 clip_start_sec, clip_end_sec, level, audio_filename)
            values ($1, $2, $3, $4, $5, $6, $7, $8)
            -- (기존 주석 유지)
            on conflict (id) do update
               set source_title = excluded.source_title,
                   source_url = excluded.source_url,
                   transcript = excluded.transcript,
                   clip_start_sec = excluded.clip_start_sec,
                   clip_end_sec = excluded.clip_end_sec,
                   audio_filename = excluded.audio_filename
            """,
            *clip,
        )
```

- [ ] **Step 5: 돌려서 통과를 확인한다**

Run: `cd app/backend && .venv/bin/pytest -c pyproject.toml ../../tests/unit/test_shadowing_seed.py -q`
Expected: PASS 10건(기존 8 + 새 2).

- [ ] **Step 6: 판별력을 확인한다**

```bash
cd /Users/redstar/MyProject/OhMyEnglish
mv assets/clips/00000000-0000-0000-0000-000000000201.wav /tmp/clip.hold
cd app/backend && .venv/bin/pytest -c pyproject.toml ../../tests/unit/test_shadowing_seed.py -q 2>&1 | tail -3
# Expected: FAIL — 「… 가 없다」 메시지가 나온다
cd /Users/redstar/MyProject/OhMyEnglish && mv /tmp/clip.hold assets/clips/00000000-0000-0000-0000-000000000201.wav
cd app/backend && .venv/bin/pytest -c pyproject.toml ../../tests/unit/test_shadowing_seed.py -q 2>&1 | tail -2
# Expected: PASS 10건
```

- [ ] **Step 7: 커밋한다** — ⛔ 바이너리를 **경로로** 지목해 담는다

```bash
git add assets/clips/00000000-0000-0000-0000-000000000201.wav scripts/migrate.py tests/unit/test_shadowing_seed.py
git diff --cached --name-only
git commit -m "$(cat <<'EOF'
feat(TASK-66): 합성 클립 오디오를 리포에 담고 시드가 그것을 가리키게 했음

파일은 assets/clips/<id>.wav 이고 git 이 추적함(결정 90). 시드에 audio_filename 을 더해
022 의 CHECK 와 같은 규약을 상수에서도 지켰음.

단정 둘을 뒀음 — 파일명이 규약을 따르는가, 그리고 그 파일이 리포에 실제로 있고
.gitignore 에 걸리지 않는가. 후자가 「제품 자산이 배포되는가」를 재는 유일한 자리임.
판별력은 파일을 옮겨 red 를 보고 되돌려 확인했음.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: `services/clip_audio.py` — 바이트를 읽는 길

**Files:**
- Create: `app/backend/app/services/clip_audio.py`
- Test: `tests/unit/test_clip_audio.py`

**Interfaces:**
- Consumes: Task 1 의 `audio_filename` 컬럼 · Task 2 의 설정 키.
- Produces: `CLIP_AUDIO_MEDIA_TYPE = "audio/wav"` ·
  `clip_audio_path(root: Path, item_id: UUID) -> Path` ·
  `load_clip_audio(conn: asyncpg.Connection, root: Path, item_id: UUID) -> bytes | None`.

- [ ] **Step 1: 실패하는 단정 다섯을 쓴다**

```python
"""합성 클립 오디오를 읽는 길의 계약 (`TASK-66` · 설계서 §5).

⚠️ **`db_conn`(롤백 트랜잭션)만 쓴다** — 커밋된 행을 남기지 않는다. HTTP 표면은
`tests/integration/test_clip_audio_api.py` 가 `db_pool` 로 따로 잰다.
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

import asyncpg
import pytest
from app.services.clip_audio import CLIP_AUDIO_MEDIA_TYPE, clip_audio_path, load_clip_audio


async def _insert_clip(conn: asyncpg.Connection, *, with_audio: bool) -> UUID:
    item_id = await conn.fetchval(
        "insert into shadowing_items (source_title, transcript, clip_start_sec, "
        "clip_end_sec, level) values ('Morning', 'I wake up at seven.', 0, 16.64, 'A2') "
        "returning id"
    )
    if with_audio:
        await conn.execute(
            "update shadowing_items set audio_filename = $2 where id = $1",
            item_id,
            f"{item_id}.wav",
        )
    return item_id


def test_media_type_declares_wav_not_raw_pcm() -> None:
    """⛔ 학습자 낭독의 `audio/L16` 과 **다른 값이어야 한다** (설계서 §6).

    낭독은 헤더가 없어 표본율·채널을 Content-Type 이 말해야 하고 `fetch()` + `VoiceIo` 로만
    재생된다. 클립은 RIFF 헤더가 있어 `new Audio()` 가 그대로 디코드한다 — 그 차이가 프런트
    설계의 근거이므로 값이 섞이면 재생 경로가 조용히 틀어진다.
    """
    assert CLIP_AUDIO_MEDIA_TYPE == "audio/wav"


def test_path_is_built_from_the_id_not_from_a_stored_string(tmp_path: Path) -> None:
    """⛔ 경로 조립의 둘째 겹 — DB 문자열을 쓰지 않는다 (설계서 §5).

    022 의 CHECK 가 파일명을 id 로 강제하지만 방어를 겹으로 둔다. **서명이 파일명을 받지 않는 것**이
    그 성질을 타입으로 보장한다.
    """
    item_id = uuid4()

    assert clip_audio_path(tmp_path, item_id) == tmp_path / f"{item_id}.wav"


@pytest.mark.asyncio
async def test_loads_the_bytes_when_the_pointer_and_the_file_are_both_there(
    db_conn: asyncpg.Connection, tmp_path: Path
) -> None:
    item_id = await _insert_clip(db_conn, with_audio=True)
    (tmp_path / f"{item_id}.wav").write_bytes(b"RIFF----WAVEfmt ")

    assert await load_clip_audio(db_conn, tmp_path, item_id) == b"RIFF----WAVEfmt "


@pytest.mark.asyncio
async def test_returns_none_for_the_three_shapes_of_no_audio(
    db_conn: asyncpg.Connection, tmp_path: Path
) -> None:
    """접근 불가 세 형태가 전부 `None` 이다 — 라우터가 404 로 옮긴다.

    ⚠️ ①(행 없음)과 ②(포인터 null)는 `fetchval` 이 둘 다 `None` 을 주어 **한 갈래로 수렴한다.**
    그래도 둘을 따로 재는 것은 호출자에게 다른 상태이기 때문이다.
    """
    # ① 클립 행이 없다
    assert await load_clip_audio(db_conn, tmp_path, uuid4()) is None

    # ② 포인터가 null 이다 — 오디오를 아직 만들지 않은 클립
    silent_id = await _insert_clip(db_conn, with_audio=False)
    assert await load_clip_audio(db_conn, tmp_path, silent_id) is None

    # ③ 포인터는 있고 파일이 없다 — 배포에서 자산이 빠졌다
    orphan_id = await _insert_clip(db_conn, with_audio=True)
    assert await load_clip_audio(db_conn, tmp_path, orphan_id) is None


@pytest.mark.asyncio
async def test_does_not_expire_product_assets(
    db_conn: asyncpg.Connection, tmp_path: Path
) -> None:
    """⛔ 만료를 재지 않는다 — `load_recording` 과 갈라지는 자리다 (설계서 §5).

    낭독은 학습자의 당일이 지나면 `None` 이 되지만 클립은 제품 자산이라 시간에 따라 사라지지
    않는다. **세션 상태와 무관하게** 바이트가 나오는 것이 그 성질이다.
    """
    item_id = await _insert_clip(db_conn, with_audio=True)
    (tmp_path / f"{item_id}.wav").write_bytes(b"RIFF")
    await db_conn.execute(
        "update shadowing_items set created_at = now() - interval '400 days' where id = $1",
        item_id,
    )

    assert await load_clip_audio(db_conn, tmp_path, item_id) == b"RIFF"
```

- [ ] **Step 2: 돌려서 실패를 확인한다**

Run: `cd app/backend && .venv/bin/pytest -c pyproject.toml ../../tests/unit/test_clip_audio.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.clip_audio'`

- [ ] **Step 3: 모듈을 쓴다**

```python
"""합성한 쉐도잉 클립 오디오를 읽는 길 (`TASK-66` · 설계서 §5).

⛔ **학습자 낭독(`services/recordings.py`)과 합치지 않는다 — 수명주기가 반대다.** 낭독은 당일이
지나면 지워지는 개인정보이고(그 모듈의 만료·스윕), 클립 오디오는 리포와 함께 배포되는 **제품
자산**이라 지우는 경로가 없다. 한 모듈에 두면 만료 판정이 제품 자산으로 번질 자리가 생긴다.

**R10-7 예외의 경계는 이 docstring 이 아니라 022 의 CHECK 둘이 가둔다**
(`shadowing_items_audio_filename_matches_id` · `shadowing_items_audio_only_for_synthetic`) —
011 이 세운 방식이고 그 이유는 *"docstring 은 이 파일을 읽을 이유가 없는 사람을 구속하지
못한다"* 다.
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

import asyncpg

# WAV 는 RIFF 헤더가 표본율·채널을 싣는다 — 그래서 `new Audio()` 가 그대로 디코드한다.
# ⚠️ 낭독의 `RECORDING_MEDIA_TYPE`(`audio/L16; rate=16000; channels=1`)과 다른 이유가 이것이다:
# 그쪽은 헤더가 없어 파라미터를 Content-Type 이 말해야 하고 `fetch()` + `VoiceIo` 로만 재생된다.
CLIP_AUDIO_MEDIA_TYPE = "audio/wav"

_SELECT_CLIP_AUDIO_FILENAME_SQL = """
select audio_filename
  from shadowing_items
 where id = $1
"""


def clip_audio_path(root: Path, item_id: UUID) -> Path:
    """클립 오디오 파일의 자리. **파일명을 DB 에서 받지 않고 id 로 조립한다.**

    022 의 CHECK 가 `audio_filename = id::text || '.wav'` 를 강제하므로 두 값은 같다. 그래도
    조립을 id 로 하는 것은 방어를 겹으로 두는 것이다 — 한 겹이 뚫려도 다른 겹이 막아야 한다.
    ⛔ **이 함수에 파일명 인자를 더하지 마라.** 그 순간 DB 문자열이 경로에 닿는 길이 열린다.
    """
    return root / f"{item_id}.wav"


async def load_clip_audio(conn: asyncpg.Connection, root: Path, item_id: UUID) -> bytes | None:
    """클립 오디오 바이트. 접근 불가면 `None` — 예외를 던지지 않는다.

    **접근 불가가 세 형태로 실재한다**: ① 클립 행이 없다 ② `audio_filename` 이 null 이다(오디오를
    아직 만들지 않은 클립) ③ 포인터는 있고 파일이 없다(배포에서 자산이 빠졌다). 전부 404 로
    옮긴다 — `load_recording` 이 세운 규약과 같다.
    ⚠️ ①과 ②는 `fetchval` 이 둘 다 `None` 을 주어 **한 갈래로 수렴한다.**

    ⛔ **만료를 재지 않는다.** 제품 자산이라 「학습자의 당일이 지났다」가 없다 — `load_recording`
    과 갈라지는 자리이고, 여기에 만료를 더하면 배포된 자산이 시간에 따라 사라진다.
    """
    filename = await conn.fetchval(_SELECT_CLIP_AUDIO_FILENAME_SQL, item_id)
    if filename is None:
        return None
    path = clip_audio_path(root, item_id)
    if not path.is_file():
        return None
    return path.read_bytes()
```

- [ ] **Step 4: 돌려서 통과를 확인한다**

Run: `cd app/backend && .venv/bin/pytest -c pyproject.toml ../../tests/unit/test_clip_audio.py -q`
Expected: PASS 5건

- [ ] **Step 5: 커밋한다**

```bash
git add app/backend/app/services/clip_audio.py tests/unit/test_clip_audio.py
git diff --cached --name-only
git commit -m "$(cat <<'EOF'
feat(TASK-66): 클립 오디오를 읽는 모듈을 낭독과 «따로» 뒀음

수명주기가 반대라서 합치지 않았음 — 낭독은 당일이 지나면 지워지는 개인정보이고 클립은 리포와
함께 배포되는 제품 자산임. 그래서 load_clip_audio 는 만료를 재지 않고, 그 성질을 400일 지난
행으로 단정했음.

경로는 파일명이 아니라 item_id 로 조립함 — 022 의 CHECK 가 첫 겹이고 이 서명이 둘째 겹임.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: 엔드포인트 `GET /api/shadowing/clips/{item_id}/audio`

**Files:**
- Create: `app/backend/app/api/shadowing.py`
- Modify: `app/backend/app/api/main.py` (import 절 · `create_app` 의 `include_router` 묶음)
- Test: `tests/integration/test_clip_audio_api.py`

**Interfaces:**
- Consumes: Task 4 의 `load_clip_audio` · `CLIP_AUDIO_MEDIA_TYPE` · Task 2 의 설정 키.
- Produces: 라우터 객체 `app.api.shadowing.router`(prefix `/api/shadowing`) ·
  경로 `GET /api/shadowing/clips/{item_id}/audio`.

- [ ] **Step 1: 실패하는 API 단정 넷을 쓴다**

⚠️ **`api_client` 픽스처는 커밋된 행만 본다** — 라우터가 여는 커넥션이 테스트의 것과 다르므로
`db_conn`(롤백)이 아니라 `db_pool` 로 심고 스스로 지운다. 설정 주입은
`tests/integration/test_recording_api.py` 의 방식을 그대로 쓴다.

```python
"""클립 오디오 HTTP 표면의 계약 (`TASK-66` · 설계서 §5).

⚠️ 설정 뿌리를 `tmp_path` 로 갈아 끼우고 `get_settings.cache_clear()` 를 앞뒤로 부른다 —
`get_settings` 가 `@lru_cache` 라 지우지 않으면 다른 테스트의 뿌리가 남는다
(`tests/integration/test_recording_api.py` 가 세운 방식).
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from uuid import UUID, uuid4

import asyncpg
import httpx
import pytest
from app.config import get_settings


@pytest.fixture
def clip_audio_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[Path]:
    monkeypatch.setenv("SHADOWING_CLIP_AUDIO_ROOT", str(tmp_path))
    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()


@pytest.fixture
async def committed_clip(db_pool: asyncpg.Pool) -> AsyncIterator[UUID]:
    """커밋된 클립 1행 — 끝나면 지운다(`api_client` 가 커밋된 것만 보기 때문이다)."""
    async with db_pool.acquire() as conn:
        item_id = await conn.fetchval(
            "insert into shadowing_items (source_title, transcript, clip_start_sec, "
            "clip_end_sec, level) values ('Morning', 'I wake up at seven.', 0, 16.64, 'A2') "
            "returning id"
        )
        await conn.execute(
            "update shadowing_items set audio_filename = $2 where id = $1",
            item_id,
            f"{item_id}.wav",
        )
    yield item_id
    async with db_pool.acquire() as conn:
        await conn.execute("delete from shadowing_items where id = $1", item_id)


@pytest.mark.asyncio
async def test_serves_the_clip_bytes_as_wav(
    api_client: httpx.AsyncClient, committed_clip: UUID, clip_audio_root: Path
) -> None:
    (clip_audio_root / f"{committed_clip}.wav").write_bytes(b"RIFF----WAVEfmt ")

    response = await api_client.get(f"/api/shadowing/clips/{committed_clip}/audio")

    assert response.status_code == 200
    assert response.content == b"RIFF----WAVEfmt "
    # ⛔ `audio/L16` 이면 프런트의 `new Audio()` 가 디코드하지 못한다 — 값이 계약이다.
    assert response.headers["content-type"] == "audio/wav"


@pytest.mark.asyncio
async def test_returns_404_when_the_clip_does_not_exist(
    api_client: httpx.AsyncClient, clip_audio_root: Path
) -> None:
    response = await api_client.get(f"/api/shadowing/clips/{uuid4()}/audio")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_returns_404_when_the_file_is_missing(
    api_client: httpx.AsyncClient, committed_clip: UUID, clip_audio_root: Path
) -> None:
    """포인터만 있고 파일이 없는 상태 — 배포에서 자산이 빠졌을 때다. 500 이 아니다."""
    response = await api_client.get(f"/api/shadowing/clips/{committed_clip}/audio")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_rejects_a_path_shaped_item_id(
    api_client: httpx.AsyncClient, clip_audio_root: Path
) -> None:
    """⛔ 경로 이탈의 셋째 겹 — `UUID` 선언이 라우팅에서 막는다.

    `get_recording` 의 docstring 이 *"두 값이 `UUID` 로 선언된 것이 경로 탈출도 함께 막는다"* 로
    같은 성질을 이미 적었다.
    """
    response = await api_client.get("/api/shadowing/clips/..%2F..%2Fetc%2Fpasswd/audio")

    assert response.status_code in (404, 422)
```

- [ ] **Step 2: 돌려서 실패를 확인한다**

Run: `cd app/backend && .venv/bin/pytest -c pyproject.toml ../../tests/integration/test_clip_audio_api.py -q`
Expected: FAIL — 첫 테스트가 `200` 을 기대하는데 라우트가 없어 `404` 를 받는다.
⛔ **네 건 모두 통과로 나오면 멈춘다** — 404 를 기대하는 셋은 라우트가 없어도 통과하므로 첫 건의
빨강이 이 단계의 유일한 신호다.

- [ ] **Step 3: 라우터를 쓴다**

```python
"""쉐도잉 자원의 HTTP 표면 (`TASK-66` · 설계서 §5).

⛔ **`/api/sessions` 아래에 넣지 않는다** — 클립은 세션에 매인 것이 아니라 여러 세션이 공유하는
제품 자산이다. 낭독(`api/results.py:get_recording`)이 세션 경로 아래 있는 것은 그것이 학습자
개인의 것이고 **세션 경계가 개인정보 경계**이기 때문이다(그 docstring 이 근거를 가진다).
클립을 그 아래에 두면 없는 경계를 있는 것처럼 보이게 하고, 세션마다 같은 자산을 다른 URL 로
부르게 된다.
"""

from __future__ import annotations

from uuid import UUID

import asyncpg
from fastapi import APIRouter, HTTPException, Request, Response

from app.config import get_settings
from app.services.clip_audio import CLIP_AUDIO_MEDIA_TYPE, load_clip_audio

router = APIRouter(prefix="/api/shadowing", tags=["shadowing"])


@router.get("/clips/{item_id}/audio")
async def get_clip_audio(item_id: UUID, request: Request) -> Response:
    """합성한 클립 오디오 하나를 WAV 로 내보낸다.

    **판정은 서비스가 하고 여기서는 HTTP 로 옮기기만 한다** — `get_recording` 과 같은 규약이다.
    `load_clip_audio` 가 `None` 을 주는 세 경우(행 없음 · 포인터 null · 파일 없음)가 전부 404 다.
    ⚠️ `item_id` 가 `UUID` 로 선언된 것이 경로 탈출을 라우팅에서 막는다.
    """
    pool: asyncpg.Pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        audio = await load_clip_audio(conn, get_settings().shadowing_clip_audio_root, item_id)
    if audio is None:
        raise HTTPException(status_code=404, detail="clip audio not found")
    return Response(content=audio, media_type=CLIP_AUDIO_MEDIA_TYPE)
```

- [ ] **Step 4: 라우터를 앱에 등록한다**

`app/backend/app/api/main.py` 의 import 묶음(알파벳 순서 유지)과 `create_app` 을 고친다.

```python
from app.api.results import router as results_router
from app.api.shadowing import router as shadowing_router
from app.api.ws import router as ws_router
```

```python
    app.include_router(results_router)
    app.include_router(daily_router)
    app.include_router(shadowing_router)
    app.include_router(ws_router)
```

- [ ] **Step 5: 돌려서 통과를 확인한다**

Run: `cd app/backend && .venv/bin/pytest -c pyproject.toml ../../tests/integration/test_clip_audio_api.py -q`
Expected: PASS 4건

- [ ] **Step 6: 판별력을 확인한다 — 등록을 빼면 빨강이어야 한다**

```bash
cd /Users/redstar/MyProject/OhMyEnglish
cp app/backend/app/api/main.py /tmp/main.bak
/usr/bin/python3 - <<'PY'
import pathlib
p = pathlib.Path("app/backend/app/api/main.py"); s = p.read_text()
s2 = s.replace("    app.include_router(shadowing_router)\n", "")
assert s2 != s, "⛔ 변이가 적용되지 않았다 — 대상 줄이 안 맞았다"
p.write_text(s2)
PY
cd app/backend && .venv/bin/pytest -c pyproject.toml ../../tests/integration/test_clip_audio_api.py -q 2>&1 | tail -3
# Expected: FAIL — 첫 테스트가 404 를 받는다
cd /Users/redstar/MyProject/OhMyEnglish && cp /tmp/main.bak app/backend/app/api/main.py
diff -q /tmp/main.bak app/backend/app/api/main.py && echo "원본과 동일함"
cd app/backend && .venv/bin/pytest -c pyproject.toml ../../tests/integration/test_clip_audio_api.py -q 2>&1 | tail -2
# Expected: PASS 4건
```

- [ ] **Step 7: 커밋한다**

```bash
git add app/backend/app/api/shadowing.py app/backend/app/api/main.py tests/integration/test_clip_audio_api.py
git diff --cached --name-only
git commit -m "$(cat <<'EOF'
feat(TASK-66): 클립 오디오 엔드포인트를 세션 경로 «밖»에 뒀음

GET /api/shadowing/clips/{item_id}/audio 이고 응답은 audio/wav 임. 낭독이 /api/sessions 아래
있는 것은 세션 경계가 개인정보 경계이기 때문이고, 클립은 여러 세션이 공유하는 제품 자산이라
그 경계를 있는 것처럼 꾸미지 않았음.

StaticFiles 를 쓰지 않은 근거는 recording_url 주석이 이미 정한 방향임 — 파일 경로가 아니라
API 경로를 노출함. 404 셋과 UUID 선언의 경로 탈출 차단까지 단정을 뒀음.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: `has_audio` 를 `session_started` payload 에 싣기

**Files:**
- Modify: `app/backend/app/services/recordings.py` (`_SELECT_SESSION_CLIP_SQL` · `ShadowingClip` ·
  `load_session_clip` · `ShadowingTurns.as_event_payload`)
- Modify: `app/frontend/lib/ws.ts` (`ShadowingSetup`)
- Test: `tests/unit/test_recordings.py` (기존 클립 조회 절 이웃)

**Interfaces:**
- Consumes: Task 1 의 컬럼.
- Produces: `ShadowingClip.has_audio: bool` · payload 키 `"has_audio": bool` ·
  TS 필드 `ShadowingSetup.has_audio: boolean`.

- [ ] **Step 1: 실패하는 단정 둘을 쓴다**

`tests/unit/test_recordings.py` 의 `test_loading_the_clip_of_a_session_that_picked_one` 바로 뒤에
붙인다.

```python
@pytest.mark.asyncio
async def test_clip_reports_whether_its_audio_exists(db_conn: asyncpg.Connection) -> None:
    """화면이 재생 버튼을 보일지 정하는 신호 — 404 를 기다려 정하지 않는다 (설계서 §6).

    ⛔ **파일명을 프런트에 내려보내지 않는다.** 경로는 서버의 것이고, 프런트가 알아야 하는 것은
    「소리가 있는가」 하나다.
    """
    session_id = await _new_shadowing_session(db_conn)
    clip_id = await db_conn.fetchval(
        "insert into shadowing_items "
        "(source_title, transcript, clip_start_sec, clip_end_sec, level) "
        "values ('A morning routine', 'I usually wake up at seven.', 0, 16.64, 'A2') returning id"
    )
    await db_conn.execute(
        "update learning_sessions set shadowing_item_id = $2 where id = $1", session_id, clip_id
    )

    silent = await load_session_clip(db_conn, session_id)
    assert silent is not None
    assert silent.has_audio is False

    await db_conn.execute(
        "update shadowing_items set audio_filename = $2 where id = $1", clip_id, f"{clip_id}.wav"
    )

    loud = await load_session_clip(db_conn, session_id)
    assert loud is not None
    assert loud.has_audio is True


def test_event_payload_carries_has_audio_and_never_the_filename() -> None:
    """payload 의 **키 집합**이 계약이다 — 파일명이 새어 나가면 이 단정이 깨진다."""
    clip = ShadowingClip(
        id=UUID("00000000-0000-0000-0000-000000000201"),
        source_title="A morning routine",
        transcript="I usually wake up at seven.",
        clip_start_sec=Decimal("0.00"),
        clip_end_sec=Decimal("16.64"),
        has_audio=True,
    )

    payload = ShadowingTurns(
        clip=clip, audio_root=Path("/tmp"), playback_rate=1.5, repeat_count=3
    ).as_event_payload()

    assert payload["has_audio"] is True
    assert set(payload) == {
        "item_id",
        "source_title",
        "transcript",
        "clip_start_sec",
        "clip_end_sec",
        "playback_rate",
        "repeat_count",
        "has_audio",
    }
```

- [ ] **Step 2: 돌려서 실패를 확인한다**

Run: `cd app/backend && .venv/bin/pytest -c pyproject.toml ../../tests/unit/test_recordings.py -q -k has_audio`
Expected: FAIL — `TypeError: ShadowingClip.__init__() got an unexpected keyword argument 'has_audio'`

- [ ] **Step 3: 서비스를 고친다**

`_SELECT_SESSION_CLIP_SQL` 에 컬럼을 더한다.

```python
_SELECT_SESSION_CLIP_SQL = """
select i.id, i.source_title, i.transcript, i.clip_start_sec, i.clip_end_sec, i.audio_filename
  from learning_sessions s
  join shadowing_items i on i.id = s.shadowing_item_id
 where s.id = $1
"""
```

`ShadowingClip` 에 필드를 더한다.

```python
    id: UUID
    source_title: str
    transcript: str
    clip_start_sec: Decimal
    clip_end_sec: Decimal
    # 소리가 있는가. ⛔ **파일명이 아니라 불린이다** — 경로는 서버의 것이고 화면이 알아야 하는 것은
    # 「재생 버튼을 보일지」 하나다(`TASK-66` · 설계서 §6). `level` 을 담지 않은 것과 같은 규율이다:
    # 화면이 쓰지 않는 것을 싣지 않는다.
    has_audio: bool
```

`load_session_clip` 의 반환을 고친다.

```python
    return ShadowingClip(
        id=row["id"],
        source_title=row["source_title"],
        transcript=row["transcript"],
        clip_start_sec=row["clip_start_sec"],
        clip_end_sec=row["clip_end_sec"],
        has_audio=row["audio_filename"] is not None,
    )
```

`as_event_payload` 의 dict 마지막에 한 줄을 더한다.

```python
            "repeat_count": self.repeat_count,
            "has_audio": self.clip.has_audio,
```

- [ ] **Step 4: 프런트 타입을 고친다**

`app/frontend/lib/ws.ts` 의 `ShadowingSetup` 에 필드를 더한다.

```ts
  playback_rate: number;
  repeat_count: number;
  /**
   * 이 클립에 합성 오디오가 있는가. ⛔ **파일명이 아니다** — 경로는 서버의 것이고 화면은
   * 재생 버튼을 보일지만 정한다(`TASK-66` · 설계서 §6).
   */
  has_audio: boolean;
```

- [ ] **Step 5: 돌려서 통과를 확인한다 — 전체 게이트를 본다**

⛔ **여기서 전체를 돌린다.** `ShadowingClip` 을 직접 만드는 자리가 여럿이라 이웃이 깨진다.

```bash
cd app/backend && .venv/bin/pytest -q 2>&1 | tail -5
cd ../frontend && npx tsc --noEmit; echo "tsc exit=$?"
```

⚠️ **깨진 자리를 「내 변경이 틀렸다」로 읽지 않는다** — `ShadowingClip(...)` 을 만드는 테스트는
`has_audio=` 를 더해 고치는 것이 맞다(예상 자리: `tests/integration/test_gateway.py`).
개수를 세던 단정이 깨지면 갈래별로 좁힌다(`TASK-62` 에서 여섯이 그렇게 깨졌음).

- [ ] **Step 6: 커밋한다**

```bash
git add app/backend/app/services/recordings.py app/frontend/lib/ws.ts tests/unit/test_recordings.py
git diff --cached --name-only   # ⚠️ 깨져서 고친 테스트 파일이 있으면 그 경로도 함께 지목한다
git commit -m "$(cat <<'EOF'
feat(TASK-66): session_started 가 has_audio 를 실어 화면이 버튼을 정하게 했음

⛔ 파일명을 내려보내지 않음 — 경로는 서버의 것이고 화면이 알아야 하는 것은 「소리가 있는가」
하나임. payload 키 집합을 단정으로 못박아 파일명이 새는 것을 막았음.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: 최소 쉐도잉 화면 — 전사문과 재생

**Files:**
- Create: `app/frontend/app/ShadowingPanel.tsx`
- Modify: `app/frontend/app/page.tsx` (`handleServerEvent` 의 `session_started` 절 · 상태 하나 ·
  렌더 묶음)
- Test: 없음 — ⚠️ 프런트 테스트 인프라가 0이라 **브라우저 회차**가 이 태스크의 검증이다(설계서 §7).

**Interfaces:**
- Consumes: Task 5 의 경로 `GET /api/shadowing/clips/{item_id}/audio` · Task 6 의
  `ShadowingSetup.has_audio`.
- Produces: 컴포넌트 `ShadowingPanel({ setup }: { setup: ShadowingSetup })`.

- [ ] **Step 1: 컴포넌트를 쓴다**

⚠️ 스타일은 이 리포의 방식을 따른다 — `className` 을 쓰지 않고 인라인 `style` 에 `globals.css` 의
CSS 변수(`var(--foreground-muted)` 등)를 쓴다. ⛔ 색을 하드코딩하지 않는다(다크모드 위계가 뒤집힌
1차수 `F-1` 의 재발 방지).

```tsx
"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { ShadowingSetup } from "@/lib/ws";

// ⛔ 낭독 녹음·비교는 이 화면의 범위가 아니다(결정 90). 그래서 「녹음해 보세요」 같은 안내를
// 넣지 않는다 — 없는 기능을 있다고 알리는 것이 TASK-128.4 가 잡은 결함과 같은 부류다.
const PLAY_LABEL = "클립 듣기";
const PLAYING_LABEL = "재생 중…";
const NO_AUDIO_NOTICE = "이 클립은 소리가 아직 없어요";

export function ShadowingPanel({ setup }: { setup: ShadowingSetup }) {
  const [playing, setPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  // 남은 재생 횟수. ⚠️ 상태가 아니라 ref 인 것은 `ended` 핸들러가 최신 값을 읽어야 하기
  // 때문이다 — 상태로 두면 클로저가 옛 값을 본다.
  const remainingRef = useRef(0);

  const stop = useCallback(() => {
    const audio = audioRef.current;
    audioRef.current = null;
    if (audio) {
      audio.pause();
      audio.currentTime = 0;
    }
    remainingRef.current = 0;
    setPlaying(false);
  }, []);

  // 화면을 벗어나면 소리를 끈다 — 세션이 끝난 뒤 소리가 남으면 학습자가 껐다고 믿지 못한다.
  useEffect(() => stop, [stop]);

  const play = useCallback(() => {
    const audio = new Audio(`/api/shadowing/clips/${setup.item_id}/audio`);
    // 결정 6 의 값역(0.5~2.0배 · 1~10회)을 **브라우저 기능으로** 충족한다. 값은 서버가 설정에서
    // 읽어 payload 에 실어 보낸 것이고 화면이 고르지 않는다.
    audio.playbackRate = setup.playback_rate;
    remainingRef.current = setup.repeat_count;
    audio.addEventListener("ended", () => {
      remainingRef.current -= 1;
      if (remainingRef.current > 0) {
        void audio.play();
        return;
      }
      stop();
    });
    // ⚠️ 재생 실패(파일 없음 → 404)는 조용히 넘기지 않고 버튼을 되돌린다 — 「재생 중」이 영원히
    // 남으면 학습자가 기다린다.
    audio.addEventListener("error", stop);
    audioRef.current = audio;
    setPlaying(true);
    void audio.play().catch(stop);
  }, [setup.item_id, setup.playback_rate, setup.repeat_count, stop]);

  return (
    <section style={{ marginTop: "2rem" }}>
      <h2 style={{ fontSize: "1rem", marginBottom: "0.25rem" }}>{setup.source_title}</h2>
      <p style={{ color: "var(--foreground-muted)", marginTop: 0, marginBottom: "0.75rem" }}>
        {setup.transcript}
      </p>
      {setup.has_audio ? (
        <button type="button" onClick={playing ? stop : play} style={{ padding: "0.5rem 1rem" }}>
          {playing ? PLAYING_LABEL : PLAY_LABEL}
        </button>
      ) : (
        <p style={{ color: "var(--foreground-muted)", margin: 0 }}>{NO_AUDIO_NOTICE}</p>
      )}
    </section>
  );
}
```

- [ ] **Step 2: `page.tsx` 에 배선한다**

상태를 하나 더한다(다른 `useState` 들 이웃).

```tsx
  // 서버가 고른 쉐도잉 클립. ⛔ **키의 부재는 「쉐도잉 세션이 아니다」다** — 발음 축의
  // `pronunciation_focus` 주석이 세운 규약과 같아서 요청하지 않은 세션에서는 건드리지 않는다.
  const [shadowing, setShadowing] = useState<ShadowingSetup | null>(null);
```

`import` 에 타입과 컴포넌트를 더한다.

```tsx
import { ShadowingPanel } from "./ShadowingPanel";
import {
  SessionSocket,
  type PronunciationOutcome,
  type ServerEvent,
  type ShadowingSetup,
  type Speaker,
} from "@/lib/ws";
```

`handleServerEvent` 의 `session_started` 절에 한 줄을 더한다.

```tsx
        case "session_started":
          sessionIdRef.current = event.session_id;
          setShadowing(event.shadowing ?? null);
```

세션이 끝나는 자리(`stopMedia` 를 부르는 흐름)에서 함께 비운다.

```tsx
  const stopMedia = useCallback(() => {
    setShadowing(null);
    const voice = voiceRef.current;
```

렌더 묶음의 세션 진행 절에 패널을 넣는다.

```tsx
          {shadowing ? <ShadowingPanel setup={shadowing} /> : null}
```

- [ ] **Step 3: 게이트를 돌린다**

```bash
cd app/frontend && npx tsc --noEmit; echo "tsc exit=$?"
npm run lint; echo "eslint exit=$?"
```
Expected: 둘 다 `exit=0`

- [ ] **Step 4: 브라우저 회차로 실제 소리를 확인한다 — 검증 전용 스택**

⛔ **dev DB 를 쓰지 않는다.** 검증 전용 DB 를 만들어 022 까지 적용하고 시드를 넣은 뒤 확인하고
지운다(착수 전 필수 §5 의 규약).

```bash
# ① 검증 전용 DB — 소유자를 ohmy 로 만든다(H-AT)
/opt/homebrew/opt/postgresql@17/bin/createdb -h localhost -p 5432 -U ohmy ohmy_clipcheck
# ② 마이그레이션 + 시드 (이 DB 에만)
cd app/backend && DATABASE_URL=postgresql://ohmy:ohmy@localhost:5432/ohmy_clipcheck \
  WORKER_ENABLED=false .venv/bin/python ../../scripts/migrate.py
DATABASE_URL=postgresql://ohmy:ohmy@localhost:5432/ohmy_clipcheck \
  /opt/homebrew/opt/postgresql@17/bin/psql -h localhost -p 5432 -U ohmy -d ohmy_clipcheck \
  -tAc "select id, clip_end_sec, audio_filename from shadowing_items;"
# ③ 백엔드·프런트를 띄우고 쉐도잉 세션을 열어 「클립 듣기」를 눌러 소리를 듣는다
# ④ 끝나면 죽이고 지운다
/opt/homebrew/opt/postgresql@17/bin/dropdb -h localhost -p 5432 -U ohmy ohmy_clipcheck
# ⑤ dev DB 무오염을 조회로 확인한다
PGPASSWORD=ohmy /opt/homebrew/opt/postgresql@17/bin/psql -h localhost -p 5432 -U ohmy \
  -d ohmyenglish -tAc "select filename from schema_migrations order by filename desc limit 2;"
```

⛔ **확인할 것 넷을 사람이 직접 본다**: 소리가 나는가 · 전사문이 화면에 있는가 ·
`playback_rate`·`repeat_count` 가 설정대로 걸리는가 · 오디오 없는 클립에서 버튼이 숨는가.
⚠️ **소리를 들은 사람의 판정을 적는다** — 선행 검토 §8 이 「사람 청취가 아니다」를 미판정으로
남겼으므로 이 회차가 그것을 처음 닫는다.

- [ ] **Step 5: 회차 기록을 남기고 커밋한다**

기록은 `runs/2026-09-14-task66-clip-audio/` 에 둔다(스크린샷·조회 출력·사람 판정).

```bash
git add app/frontend/app/ShadowingPanel.tsx app/frontend/app/page.tsx
git diff --cached --name-only
git commit -m "$(cat <<'EOF'
feat(TASK-66): 최소 쉐도잉 화면을 붙여 클립 소리를 실제로 들려줌

session_started 의 shadowing 을 읽는 코드가 0곳이던 것을 이 커밋이 채움. 재생은 new Audio()
이고 playbackRate 와 ended 반복으로 결정 6 의 값역을 충족함 — 값은 서버가 실어 보낸 것이고
화면이 고르지 않음.

⛔ 낭독 녹음·비교는 범위 밖이라 진입 안내도 넣지 않았음(결정 90) — 없는 기능을 있다고 알리지
않기 위함임. 오디오가 없는 클립에서는 버튼을 숨기고 안내 문구를 보임.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: 문서와 원장 마감 (AC#5)

**Files:**
- Modify: `docs/design/2026-09-09-shadowing-synthetic-clip-review.md` (§7.4)
- Modify: `backlog/tasks/task-66 - …md` (AC 체크 · 노트)

- [ ] **Step 1: 선행 검토 §7.4 의 마지막 줄을 채운다**

`### 7.4 아직 정해지지 않은 것` 절 끝에 붙인다.

```markdown
> ### ✅ 닫혔음 — `TASK-66` · 결정 90 (2026-09-14)
>
> 파일은 **`assets/clips/<클립 id>.wav`** 이고 **git 이 추적함**(제품 자산이므로 리포와 함께
> 배포됨). DB 는 `shadowing_items.audio_filename` 으로 그 파일명을 가리키고, 022 의 CHECK 가
> `audio_filename = id::text || '.wav'` 를 강제해 **규약이 스키마에 새겨짐.**
> ⛔ 학습자 낭독 뿌리(`shadowing_audio_root`)를 재사용하지 않음 — 그 뿌리는 스윕이 순회하며
> 걷으므로 제품 자산이 지워질 수 있음. 새 설정 키는 `shadowing_clip_audio_root` 임.
> 설계 정본은 `2026-09-14-shadowing-clip-audio-design.md` 임.
```

- [ ] **Step 2: 원장의 AC 를 체크하고 노트를 남긴다**

```bash
backlog task edit TASK-66 --check-ac 1 --check-ac 2 --check-ac 4 --check-ac 5 \
  --append-notes "완료 2026-09-14 — 결정 90 의 넷을 그대로 구현했음. 게이트 실측과 브라우저 회차 결과를 여기에 적는다."
backlog task edit TASK-66 -s Done
```

⛔ **게이트 수치를 「적었다」로 대신하지 않는다** — 그 턴에 직접 돌린 출력을 노트에 붙인다.

- [ ] **Step 3: 커밋한다**

```bash
git add docs/design/2026-09-09-shadowing-synthetic-clip-review.md "backlog/tasks/task-66 - 구현-합성한-쉐도잉-클립-오디오를-담을-자리를-만든다-—-지금-스키마에-자리가-0이다.md"
git diff --cached --name-only
git commit -m "$(cat <<'EOF'
docs(TASK-66): AC#1·#2·#4·#5 를 닫고 선행 검토의 미정 절을 채웠음

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: dev DB 에 022 를 적용한다 — ⛔ **승인 없이 착수하지 않음**

**Files:** 없음(운영 조작임).

⛔ **이 태스크는 사용자 승인이 선행 조건이다.** 지금 dev DB 는 `019` 까지 적용돼 있고 **020(발음
축)·021(내 것)이 미적용**이라, 022 를 적용하려면 그 둘의 순서와 소유가 함께 걸린다 — 발음 축과의
조율이 필요하다.

- [ ] **Step 1: 적용 전 상태를 기록한다**

```bash
PGPASSWORD=ohmy /opt/homebrew/opt/postgresql@17/bin/psql -h localhost -p 5432 -U ohmy \
  -d ohmyenglish -tAc "select filename from schema_migrations order by filename;"
PGPASSWORD=ohmy /opt/homebrew/opt/postgresql@17/bin/psql -h localhost -p 5432 -U ohmy \
  -d ohmyenglish -tAc "select count(*) from shadowing_items;"
```

- [ ] **Step 2: 011 의 적용 5단계를 그대로 따른다**

① `pg_dump -n public` 으로 백업한다(⚠️ `-n public` 을 빼면 공유 인스턴스의 다른 스키마에서
`permission denied` 로 막힌다) ② 표별 행 수를 기록한다 ③ 적용한다 ④ 재조회로 대조하고 출력을 태스크
노트에 남긴다 ⑤ 어긋나면 **멈추고 사용자에게 올린다.**

- [ ] **Step 3: 적용 뒤 실측을 원장에 남긴다**

`schema_migrations` 에 `022_shadowing_clip_audio.sql` 이 있는지, 그리고 시드 행의
`audio_filename` 이 채워졌는지를 **조회 출력으로** 남긴다. ⛔ `migrate.py` 는 이미 적용된 파일에
아무 것도 출력하지 않으므로 출력만 보고 판정하지 않는다.

---

## 자가 검토 — 계획을 설계서와 대조함

**설계서 절별 대응**: §3 스키마 → Task 1 · §4 파일과 설정 → Task 2·3 · §5 엔드포인트 → Task 4·5 ·
§6 화면 → Task 6·7 · §7 테스트 축 → Task 1·3·4·5·6 의 단정과 Task 7 의 회차 · §8 되돌리기 → Task 9
의 5단계가 백업으로 덮음 · §9 선행과 위험 → Task 3 Step 1(TTS 회차) · Task 9(dev DB 승인) ·
§10 확인하지 못한 것 → Task 7 Step 4 가 사람 청취를 처음 닫음.

**빠진 자리 하나를 적어 둠**: 설계서 §8 의 되돌리기 SQL 을 **별 태스크로 두지 않았음.** 되돌림은
사고 대응이고 계획의 산출물이 아니므로 설계서 §8 이 소유함 — 계획에 태스크로 넣으면 「되돌리기를
실행한다」가 할 일 목록에 남아 오독됨.

**이름 대조**: `audio_filename`(컬럼·시드 필드·TS 없음) · `has_audio`(파이썬 필드·payload 키·TS
필드) · `shadowing_clip_audio_root`(설정 키·환경변수 `SHADOWING_CLIP_AUDIO_ROOT`) ·
`clip_audio_path`·`load_clip_audio`·`CLIP_AUDIO_MEDIA_TYPE`(모듈 심볼) ·
`shadowing_items_audio_filename_matches_id`·`shadowing_items_audio_only_for_synthetic`(제약) —
Task 사이에서 같은 철자를 씀.

