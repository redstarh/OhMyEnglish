# 쉐도잉 과제 설계 — `shadowing_items` · 오디오 저장 예외 · 당일 경과 삭제 (TASK-27)

> **이 문서는 설계만 담는다.** 코드도 마이그레이션 SQL 파일도 만들지 않았다 — 아래 SQL은
> **명세**이고, 파일로 쓰는 조건은 §9가 정한다.
>
> **소유 범위**: `TASK-27` AC **#1·#2·#3·#4·#7**. **AC#5·#6은 범위 밖이고 §12가 그 이유와
> 소유자를 적는다.**
>
> **재론하지 않는 것**: 쉐도잉이 MVP 범위인지 · 진행 순서 · 자료 출처 · 자동수집 비범위 ·
> 오디오 저장 예외를 열지 · 보존 기간 · 재생 속도와 반복 횟수의 값역. 전부 이미 결정됐다(§1).
>
> ⚠️ **이 문서의 수치·값역·제약은 이 세션에서 직접 조회하거나 파일을 열어 확인한 것만 적었다.**
> 계산값과 인용된 값을 물려받은 곳은 없다.

---

## §1. 이미 결정된 것 — 이 설계의 입력

| 무엇 | 결정 | 어디가 소유하나 |
|---|---|---|
| 쉐도잉은 MVP 범위다 | 범위 안 | `docs/PRD.md` §4 MVP 6번 |
| 진행 순서 | 듣기 → 따라 말하기 → **녹음 비교** → 본인 상황으로 바꿔 말하기 | `docs/PRD.md` §7 「Shadowing & Content」 |
| 자료 | 30~90초 짧은 클립 · **외부 영상은 메타데이터·링크만** · 사용자가 선택한 것만 | 같은 절 |
| 자동 수집은 하지 않는다 | 비범위 | `docs/PRD.md` §5 |
| 학습자 오디오 저장 | **예외를 연다** (R10-7의 *"기본"* 저장 안 함에 대한 예외) | `2026-09-06-captain-decisions.md` §1 항목 6 |
| 보존 기간 | **비교된 오디오는 당일이 지나면 삭제한다** | 같은 곳 |
| 재생 속도 · 반복 횟수 | **0.5~2.0배** · **1~10회**, 설정값으로 관리 | 같은 곳 |
| `mode` 파라미터화의 소유자 | **`TASK-27`** — "첫 소비자가 생길 때" | 같은 문서 결정 11 |

**결정 11이 이 설계에서 발화한다.** 쉐도잉 세션은 `learning_sessions.mode = 'shadowing'`으로
열려야 하고, 지금 `_CREATE_SESSION_SQL`은 `'speaking'`을 **리터럴로 박아** 두고
(`app/backend/app/services/sessions.py:73`) `create_session`은 `user_id` 하나만 받는다(`:312` —
둘 다 이 세션에서 직접 열어 확인). → **이 설계가 결정 11이 예고한 「첫 소비자」다.** §7이 요구사항만
적고 구현은 §12로 넘긴다.

---

## §2. 데이터 우선 1단계 — 기존 스키마 실측 (직접 조회)

`docs/ops/data-first-design-convention.md` §1이 요구하는 "파일만 읽지 않는다"를 지켰다.
아래는 `ohmyenglish` DB에 **지금 있는 것**이다.

| 조회 | 결과 |
|---|---|
| 적용된 마이그레이션 | `001 · 003 · 004 · 005 · 006 · 007 · 009` — **008은 비어 있다** |
| 표 개수 | 16 (`shadowing_items` 없음) |
| `users.timezone` | `text not null default 'Asia/Seoul'` · 실제 값 `Asia/Seoul` 1건 |
| `utterances` 행 수 | **114** · 그중 `audio_url is not null` = **0** |
| `learning_sessions` 행 수 | 12 |

**AC#7 — 값역 3종은 이미 열려 있다** (`pg_get_constraintdef`로 직접 확인, 넓히지 않는다):

| 제약 | 현재 값역 |
|---|---|
| `review_tasks_task_type_check` | `rephrase` · `role_play` · **`shadowing`** |
| `learning_scenarios_category_check` | `daily_life` · `business` · **`shadowing`** |
| `learning_sessions_mode_check` | `speaking` · **`shadowing`** · `review` |

→ **AC#7 충족: 이 설계는 이 셋을 건드리지 않는다.** 마이그레이션도 필요 없다.

**`audio_url`의 재사용은 규약이 이미 정했다.** `data-first-design-convention.md` §2가
*"컬럼이 있는데 아무도 쓰지 않는다 → **재사용한다**"*로 판정하고 **`audio_url`을 실측 사례로
직접 지목**한다. 위 조회(114행 중 0건)가 그 전제를 재확인했다. → **새 컬럼을 만들지 않는다.**

**`utterances.audio_url`의 삭제 계약도 이미 있다** — `docs/database-schema.md` 「개인정보 원칙」:
*"사용자가 삭제하면 즉시 접근 불가 처리한다(객체 스토리지 삭제 + `audio_url = NULL` 갱신)"*.
§6의 삭제 순서가 이 문장을 그대로 따른다.

---

## §3. `shadowing_items` (AC#1)

### 3.1 문서가 이미 예약한 컬럼을 그대로 쓴다

`docs/database-schema.md`의 「아직 SQL에 존재하지 않는 테이블」 절이 이 표를
**`id`, `source_title`, `source_url`, `transcript`, `clip_start_sec`, `clip_end_sec`, `level`**로
이미 지정했다. **발명하지 않고 그 목록을 그대로 쓰고**, 더한 것은 `created_at` 하나다(전역 규약:
이벤트 시각은 `timestamptz`).

### 3.2 한 행은 무엇인가 — **클립 1개** (유도 1, §11)

`clip_start_sec`/`clip_end_sec`는 **출처 안에서의 시간 창**이고, PRD가 말하는 "30~90초 클립"이
그 창이다. 문장 단위 제공(PRD §7)은 `transcript`를 **런타임에 문장으로 쪼개** 만든다 —
문장 색인을 저장하지 않는 근거는 §11 유도 2.

### 3.3 명세 — `011_shadowing_items.sql` (번호 근거는 §3.5)

```sql
-- 학습자가 고른 쉐도잉 클립. 저작물 전체를 저장하지 않는다(PRD §5) — 링크와 시간 창만 담는다.
create table shadowing_items (
  id uuid primary key default gen_random_uuid(),
  source_title text not null check (length(btrim(source_title)) > 0),
  -- null = 내장·직접 입력 자료. 외부 영상은 링크만 보관한다(PRD §7).
  source_url text,
  -- 클립의 전사문. 문장 단위 제공은 이 값을 런타임에 쪼개 만든다(§3.2).
  transcript text not null check (length(btrim(transcript)) > 0),
  -- 출처 안에서의 시간 창. numeric(6,2) = 최대 9999.99초까지 담는다.
  clip_start_sec numeric(6, 2) not null check (clip_start_sec >= 0),
  clip_end_sec   numeric(6, 2) not null,
  -- learning_scenarios.level과 같은 값역을 쓴다 — 선택의 기준이 같기 때문이다.
  level text not null check (level in ('A1', 'A2', 'B1', 'B2', 'C1', 'C2')),
  created_at timestamptz not null default now(),
  constraint shadowing_items_span_ordered check (clip_end_sec > clip_start_sec),
  -- PRD §7이 정한 클립 길이 상한(90초). 발명값이 아니라 요구사항이다.
  constraint shadowing_items_span_within_limit check (clip_end_sec - clip_start_sec <= 90)
);

-- 뜨거운 조회는 「학습자 수준에 맞는 클립 고르기」 하나다(§9의 소비자 1).
create index shadowing_items_level_idx on shadowing_items (level);

-- 세션이 고른 클립. scenario_id와 정확히 같은 자리·같은 모양이다(nullable FK).
-- 이것이 「코드는 있는데 저장할 자리가 없다」를 막는다 — 선택이 재접속에서 살아남는다.
alter table learning_sessions
  add column shadowing_item_id uuid references shadowing_items (id) on delete set null;

-- 클립은 쉐도잉 세션에만 붙는다. 역방향(mode='shadowing'이면 반드시 클립)은 강제하지 않는다 —
-- 클립을 고르기 전에 세션이 열릴 수 있다.
alter table learning_sessions
  add constraint learning_sessions_shadowing_item_requires_mode
  check (shadowing_item_id is null or mode = 'shadowing');
```

**`learning_scenarios`에 얹지 않은 이유**: 그 표는 역할극 `prompt_template`을 담고
`source_url`·시간 창·전사문을 담을 자리가 없다. `category`에 `shadowing`이 열려 있다는 것이
같은 표를 쓰라는 뜻은 아니다 — 개념이 다르므로 `data-first` §2의 **CREATE**에 해당한다.

### 3.4 예시 행 (데이터 우선 3단계)

| `source_title` | `source_url` | `transcript` | `clip_start_sec` | `clip_end_sec` | `level` |
|---|---|---|---|---|---|
| `Standup: blocker 공유` | `null` | `I hit a blocker on the auth migration. I'll need one more day. …` | `0.00` | `42.50` | `B1` |
| `Conference talk — retro` | `https://…` | `The first thing we changed was the review cadence. …` | `312.00` | `380.00` | `B2` |

두 행 모두 요구사항을 만족한다: 30~90초 창 · 링크만 보관 · 수준으로 선택 가능.

### 3.5 마이그레이션 번호 — **011** (처음 고른 `010`은 이미 임자가 있다)

- **002를 되살리지 않는다.** 이미 적용된 `003`보다 앞으로 정렬되어 새 DB와 기존 DB의 적용
  순서가 갈라진다(`data-first` §2 · 결정 문서 §3 유도 1).
- ⛔ **008·002 는 결정 27 로 「영구 결번」이 됐다** (2026-09-08). `008` 은 `TASK-26` **예약**이었으나
  009·010 이 먼저 나가 적용 순서가 갈라지는 것이 실측으로 확인돼 예약을 풀었다. `009` 는 적용됨.
  ⛔ **앞으로 번호를 미리 예약하지 않는다** — 발급은 그 마이그레이션을 **실제로 쓰는 턴**에 한다.
- ⛔ **`010`은 `TASK-12`(복습 이력)가 먼저 가져갔다.** 이 문서의 첫 판은 `010`을 골랐고
  **그것이 틀렸다** — 커밋 `f695fb8`(`docs/design/2026-09-08-review-task-history-design.md` §5.1)이
  내 커밋보다 **먼저** 들어왔고 같은 번호를 지정했다. 그쪽 번호를 물러나게 할 이유가 없다:
  그 설계는 `review_tasks`의 유일키 교체와 **기존 행 이관**을 그 번호에 걸어 두었고,
  *"지우고 다시 만들기가 공짜인 마지막 순간"*이라는 시점 논거를 갖는다. → **이 설계가 `011`로 옮긴다.**
- ✅ ~~**`011`도 확정이 아니다** — 008 이동안이 승인되면 `012`가 된다~~ → ⛔ **이 서술은 거짓이 됐다**
  (2026-09-08 · **결정 27**). 008 이동안이 아니라 **008 예약 자체가 풀렸다**(영구 결번) → **`011`이
  확정이다.** ⚠️ 다만 **번호를 지금 믿지 말고 쓰는 턴에 `ls db/migrations/` 로 최대값을 다시
  확인한다** — 그것이 결정 27 이 세운 규칙이고, 이 문단이 겪은 충돌(`010`을 두 태스크가 골랐다)을
  구조적으로 막는 유일한 방법이다. **2026-09-08 실측 최대값은 `010`이다**(적용까지 끝났다).
- ✅ **번호가 어디로 가도 이 설계의 내용은 바뀌지 않는다.** `011`이 건드리는 것은
  `utterances`·`learning_sessions`이고 `TASK-12`의 `010`은 `review_tasks`다 — **서로 독립**이라
  적용 순서가 결과를 바꾸지 않는다(둘을 직접 대조해 확인했다).

**008이 나중에 들어올 때의 순서 갈라짐** — `009_drill_turns.sql`의 정정 상자가 소유하는 기전이
이 파일에도 그대로 적용된다. 이 DB는 `009 → 010 → 011 → (나중에) 008` 순으로 적용하고 새 DB는
`008 → 009 → 010 → 011` 순으로 적용한다. **무해할 조건을 여기 못 박는다**:

> **`008`은 `learning_sessions`에 `shadowing_item_id`라는 이름의 컬럼을 더하지 않아야 하고,
> `shadowing_items`·그 FK·위 CHECK·`utterances`의 값역에 의존하지 않아야 한다.**

✅ **이 절의 전제가 사라졌다** (2026-09-08 · 결정 27): **008 은 영구 결번이므로 「나중에 들어올
008」이 없다.** 위 조건은 이제 이행할 대상이 아니라 **왜 번호 예약을 그만두었는지의 기록**이다 —
`TASK-26`(주간 리포트)은 쓰는 턴에 새 번호를 받는다. ⛔ 지우지 마라: 예약이 만든 순서 갈라짐이
어떤 모양이었는지가 그 규칙의 근거다.

---

## §4. 학습자 오디오 저장 위치·경로 (AC#2)

### 4.1 무엇이 표시가 되는가 — `utterance_type`에 값을 하나 더한다

`audio_url`을 재사용하기로 정했으므로(§2) 남는 문제는 **"어떤 발화의 오디오를 저장하는가"를
스키마가 어떻게 아는가**다. CHECK는 행 지역이라 세션의 `mode`를 볼 수 없다 → 표시가 행에 있어야
한다. **`utterances.utterance_type`에 `shadowing_recording`을 더한다.**

**이 선택의 결정적 근거는 「공짜로 얻는 것」이다 — 직접 grep해 확인한 4자리:**

| 자리 | 무엇을 하나 |
|---|---|
| `services/utterances.py:161-162` | 분석 묶음 경계를 `speaker='user' and utterance_type='learning'`으로 센다 |
| `services/analysis.py:223,238` | 같은 조건으로 분석 대상을 고른다 |
| `services/results.py:177` | 결과 화면의 교정 대상을 `utterance_type='learning'`으로 거른다 |
| `services/plan_input.py:53` | 다음 세션 계획의 입력을 같은 조건으로 거른다 |

→ **새 값을 쓰면 쉐도잉 낭독이 오류 분석·교정 표시·계획 입력에서 자동으로 빠진다. 코드 변경 0.**
반대로 `learning`으로 저장하면 **학습자가 짓지 않은 문장이 학습자의 오류 패턴을 오염시킨다** —
쉐도잉은 남의 문장을 따라 읽는 것이므로 그 문장의 문법은 학습자의 것이 아니다. 이것이
`voice_command`를 분석에서 뺀 것과 **같은 종류의 이유**다.

⚠️ **이것은 값역 확장이고 `data-first` §2가 「가장 위험한 형태」로 지목한 DROP → ADD다**
(114행이 든 표의 규칙을 바꾼다). **되돌리기 스크립트를 함께 명세한다**(§4.5). AC#7이 금지한 것은
`task_type`·`category`·`mode` 3종이고 `utterance_type`은 그 목록에 없다 — **AC#7 위반이 아니다.**

### 4.2 R10-7의 예외를 스키마가 가둔다

```sql
-- 값역 확장 (DROP → ADD — data-first §5의 절차를 따른다).
alter table utterances drop constraint utterances_utterance_type_check;
alter table utterances add constraint utterances_utterance_type_check
  check (utterance_type in
         ('learning', 'voice_command', 'command_confirmation', 'shadowing_recording'));

-- R10-7 예외의 경계를 스키마에 새긴다: 오디오가 있으면 그것은 **학습자의 쉐도잉 낭독**이다.
-- 캡틴이 연 예외는 이 하나이고, 다른 오디오가 조용히 쌓이는 길을 여기서 막는다.
alter table utterances
  add constraint utterances_audio_only_for_shadowing
  check (audio_url is null
         or (utterance_type = 'shadowing_recording' and speaker = 'user'));

-- 삭제 스윕과 고아 파일 정리가 도는 유일한 조회. 부분 인덱스라 지금 크기가 0이다.
create index utterances_stored_audio_idx
  on utterances (session_id, created_at)
  where audio_url is not null;
```

### 4.3 저장 위치 — 리포루트 `assets/audio/`

**`.gitignore`가 이미 이 자리를 예약해 두었다**(`:32` — 주석이 *"음성 녹음은 opt-in이며
저장소에 넣지 않는다"*라고 적혀 있다). 발명하지 않고 그 자리를 쓴다.

⛔ **실측한 함정 — 경로 철자가 하나뿐이다.** `git check-ignore`를 직접 돌린 결과:

| 경로 | 판정 |
|---|---|
| `assets/audio/x.pcm` | **IGNORED** (`.gitignore:32`) |
| `app/backend/assets/audio/x.pcm` | **NOT ignored** |
| `data/local/x.pcm` | IGNORED |

`assets/audio/`는 슬래시를 포함하므로 **리포루트에만 앵커**된다. 백엔드 프로세스의 cwd는
`app/backend`이므로(`docs/ops/local-run.md`: `cd app/backend && .venv/bin/uvicorn …`)
기본값을 `assets/audio`로 두면 녹음이 **추적 대상 디렉터리**에 떨어진다. → 기본값은
**`../../assets/audio`**여야 한다. cwd 상대 해석은 이 프로젝트의 기존 관례다(`.env.example`
머리말: *"Settings() reads `.env` relative to the backend process's cwd"*).

### 4.4 경로와 `audio_url`의 값 — DB에 파일 경로를 담지 않는다

| 항목 | 값 |
|---|---|
| 뿌리 | `Settings.shadowing_audio_root` (기본 `../../assets/audio`) |
| 파일 | `<뿌리>/<session_id>/<utterance_id>.pcm` |
| 형식 | **raw LPCM 16kHz · 16bit · mono** — 변환 없음 |
| `audio_url` 값 | `/api/sessions/<session_id>/recordings/<utterance_id>` |
| 서빙 | `GET /api/sessions/{session_id}/recordings/{utterance_id}` (`api/results.py`의 라우터, prefix `/api/sessions`) |
| Content-Type | `audio/L16; rate=16000; channels=1` |

- **형식을 정하지 않고 이미 있는 것을 쓴다.** 프론트가 `AudioWorklet`으로 raw LPCM
  16kHz/16bit/mono를 만들어 base64로 보내고(`app/frontend/lib/audio.ts` · `page.tsx`),
  서버는 `SessionRunner._forward_audio`에서 그 프레임을 받는다. **저장은 그 바이트를 그대로
  파일에 흘리는 것이고 인코딩 의존성이 새로 생기지 않는다.** 확장자를 `.pcm`으로 둔 이유는
  헤더가 없기 때문이다(`lib/audio.ts`가 그 사실을 이미 문서화한다).
- **`audio_url`은 파일 경로가 아니라 API 경로다.** 파일 위치는 `(session_id, utterance_id)`에서
  결정론적으로 유도되므로 **뿌리를 옮겨도 저장된 행이 무효가 되지 않는다** — 뿌리는 설정이고
  데이터가 아니다. 그리고 컬럼 이름(`audio_url`)과 `database-schema.md`의 계약("접근 불가
  처리")이 그대로 성립한다.
- **재생은 `<audio src>`가 아니다.** 헤더 없는 PCM은 `new Audio()`로 디코드되지 않는다
  (`lib/audio.ts`가 실측으로 적어 둔 사실). 프론트는 `fetch()`로 바이트를 받아 이미 가진
  재생 큐(`VoiceIo`)에 넣는다 — 재생 속도 조절(§7)도 그 큐가 소유한다.
- **라우트 등록 순서**: `api/results.py`는 리터럴 경로(`/next-plan`)를 파라미터 경로보다 먼저
  등록하라는 주석을 이미 갖고 있다. 이 경로는 세그먼트가 3개라 지금은 가려지지 않지만
  **같은 규칙을 따라 등록한다.**

### 4.5 쓰기 순서 — DB 포인터를 **마지막에** 쓴다

바이트는 전사문 확정보다 **먼저** 도착한다(Nova가 문장을 닫을 때 `utterances` 행이 생긴다).
그래서 파일 이름을 처음부터 `utterance_id`로 지을 수 없다.

1. 낭독 턴이 열리면 `<뿌리>/<session_id>/<turn_uuid>.pcm.part`에 프레임을 흘린다.
2. 턴이 닫히면 `save_final_transcript(utterance_type='shadowing_recording')`가 행을 만들고
   `utterance_id`를 돌려준다.
3. 파일을 `<utterance_id>.pcm`으로 **rename**한다(같은 파일시스템 내 원자적 연산).
4. `audio_url`을 UPDATE한다.

**불변식: 어느 단계에서 죽어도 「접근 가능한 반쪽 녹음」이 생기지 않는다.** 3과 4 사이에서
죽으면 파일만 남고 DB 포인터가 없어 접근 불가 — §6의 고아 파일 정리가 걷는다. 2와 3 사이에서
죽으면 `.part`가 남고 같은 정리가 걷는다. **DB가 접근 가능성의 정본이고 파일은 바이트일 뿐이다.**

### 4.6 되돌리기 스크립트 (`data-first` §5-6이 요구한다)

```sql
-- 011 되돌리기. ⚠️ shadowing_recording 행이 이미 있으면 값역 축소가 실패한다 —
-- 그때는 그 행들을 어떻게 할지가 데이터 판단이므로 스크립트가 조용히 결정하지 않는다.
alter table utterances drop constraint utterances_audio_only_for_shadowing;
drop index if exists utterances_stored_audio_idx;
alter table utterances drop constraint utterances_utterance_type_check;
alter table utterances add constraint utterances_utterance_type_check
  check (utterance_type in ('learning', 'voice_command', 'command_confirmation'));
alter table learning_sessions drop constraint learning_sessions_shadowing_item_requires_mode;
alter table learning_sessions drop column shadowing_item_id;
drop table shadowing_items;
```

**적용 절차는 `data-first` §5를 그대로 따른다**(007이 통과한 형태): `pg_dump -n public` 백업 →
표별 행 수 기록 → 적용 → 재조회 대조(표 16 → 17 · `utterances` 114행 유지) → 어긋나면 복원.
⛔ `-n public`을 빼면 `permission denied for schema en_coach`로 막힌다(같은 절의 실측).

---

## §5. 「당일이 지났다」의 경계 (AC#3)

### 5.1 `current_date`를 쓰지 않는 이유 — 지금 이 순간 갈라져 있다

이 세션에서 공유 DB에 직접 돌린 한 줄이다:

```
now()                              = 2026-09-07 17:45:58.872051+00
current_date                       = 2026-09-07
(now() at time zone 'Asia/Seoul')  = 2026-09-08     ← 학습자의 날짜
SHOW TimeZone                      = UTC
```

**`current_date`가 학습자 날짜보다 하루 이르다 — 관측 시점에 실제로 그랬다.** 이 값으로
"당일이 지났다"를 판정하면 **학습자가 아직 비교하지 못한 녹음이 하루 일찍 사라진다.**
되돌릴 수 없다. → **AC#3이 금지한 그대로, `current_date`를 쓰지 않는다.**

### 5.2 경계는 「학습자의 현재 달력 날짜의 시작」이다

타임존의 정본은 **`users.timezone` 컬럼**이다(호스트 시간도 세션 기본값도 아니다).
경계를 **절대 시각 하나**로 환산해 비교한다:

```python
def day_start_for(tz_name: str, *, now: datetime) -> datetime:
    """학습자의 「오늘」이 시작한 절대 시각. 이 값보다 이전 녹음이 삭제 대상이다."""
    if now.tzinfo is None:                      # jobs.py `_require_aware`와 같은 경계 방어
        raise ValueError("`now` must be timezone-aware")
    zone = ZoneInfo(tz_name)                    # 잘못된 값이면 ZoneInfoNotFoundError
    today_local = now.astimezone(zone).date()
    # ⚠️ `replace(hour=0, …)`를 쓰지 않는다 — DST가 있는 지역에서 존재하지 않는 지역
    #    자정을 만들 수 있다. 날짜와 tzinfo로 다시 조립하면 zoneinfo가 fold 규칙으로 푼다.
    return datetime.combine(today_local, time.min, tzinfo=zone).astimezone(UTC)
```

삭제 조건: `utterances.created_at < day_start_for(user.timezone, now=…)`.

**SQL에서 `AT TIME ZONE`을 쓰지 않고 Python에서 구하는 이유 3개** — 전역 규약은
*"`AT TIME ZONE 'X'` **또는 앱의 tz 함수**"*를 모두 허용하므로 규약 위반이 아니다:

1. **잘못된 타임존 값이 한 사람만 막는다.** 직접 확인했다 —
   `select now() at time zone 'Not/AZone'` → `ERROR: time zone "Not/AZone" not recognized`.
   `users.timezone`에는 CHECK가 없다(조회로 확인). 집합 UPDATE 안에서 이 오류가 나면
   **한 사람의 잘못된 값이 모든 사람의 삭제를 막는다.** Python이면
   `ZoneInfoNotFoundError`를 그 사용자에게만 잡아 이름 있는 경고로 남길 수 있다.
2. **인덱스를 쓸 수 있다.** `created_at < $1`은 §4.2의 부분 인덱스를 타고,
   `(created_at at time zone u.timezone)::date < …`는 타지 못한다.
3. **DB 없이 단위 테스트할 수 있다.** 이 경계는 되돌릴 수 없는 삭제를 판정하므로
   경계값(자정 직전·직후·DST 지역)을 값싸게 재야 한다.

⚠️ **`clock_timestamp()` 계열을 쓴다** — `now()`(=transaction_timestamp)는 문장 사이에
전진하지 않는다. `services/jobs.py`가 백오프 붕괴 때문에 같은 선택을 이미 해 두었다.

### 5.3 타임존을 삭제 시점에 읽는 것이 불변식을 만든다

학습자가 `users.timezone`을 바꾸면 경계가 움직인다. **저장된 `timestamptz`를 고치는 것이
아니므로 데이터 손상은 아니다**(전역 규약 4번). 그리고 **비교의 양쪽이 같은 타임존을 쓰기 때문에
불변식이 유지된다**:

> **어떤 녹음도, 그 학습자의 현재 달력 날짜와 같은 날에 만들어진 것이면 삭제되지 않는다.**

경계가 앞뒤로 밀릴 수는 있지만 "오늘 만든 녹음이 오늘 사라지는" 일은 원리적으로 생기지 않는다.

### 5.4 진행 중인 세션의 녹음은 삭제하지 않는다

자정을 넘기며 진행되는 세션에서 23:58에 만든 녹음을 00:01에 지우면 **학습자가 지금 비교하려는
것이 사라진다.** 캡틴 결정의 문구가 *"**비교된** 오디오는 당일이 지나면 삭제한다"*이므로 아직
비교 중인 것은 대상이 아니다. → **삭제 조건에 `learning_sessions.status <> 'active'`를 더한다.**

크래시로 `active`에 남은 세션은 기존 고아 리퍼(`reap_orphan_sessions` · `ORPHAN_IDLE_GRACE`)가
`failed`로 닫고, 그 다음 주기에 삭제 대상이 된다 — **새 장치가 필요하지 않다.**

---

## §6. 삭제 실행 주체와 재시도 (AC#4)

### 6.1 주체 — **워커의 유휴 사이클 스윕**. 새 job 종류를 만들지 않는다

| 후보 | 판정 |
|---|---|
| `analysis_jobs`에 job 종류를 더한다 | ⛔ **기각.** `analysis_jobs_target_matches_job_type` CHECK가 **job 종류를 전수 열거**한다(직접 조회 확인) → 종류를 더하려면 그 CHECK를 DROP → ADD해야 하고, 그것이 `data-first` 규약이 말하는 가장 위험한 형태다. 게다가 이 표에는 `user_id`가 없다 — 삭제는 **사용자·날짜 단위**라 담을 대상 컬럼이 없다 |
| 조회 시점에만 지운다 | ⛔ 단독으로는 기각. 학습자가 다시 열지 않으면 **바이트가 영구히 남는다** |
| **워커의 유휴 사이클 스윕** | ✅ **채택** — 선례가 이미 둘 있다 |
| 조회 시점 **차단** | ✅ **함께 채택**(§6.4) — 워커가 안 돌아도 접근은 막힌다 |

**선례를 그대로 베낀다.** `workers/analysis_worker.py`의 유휴 사이클은 큐가 비었을 때
`reap_orphans`(I-4)와 `sweep_lost_runs`(I-1)를 부르고, **리퍼 고유의 실패가 스윕을 막지 않게
각각 따로 `try/except`로 감싼다.** 삭제 스윕은 그 목록에 하나 더 붙는 세 번째 항목이다 —
**새 프로세스도, 새 표도, 새 크론도 만들지 않는다.**

### 6.2 두 다리 — DB 포인터와 파일은 따로 걷는다

**1다리 — 만료된 녹음을 접근 불가로 만들고 바이트를 지운다** (사용자별로 자기 트랜잭션):

```
사용자마다 (user_id, timezone)을 읽는다
  cutoff = day_start_for(timezone, now=clock)        ← 잘못된 tz면 이 사용자만 건너뛰고 경고
  대상 = utterances u join learning_sessions s on …
         where u.audio_url is not null
           and u.utterance_type = 'shadowing_recording'
           and s.user_id = <user> and s.status <> 'active'
           and u.created_at < cutoff
         limit N                                     ← 사이클당 상한. 루프를 굶기지 않는다
  (a) update … set audio_url = null   ← 커밋한다. 여기서 「접근 불가」가 확정된다
  (b) 파일을 unlink 한다              ← 실패해도 (a)는 이미 섰다
```

**순서가 (a) → (b)인 것이 계약이다.** `database-schema.md`가 요구하는 것은 **"즉시 접근 불가"**
이므로 실패 시 닫히는 쪽으로 넘어져야 한다. 뒤집으면(파일 먼저) 크래시 후 DB는 "있다"고 하고
파일은 없어 **학습자에게 깨진 재생**이 남는다.

**2다리 — 고아 파일 정리.** 1다리의 (b) 실패는 (a) 때문에 **1다리로는 재시도되지 않는다**
(조건이 `audio_url is not null`이므로 더 이상 선택되지 않는다). 그래서 파일 쪽에서 걷는 다리가
**선택이 아니라 필수**다:

```
뿌리 아래 세션 디렉터리마다 (status <> 'active'인 세션만)
  살아있는 키 = select utterance_id … where session_id = <s> and audio_url is not null
  그 집합에 없는 파일과 `.part` 파일을 unlink → 빈 디렉터리는 rmdir
```

**2다리가 잡는 것 3가지**: ① 1다리의 unlink 실패 ② §4.5의 중단된 쓰기(`.part`) ③ **FK
cascade로 사라진 포인터.** `utterances`는 `learning_sessions`에 `on delete cascade`이므로
**세션을 지우면 DB 포인터는 사라지고 파일은 남는다** — 2다리 없이는 영구 누출이다.

### 6.3 재시도 — 상태를 만들지 않는다. 술어가 여전히 참이면 다시 걷는다

| 실패 | 무엇이 재시도하나 |
|---|---|
| (a) UPDATE 실패 | 술어가 그대로 참 → **다음 유휴 사이클이 같은 행을 다시 고른다** |
| (b) unlink 실패 (권한·EBUSY) | **2다리**가 같은 파일을 다시 고른다 |
| 잘못된 `users.timezone` | 그 사용자만 건너뛴다. `WARNING`으로 남긴다 — 값을 고치면 다음 사이클에 낫는다 |
| 워커 자체가 죽었다 | 재기동 시 다음 유휴 사이클. **그 사이에도 §6.4가 접근을 막는다** |
| 뿌리 디렉터리가 없다 | 만든다(`parents=True`). 없다는 것은 저장한 적이 없다는 뜻이라 오류가 아니다 |

**attempts 카운터도 백오프도 두지 않는다.** 이 스윕은 **멱등**이고(같은 조건을 다시 계산한다)
영구 실패해도 데이터가 어긋나지 않는다(접근은 이미 막혀 있다). `analysis_jobs`의 lease·attempts는
**Claude 호출 중복 과금**을 막기 위한 장치인데 여기에는 그 비용이 없다 —
`sweep_lost_runs`가 같은 이유로 카운터를 두지 않은 선례다.
⚠️ **로그 수준**: 스윕이 무언가를 지웠으면 `INFO`, unlink가 실패했으면 `WARNING`이다. 문서가
지정한 실행 명령은 root 로거에 핸들러를 두지 않아 **`WARNING` 이상만 흐른다**(워커 코드가
직접 적어 둔 실측) — 실패가 보이지 않으면 안 되므로 그 경계를 지킨다.

### 6.4 조회 시점 차단 — 워커에 개인정보를 걸지 않는다

`WORKER_ENABLED=false`로 며칠을 돌리면 스윕이 한 번도 돌지 않는다. 그동안 접근이 열려 있으면
**「당일이 지나면 삭제」가 워커 기동 여부에 걸린 약속**이 된다.

→ **§4.4의 서빙 엔드포인트가 같은 경계 함수(`day_start_for`)를 다시 계산해, 만료된 녹음에는
바이트를 주지 않고 `404`를 돌려준다.** 스윕과 엔드포인트가 **같은 함수 하나**를 부른다 —
두 곳에서 각자 계산하면 갈라진다(`009_drill_turns.sql`가 "두 곳에 세면 갈라진다"로 적어 둔 것과
같은 규칙). §5.4의 `active` 예외도 이 함수의 호출자가 함께 적용해, 자정을 넘긴 진행 중 세션이
**엔드포인트에서 404를 받는 일이 없게** 한다.

---

## §7. 설정값 — **명세만 적는다** (AC#5는 범위 밖 · §12)

⛔ **이 절은 코드를 고치지 않았다.** 값역 거부는 TDD로 red를 먼저 봐야 하고 이 세션은
`pytest`를 돌릴 수 없다(H-X — 공유 테스트 DB가 실행마다 파괴된다). 아래는 **구현자에게 넘기는
명세**다.

✅ **그 구현이 끝났다 (2026-09-08 · `TASK-45` AC#2)** — 아래 명세를 **한 글자도 바꾸지 않고**
그대로 넣었다. 이 절은 이제 「넘기는 명세」가 아니라 **코드가 왜 그 모양인지의 근거**다.
정본은 `app/backend/app/config.py`의 필드 주석이고, 값역의 근거(캡틴 결정 6)와 기본값을
항등원으로 고른 판단(유도 3)이 그쪽에도 함께 있다.

### 7.1 `Settings`에 더할 필드 3개

`app/backend/app/config.py`의 `Settings`는 이미 `BaseSettings`이고 `Field(default=…, ge=…)`
관례를 쓴다(`drill_turns_min`·`drill_count`가 그 형태다 — 직접 읽어 확인). **새 설정 체계를
만들지 않고 같은 클래스에 더한다**(결정 문서 §2).

```python
# 쉐도잉 재생 속도. 캡틴 결정 6이 0.5~2배를 지정했다 — 값역이 계약이므로 기동 시점에 거부한다.
# 기본 1.0은 값역의 **항등원**이다: 설정이 생기는 것만으로 재생이 달라지지 않게 한다.
shadowing_playback_rate: float = Field(default=1.0, ge=0.5, le=2.0)
# 쉐도잉 반복 횟수. 캡틴 결정 6이 1~10회를 지정했다. 기본 1도 같은 이유의 항등원이다 —
# PRD §7의 진행 순서가 요구하는 것 이상을 기본값이 발명하지 않는다.
shadowing_repeat_count: int = Field(default=1, ge=1, le=10)
# 학습자 녹음 뿌리. 백엔드 cwd(`app/backend`) 기준 상대경로다(`.env`와 같은 해석).
# ⚠️ 기본값이 `../../`인 이유: `.gitignore:32`의 `assets/audio/`는 슬래시를 포함해
#    **리포루트에만** 앵커된다 — `app/backend/assets/audio/`는 추적 대상이다(§4.3 실측).
shadowing_audio_root: Path = Path("../../assets/audio")
```

**기본값을 항등원으로 고른 것이 이 절의 유일한 판단이다**(유도 3, §11). 캡틴은 **값역만**
지정했고 기본값을 말하지 않았다 — 관측 없이 중간값(예: 3회)을 고르면 그 숫자가 코드에 굳는다.
값역의 최소값은 **"설정이 아무것도 바꾸지 않는 상태"**이므로 발명이 아니다.

### 7.2 `ge`/`le`가 기동 시점 거부를 만든다

pydantic이 `Settings()` 구성 시점에 `ValidationError`를 던지므로 **런타임에 조용히 잘리지
않는다** — 결정 문서 §2가 요구한 형태 그대로다. `get_settings()`는 `@lru_cache`이므로
첫 호출(=앱 기동)에서 터진다.

### 7.3 `.env.example`도 함께 갱신한다 — 결정 문서가 남긴 열린 질문의 답

결정 문서 §2의 2026-09-07 정정 상자가 *"새 설정값을 더할 때 루트 `.env.example`도 함께 갱신할지
— **작업세션이 정한다**"*로 이 질문을 열어 두었다. **답: 갱신한다.** 근거는 발명이 아니라
**선례**다 — 그 파일을 직접 열어 확인했고 `DRILL_TURNS_MIN`·`DRILL_COUNT`가 **이미 그 안에
근거 주석까지 달고 들어 있다**. 즉 "설정값을 더하면 예시 파일도 갱신한다"가 이 리포의 관례이고,
빼면 관례가 갈라진다.

### 7.4 재생 속도·반복 횟수를 **누가 읽나**

| 값 | 소비자 |
|---|---|
| `shadowing_playback_rate` | 프론트의 재생 큐(`lib/audio.ts`의 `VoiceIo`) — 헤더 없는 PCM을 직접 쥐고 있으므로 속도 조절의 자리가 거기다. 서버는 세션 시작 응답에 값을 실어 보낸다 |
| `shadowing_repeat_count` | 코치 지시문 조립 — "각 문장을 N회 따라 말하게 한다". `drill_count`가 `questions[:drill_count]`로 지시문에 들어가는 것과 같은 자리·같은 방식이다 |
| `shadowing_audio_root` | §6의 스윕 두 다리와 §4.4의 서빙 엔드포인트 |

⚠️ **`shadowing_repeat_count`는 지시문을 바꾸는 값이다** — `drill_count`가 그렇듯 "통과 문턱만
바꾸는 노브"가 아니다. 내리면 실제 연습량이 함께 줄어든다는 것을 필드 주석에 적는다.

---

## §8. 4 Lenses 검증

### L1. Contract

| 계약 | 전제 / 사후조건 |
|---|---|
| `day_start_for(tz, now)` | **전제**: `now`는 aware(naive는 거부 — `jobs.py:_require_aware`와 같은 경계). `tz`는 IANA 이름. **사후**: 반환값 이후에 만들어진 녹음은 이 호출에서 절대 삭제 대상이 아니다. **불변**: 삭제 스윕과 서빙 엔드포인트가 **같은 함수**를 부른다 |
| `audio_url` | **불변**: `audio_url is not null` ⇔ 그 행은 학습자의 쉐도잉 낭독이다 — CHECK가 강제한다(§4.2). 값은 **API 경로**이고 파일 경로가 아니다 |
| 저장 (§4.5) | **사후**: DB 포인터가 있으면 파일이 있다. **역은 성립하지 않는다**(고아 파일 허용) — 그것이 fail-closed 방향이고 2다리가 걷는다 |
| `shadowing_items` | **불변**: `clip_end_sec > clip_start_sec` · 창 길이 ≤ 90초 · `transcript`·`source_title` 비지 않음 — 전부 CHECK |
| `learning_sessions.shadowing_item_id` | **불변**: 값이 있으면 `mode = 'shadowing'`. 역은 강제하지 않는다(클립 선택 전에 세션이 열릴 수 있다) |
| 설정값 3개 | **전제**: 값역 밖이면 **기동이 실패한다**(런타임 절단 없음) |

### L2. Boundary

| 경계 | 무엇이 넘나 | 변환·검증 |
|---|---|---|
| **시간 (달력 날짜)** | UTC 절대 시각 → 학습자 달력 날짜 | `users.timezone`으로 환산한다. ⛔ `current_date` 금지 — §5.1에서 **하루 차이를 직접 관측했다** |
| **시간 (DST)** | 지역 자정의 존재 여부 | `replace(hour=0)`이 아니라 `datetime.combine(date, time.min, tzinfo=…)`로 조립한다(§5.2) |
| **타입** | aware ↔ naive datetime | 앱 경계에서 naive를 거부한다 |
| **프로세스** | 메모리(오디오 프레임) → 파일 → DB 포인터 | 순서가 §4.5. **DB 포인터를 마지막에** 쓴다 |
| **파일시스템 ↔ DB** | 두 저장소의 정합 | **DB가 접근 가능성의 정본**이다. 어긋남은 2다리가 한 방향(고아 파일)만 허용하고 걷는다 |
| **리포 추적 경계** | 녹음 파일이 git에 들어가는가 | 뿌리 기본값이 **리포루트** `assets/audio/`여야 한다 — `app/backend/assets/audio/`는 **추적 대상**임을 `git check-ignore`로 확인했다(§4.3) |
| **분석 경계** | 쉐도잉 낭독이 오류 분석에 들어가는가 | `utterance_type='shadowing_recording'` → 4자리 SQL이 자동으로 배제한다(§4.1) |
| **DB 값역 ↔ 실제 값** | `users.timezone`은 free text | 잘못된 값은 `ZoneInfoNotFoundError`로 **그 사용자만** 건너뛴다(§5.2 근거 1) |

### L3. Failure — **삭제와 재시도가 이 렌즈의 핵심이다**

| 실패 | 그때 시스템 상태 | 대응 |
|---|---|---|
| (a) UPDATE 성공 → (b) unlink 실패 | 접근 불가 ✅ · 바이트 잔존 ❌ | **2다리**가 걷는다(1다리는 술어에서 빠져 못 걷는다 — §6.2가 2다리를 필수로 만든 이유) |
| (b)를 먼저 하고 (a) 전에 크래시 | DB는 "있다" · 파일 없음 → **깨진 재생** | ⛔ 그래서 순서를 (a) → (b)로 못 박았다 |
| §4.5의 3~4 사이 크래시 | 파일만 있고 포인터 없음 → 접근 불가 | 2다리가 걷는다. **부분 저장이 접근 가능한 녹음을 만들지 않는다** |
| 세션 FK cascade 삭제 | 포인터가 사라지고 파일이 남는다 | 2다리 — **이것이 없으면 영구 누출** |
| 잘못된 `users.timezone` | SQL이면 **전원 삭제 정지** | Python 경계 계산으로 그 사용자만 격리(§5.2) |
| 워커가 며칠 꺼져 있다 | 바이트 잔존 | **§6.4 조회 시점 차단** — 접근은 워커와 무관하게 닫힌다 |
| 스윕이 예외로 죽는다 | 다른 회복 경로도 죽을 수 있다 | `reap_orphans`처럼 **자기 `try/except`로 감싼다**(선례) |
| 삭제 대상이 수천 건 | 루프가 한 사이클에 매달린다 | 사이클당 `limit N`. 남은 것은 다음 사이클 |
| 자정을 넘긴 진행 중 세션 | 비교 직전의 녹음이 사라진다 | `status <> 'active'` 조건(§5.4). 크래시로 남은 `active`는 기존 고아 리퍼가 닫는다 |
| 값역 축소 되돌리기 시 낭독 행 존재 | `ALTER`가 실패한다 | 되돌리기 스크립트가 **조용히 결정하지 않는다**(§4.6) — 데이터 판단을 사람에게 올린다 |

### L4. Dependency

- **적용 순서**: `011`은 `001`(`utterances`·`learning_sessions`)에만 의존한다. `009`·`TASK-12`의 `010`과 독립이고
  (`009`는 `learning_sessions`에 다른 컬럼을 더한다) **`008`과도 독립이어야 한다** — 그 조건을
  §3.5에 명시적으로 못 박았다.
- **코드 순서**: 서빙 엔드포인트와 스윕은 **둘 다** `day_start_for` 하나에 의존한다. 그 함수가
  먼저 있어야 두 소비자가 갈라지지 않는다.
- **워커 유휴 사이클 순서**: `reap_orphans` → `sweep_lost_runs` → **삭제 스윕**. 리퍼를 먼저
  두는 이유는 §5.4다 — 방금 닫힌 세션의 녹음이 같은 사이클에 삭제 대상이 된다.
- **`mode` 파라미터화가 선행이다**: `create_session`이 `mode='shadowing'`을 쓸 수 있어야
  `shadowing_item_id`의 CHECK를 통과한다. **순환은 없다** — 값역은 이미 열려 있어(§2)
  마이그레이션이 코드를 기다리지 않는다.
- **순환 의존 없음**: `shadowing_items` ← `learning_sessions` ← `utterances` 단방향.

---

## §9. 데이터 우선 §3 표 — 소비자 0곳이면 진행하지 않는다

| 항목 | 답 |
|---|---|
| 무엇을 저장하나 | ① 쉐도잉 클립(출처·전사문·시간 창·수준) ② 세션이 고른 클립 ③ 학습자 낭독 녹음(파일 + `audio_url` 포인터) |
| 어느 표·컬럼에 | ① `shadowing_items`(신설) ② `learning_sessions.shadowing_item_id`(ALTER ADD) ③ 파일 + `utterances.audio_url`(**재사용**) |
| **누가 읽나** | ① 클립 선택(학습자 `current_level` 대조) + 코치 지시문 조립(전사문) ② 재접속·결과 조회 시 세션의 클립 복원 ③ **§4.4 서빙 엔드포인트**(프론트의 녹음 비교 재생) + **§6 삭제 스윕 두 다리** |
| 읽은 값으로 무엇이 달라지나 | ① 화면에 뜨는 문장과 코치 지시문 ② 세션 재개 시 같은 클립 ③ 학습자가 자기 녹음을 원본과 비교해 듣는다 = **PRD §7의 「녹음 비교」 그 자체** |
| 읽는 쪽이 아직 없다면 **어느 태스크가 소유하나** | ①②의 **선택 UI·진입점은 `TASK-10`이 소유한다**(§12). ③의 서빙 엔드포인트·스윕은 **이 설계가 명세하고 구현 태스크가 만든다** |

### ⛔ 마이그레이션 파일을 쓰는 조건 — 지금은 쓰지 않는다

`data-first` §3은 **"소비자가 0곳이면 진행하지 않는다"**고 못 박는다. 이 리포는 같은 실패를
**네 번** 냈다(값을 저장하는데 읽는 코드가 0곳). → **`011_shadowing_items.sql`은 아래 둘이
갖춰진 뒤에 쓴다:**

1. **`TASK-10`이 쉐도잉 진입점을 확정했다** — 클립을 고르는 주체가 정해진다.
2. **`create_session`이 `mode`를 받는다** — 그것 없이는 `shadowing_item_id`가 CHECK를 통과할
   행을 만들 수 없다.

**번호 `011`은 지금 예약하고 파일은 그때 쓴다.** 예약만 하면 §3.5의 순서 갈라짐이 하나 더
생기지만, 소비자 없는 표를 만드는 비용이 그보다 크다.

---

## §10. 이 설계의 약점 5개

1. **`utterance_type` 값역 확장이 되돌릴 수 없는 방향으로 굳는다.** 114행이 든 표의 CHECK를
   DROP → ADD하고(가장 위험한 형태), `shadowing_recording` 행이 하나라도 생기면 되돌리기
   스크립트가 실패한다(§4.6). 대안(불리언 컬럼 신설)은 4자리 SQL의 자동 배제를 잃는다 —
   그 값어치가 이 위험보다 크다고 판단했지만 **판단이다.**
2. **`shadowing_items`에 행을 넣는 경로가 없다.** PRD가 자동 수집을 비범위로 못 박았으므로
   행은 손으로 들어와야 하는데 **시딩을 소유한 태스크가 없다.** 마이그레이션을 적용해도
   **0행이면 쉐도잉은 여전히 동작하지 않는다.** §13이 이것을 캡틴에게 올린다.
3. **§6.4의 조회 시점 차단을 스키마가 강제할 수 없다.** 나중에 다른 읽는 자리(예: 결과 화면의
   녹음 목록)가 생겼을 때 그 자리가 `day_start_for` 호출을 빠뜨리면 **만료된 녹음이 샌다.**
   방어는 규약뿐이다 — 이 설계에서 가장 약한 고리다.
4. **삭제는 「접근 불가」가 먼저고 「바이트 소거」가 나중이다.** 워커가 오래 꺼져 있으면
   바이트가 디스크에 남는다. 개인정보 계약(`database-schema.md`)은 "즉시 접근 불가"만 요구하므로
   위반은 아니지만, **"삭제한다"는 캡틴 결정의 문구보다 약하다.**
5. **문장 색인을 저장하지 않아 같은 날 다시 열었을 때 「어느 문장의 녹음인가」를 복원할 수
   없다.** 반복 횟수가 1보다 크면 순서로 짝지을 수도 없다(유도 2). 세션 안에서는 프론트가 알고
   있으므로 「녹음 비교」 자체는 성립한다.

---

## §11. 내가 유도한 것 4건 — 뒤집으면 무엇이 달라지는가

캡틴이 답하지 않은 자리에서 내가 답을 유도한 곳이다. **틀렸으면 그 줄만 뒤집으면 된다.**

### 유도 1 — `shadowing_items` 한 행은 **클립 1개**다 (문장 1개가 아니다)

**근거**: `clip_start_sec`/`clip_end_sec`가 출처 안의 시간 창을 뜻하고, PRD가 "30~90초 클립"과
"외부 영상은 링크만"을 함께 말한다. 그리고 **세션이 고르는 단위가 클립**이라
(`사용자가 선택한 콘텐츠만 과제로 사용한다`) 선택을 담을 자리가 `learning_sessions`의 FK 하나로
끝난다.
**뒤집으면**(한 행 = 문장 1개): `source_title`·`source_url`이 문장마다 반복돼 클립 제목을 고칠 때
N행을 고쳐야 하고, 세션의 「고른 클립」을 담을 자리가 사라져 **클립 단위 부모 표(`shadowing_sources`)가
하나 더 필요**하다. 대신 녹음 ↔ 문장 짝짓기가 FK 하나로 해결된다(약점 5가 사라진다).

### 유도 2 — 문장 색인을 **저장하지 않는다**

**근거**: `data-first` §3이 "읽는 코드가 0곳이면 진행하지 않는다"고 못 박고, 문장 색인의 유일한
소비자는 **아직 없는 화면**이다. 그리고 녹음은 하루를 못 넘기므로 세션 밖 소비자가 구조적으로
드물다.
**뒤집으면**: `utterances`에 `sentence_index smallint` 하나가 더 생기고 약점 5가 닫힌다.
대가는 **이 리포가 네 번 낸 실패의 다섯 번째** — 읽는 코드가 0곳인 컬럼이다.

### 유도 3 — 설정 기본값은 값역의 **항등원**이다 (`1.0`배 · `1`회)

**근거**: 캡틴은 **값역만** 지정했다(0.5~2.0 · 1~10). 관측 없이 중간값을 고르면 그 숫자가 코드에
굳는다 — 이 리포가 스스로 지목한 가장 비싼 실패다. 항등원은 "설정이 아무것도 바꾸지 않는 상태"라
발명이 아니다.
**뒤집으면**(예: 기본 3회): 첫 실행부터 학습량이 3배가 되고, 그 숫자의 근거는 아무 데도 없다.
반대로 항등원 기본값의 대가는 **누군가 값을 올리기 전까지 반복 기능이 실질적으로 꺼져 있다**는
것이다 — 캡틴이 "반복을 기본으로 켜라"는 뜻이었다면 이 줄이 틀렸다.

### 유도 4 — 삭제 주체는 **워커의 유휴 사이클**이고 새 job 종류를 만들지 않는다

**근거**: `analysis_jobs`의 대상 CHECK가 job 종류를 전수 열거해서 확장이 가장 위험한 형태이고
(직접 조회), 그 표에 `user_id`가 없다. 그리고 **같은 모양의 선례가 이미 둘**이다
(`reap_orphans`·`sweep_lost_runs`).
**뒤집으면**(job 큐를 쓴다): lease·attempts·백오프를 공짜로 얻지만 `analysis_jobs`의 CHECK를
DROP → ADD해야 하고 대상 컬럼(`user_id`)을 더해야 한다 — **007이 이미 위험하다고 판정한 형태를
한 번 더 하는 것**이고, 이 스윕에는 그 장치가 막아 줄 비용(중복 Claude 과금)이 없다.

---

## §12. 범위 밖 — 무엇을 왜 안 했고 누가 소유하나

### AC#5 — `Settings`에 필드를 더하는 **코드 변경**

**하지 않았다.** 값역 거부(`ge`/`le`)는 **동작이므로 TDD 대상**이고, 구현 전 red를 실제로
관측해야 한다. 이 세션은 **`pytest`를 돌릴 수 없다** — 함정 **H-X**: `tests/conftest.py`의
session 스코프 픽스처가 매 실행 시작에 테스트 DB를 `DROP`/`CREATE`하므로, 두 세션이 동시에
돌리면 서로를 깨뜨리고 그 실패가 회귀로 오인된다.
→ **필드명·기본값·값역·주석 형식·`.env.example` 갱신 여부까지 §7이 명세로 적어 두었다.**
**소유자**: 구현 태스크(세션 분리). 그 세션이 red → green을 관측하고 게이트 수치를 남긴다.

✅ **이행됐다 (2026-09-08 · `TASK-45` AC#2).** 위 「하지 않았다」는 **이 설계 세션**에 대한
서술이고 지금도 그 뜻으로 참이지만, **구현은 끝났다** — 세 필드가 `app/backend/app/config.py`의
`Settings`에 들어갔고 `.env.example`도 갱신됐다. red→green: 신규 테스트 **8건**이 red(기본값·경계는
`AttributeError`, **거부 테스트는 `DID NOT RAISE`** — `extra="ignore"` 때문에 미지의 필드가 조용히
무시됐다) → 구현 후 8 passed. 게이트 **766 passed**. 명세와 다르게 한 것은 **없다**.

### AC#6 — 쉐도잉 진입점

**정하지 않았다. `TASK-10`이 소유한다.** AC#6 자신이 *"여기서 따로 정하면 두 곳이 갈라진다"*고
경고하고, `gap-investigation` §6도 같은 판정을 적어 두었다(PRD §7 「Additional Learning」이
추가 학습 5종에 쉐도잉을 넣었고 `TASK-10` AC 1이 이미 그 결정을 요구한다). `TASK-10`은 지금
`TASK-2`를 기다리며 막혀 있다.

**이 설계가 진입점에 요구하는 것 5개** (진입점을 정하는 쪽이 만족시켜야 하는 계약):

| # | 요구 | 왜 |
|--:|---|---|
| 1 | 세션을 **`mode='shadowing'`**으로 연다 | `shadowing_item_id`의 CHECK가 그것을 요구한다(§3.3). `create_session`의 `mode` 파라미터화가 여기서 발화한다(결정 11) |
| 2 | **클립 1개를 고르고** 그 id를 세션에 남긴다 | 선택이 재접속에서 살아남아야 한다(`data-first` 방향 B) |
| 3 | 선택은 **학습자 수준**(`users.current_level`)을 기준으로 한다 | `shadowing_items.level`의 유일한 소비자가 그것이다 |
| 4 | 낭독 턴을 **명시적으로 열고 닫는다** | §4.5의 파일 수명이 그 경계에 걸린다. "언제부터 저장하는가"를 UI가 알려주지 않으면 세션 전체가 녹음된다 |
| 5 | 재생 속도·반복 횟수를 화면에 **전달만** 한다 | 값의 정본은 `Settings`다(§7). 화면이 자기 기본값을 갖지 않는다 |

### 그 밖에 하지 않은 것

- **코드·마이그레이션 SQL 파일을 만들지 않았다.** 이 문서의 SQL은 명세이고, 파일을 쓰는 조건은
  §9가 정한다.
- **기존 설계서를 편집하지 않았다.** 새 파일 하나만 만들었다.
- **`docs/database-schema.md`를 갱신하지 않았다** — 그 문서의 「아직 SQL에 없는 테이블」 절에서
  `shadowing_items`를 옮기는 것은 **마이그레이션이 실제로 적용된 뒤**에 할 일이다. 지금 옮기면
  「설계 ↔ 실제 DB」가 어긋난다(`data-first` §4가 지목한 실패 사례와 같은 형태).

---

## §13. 캡틴에게 물을 것 — 1건

발명하지 않았다. 저장 예외·보존 기간·재생 속도·반복 횟수는 이미 결정됐고(§1), 마이그레이션
번호·저장 위치·삭제 주체·값역 처리는 **내가 정할 수 있는 설계 판단**이라 §3~§6에서 정했다.
남은 하나는 설계 판단이 아니다.

> **쉐도잉 클립(`shadowing_items`)의 행은 누가 어떻게 넣습니까?**
>
> PRD가 자동 수집을 비범위로 못 박고(§5) *"외부 영상은 메타데이터·링크만 보관하고 사용자가
> 선택한 콘텐츠만 과제로 사용한다"*(§7)고 정했습니다. 그래서 클립의 **제목·링크·전사문·시간
> 창**은 손으로 들어와야 하는데, **그 일을 소유한 태스크가 없습니다.** 표를 만들어도 0행이면
> 쉐도잉은 동작하지 않습니다(약점 2).
>
> 이것을 설계로 정하지 않은 이유: 어떤 자료를 어디서 가져오는지는 **저작권과 개인정보가 걸린
> 제품 결정**이라 제가 정할 자리가 아닙니다. 선택지는 대략 셋으로 보입니다 — ① 캡틴이 클립
> 몇 개를 직접 골라 시드로 넣는다 ② 학습자가 링크와 문장을 화면에서 입력한다(진입점 설계가
> 커진다 → `TASK-10`) ③ 기존 업무 시나리오 문장을 TTS로 읽어 자체 생성한다(외부 자료 문제가
> 사라진다).

---

_작성: 2026-09-08. **이 문서의 모든 값역·행 수·제약·경로 판정은 이 세션에서 직접 조회하거나_
_파일을 열어 얻었다** — `pg_get_constraintdef` · `information_schema` · `git check-ignore` ·_
_`grep`. 인용한 심볼(`_CREATE_SESSION_SQL` · `day_start_for`의 선례인 `jobs.py:_require_aware` ·_
_`utterance_type` 4자리)도 직접 열어 확인했다._
_결정의 정본은 `docs/design/2026-09-06-captain-decisions.md`, 공백 근거는_
_`docs/design/2026-09-06-gap-investigation.md` §6, 표 설계 규약은_
_`docs/ops/data-first-design-convention.md`, 태스크 상태는 Backlog.md가 소유한다._

