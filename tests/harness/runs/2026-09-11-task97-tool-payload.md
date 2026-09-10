# TASK-97 — **프롬프트 강화로 고쳐지지 않는다(3/3 대 3/3).** 그리고 원인이 더 깊은 자리에 있다
# ⛔ **두 tool 호출이 `target_form` 을 서로 다른 뜻으로 쓰고, 앱이 좋은 값을 버린다**

> 회차 디렉터리: `runs/2026-09-11-task97-tool-payload/`. 실물 Nova **9회**(B0 3 · B1 1판 3 · B1 2판 3) ·
> 스파이크 직결 · **DB 쓰기 0건**(회차 전·후 `17 | 128 | 9 | 7 | 57` 동일 · 직접 확인).
> 닫은 AC: **#2 · #3**. 남긴 AC: **#1**(사용자 판정) · **#4**(상시 가드).

---

## 1. ⛔ 착수하자마자 이 태스크 문면의 전제가 반증됐다 — 지시는 **있다**

AC#2 는 *"규칙 10 이 `target_form` 의 내용을 지시하지 않는다"* 를 전제로 쓰였다. **규칙 10 만 보면 참인데
그것이 전부가 아니다.**

| 자리 | 문면 | 어느 팔에 실리는가 |
|---|---|---|
| `models/pronunciation.py` tool 스키마 | **`"The full sentence you modeled with correct pronunciation."`** | ⛔ **두 팔 전부** — `spike_nova_protocol.py:148` 이 제품 스키마를 그대로 싣는다 |
| `nova.py` 규칙 10 | `target_sound` 만 지시한다. `target_form` 은 언급 없음 | 앱 프롬프트 팔 |
| 스파이크 `TOOL_SYSTEM_PROMPT` | `say the whole sentence back with correct pronunciation` | 기준 팔 |

⇒ **`target_form` 의 내용 지시는 제품 스키마의 필드 설명에 이미 «명시»돼 있고 모델이 그것을 어겼다.**
「지시가 없어서 그렇다」가 아니다.

⚠️ **그리고 `TASK-93` 의 payload 관측은 앱 프롬프트 팔이 아니다** — 그 회차의 팔 A(앱 프롬프트)는
tool **0건**이었고, 인용된 payload 는 팔 B(스파이크 `TOOL_SYSTEM_PROMPT`)에서 나왔다. **제품 프롬프트가
낸 payload 는 아직 한 건도 없다.** 그래서 이 회차도 기준 팔에서 잰다 — 그것이 payload 를 얻는 유일한 팔이다.

---

## 2. AC#2 — **판정: 프롬프트 강화로 고쳐지지 않는다.** 교차 3쌍

**단일 변수를 지켰다** — 두 프롬프트를 코드에서 `TOOL_SYSTEM_PROMPT` 를 **그대로 뽑아** 만들고
한쪽에 **문장 하나**만 더했다(`diff` 로 확인). 봉투는 `--wav p2m.wav,p2a.wav --tools --prompt-file`
이고 **두 팔이 같은 경로**를 지난다. 팔을 **번갈아** 돌렸다(`TASK-81` 이 시점 차이로 헛된 차이를 본 뒤의 규율).

| 팔 | 더한 문장 | 회차 | 첫 `target_form` 이 무너진 전사인가 |
|---|---|--:|:--:|
| **B0** 기준 | 없음(317자) | 3 | **3/3 그렇다** |
| **B1 2판** | `When you report target_form, write the sentence in standard English spelling as it should be said, not as it sounded.`(435자) | 3 | **3/3 그렇다** |

⇒ **같은 방향이다. 강화가 듣지 않았다.**

### 2-1. ⛔ 1판은 **Bedrock 콘텐츠 필터에 3/3 막혔다** — 이것도 기록한다

1판의 더한 문장은 *"The target_form you report must be the CORRECTED sentence in normal English
spelling; never copy back the garbled words you heard."* 였고 **세 회차 전부**
`ValidationException … This request has been blocked by our content filters.` 로 죽었다.

⇒ **프롬프트 강화 축에는 가드레일 제약이 있다.** 부정문(`never …`)과 `garbled` 를 뺀 2판은 통과했다.
⚠️ **어느 낱말이 걸렸는지는 재지 않았다** — 두 낱말을 한 번에 뺐다. 1판 원문은
`prompt-B1-BLOCKED-by-content-filter.txt` 로 남긴다.

---

## 3. ⛔ 이 회차가 더한 것 — **두 호출이 `target_form` 을 다른 뜻으로 쓴다.** 6/6

12건의 payload 를 전부 원문으로 읽었다. **두 팔·여섯 회차가 같은 모양이다.**

| 호출 | `target_form` | `outcome` |
|--:|---|---|
| 1 | **무너진 전사**(`I finished the la port en shayz du luh seps with my team.` 류) | `pending` |
| 2 | ✅ **옳은 목표 문장**(`I finished the report and shared the results with my team.`) | `pending` |

⇒ **모델은 첫 호출을 「내가 들은 것」으로, 둘째를 「목표 문장」으로 쓴다.** 규칙 10 이 두 호출을
**시점**(시범 직후 / 재발화 청취 후)으로만 구별하고 `target_form` 의 뜻을 고정하지 않으므로,
그 필드가 호출마다 다른 것을 담는 것이 **문면상 모순이 아니다.**

### 3-1. ⛔ 그리고 앱이 **좋은 값을 버린다** — 코드로 확인했다

`services/pronunciation.record_attempt` 의 판정 UPDATE 를 직접 읽었다:

```
update pronunciation_attempts set
    outcome = $2, spoken_form = coalesce($3, spoken_form),
    target_sound = coalesce($4, target_sound), utterance_id = coalesce($5, utterance_id),
    resolved_at = clock_timestamp()
```

⛔ **`target_form` 이 그 UPDATE 에 없다.** 즉 **첫 호출의 값이 그 행의 최종값**이고, 둘째 호출이
가져온 옳은 문장은 **어디에도 저장되지 않는다.**

⚠️ **그 값이 학습자 화면에 그대로 뜬다** — 결과 화면이 `target_form` 을 `시범 문장` 자리에 렌더한다
(`TASK-94` 회차 §5 에서 직접 관측했다). 즉 **「이렇게 말하세요」 자리에 학습자의 오발음이 뜬다.**

### 3-2. ⚠️ 이 봉투에서는 판정이 아예 오지 않았다 — 함께 적는다

**12/12 가 `outcome: "pending"`** 이고 `correct`·`incorrect`·`unclear` 가 **0건**이다.
`target_sound` 도 **12/12 부재**다(`TASK-93` 은 1/4 에서 `r as r` 을 받았다 — 봉투가 같지 않다).

⇒ 그러면 `record_attempt` 의 `pending` 경로가 **두 번** 돌아 **열린 행이 둘** 생긴다. 판정이 오면
`order by attempt_seq desc limit 1` 이 **최신 것**을 닫으므로 **무너진 `target_form` 을 가진 첫 행이
열린 채 남는다.** ⛔ 그 뒤 처리는 `resolve_dangling` 이 정하고 **이 회차는 그것을 재지 않았다.**

---

## 4. AC#3 — **판정: 앱의 내용 검사로는 막을 수 없다**

| 층 | 지금 하는 것 | 더 할 수 있는가 |
|---|---|---|
| `models/pronunciation.py` 파싱 | `target_form` 이 **비었으면** 폐기 · `target_sound` 는 `_optional_text` | 내용 검사 없음 |
| `link_pattern` SQL | `length(btrim(target_sound)) > 0` — **빈 값만** 거른다 | 같음 |

⛔ **형태 검사(`^[a-z0-9]+_as_[a-z0-9]+$` 류)는 이 리포가 이미 기각한 방향이다** —
`nova.py` 의 소리 줄 주석이 *"`X_as_Y` 형태는 Nova 가 지어내는 값이라 규약이 아니다 … 파싱하면
다음 키 모양에서 조용히 깨진다"* 로 근거를 갖는다. 그리고 **`r as r` 의 문제는 형태가 아니라 의미**다
(「r 을 r 로」는 형태가 옳고 뜻이 틀렸다) — 형태 검사로는 잡히지 않는다.

**좁게 잡을 수 있는 것 하나**: 양쪽이 **같은** 키(`r as r` · `r_as_r`)는 **정의상 오류가 아니다.**
그 한 모양은 임의 형태를 파싱하지 않고도 거를 수 있다. ⚠️ **그 한 모양만 잡는다** — 일반해가 아니다.

⇒ **AC#3 의 답: 앱 단독으로는 못 막는다.** 빈 값 거르기가 상한이고, 그 위는 **모델 쪽 문제**다.

---

## 5. AC#1 은 사용자 판정이라 남긴다 — 올릴 재료를 여기 모은다

AC#1: *「결정 50 의 ③ 판정 기준에 「내용의 질」을 넣을지 판정한다」*.

이 회차가 그 판단에 더하는 사실 셋:

1. **도착률과 내용의 질은 따로 움직인다** — 이 봉투는 tool 을 **6/6 냈고** 내용은 **6/6 쓸 수 없었다.**
   ⇒ 도착률만으로 우회로를 걷어내면 **기록은 생기고 그 기록이 틀린 구간**이 생긴다.
2. **프롬프트로는 고쳐지지 않는다**(§2) — 「문면을 고치면 되니 ③을 열어도 된다」가 성립하지 않는다.
3. **앱이 고칠 수 있는 자리가 하나 있다**(§3-1) — 둘째 호출의 옳은 `target_form` 을 **버리지 않는 것**.
   그것은 프롬프트가 아니라 **저장 코드**의 일이고 ③과 독립적으로 진행할 수 있다.

⛔ **AC#4 는 그대로 유지한다** — 이 태스크가 닫히기 전에 결정 50 의 ③을 실행하지 않는다.

## 6. 남긴 것

- ⚠️ **제품 프롬프트 팔의 payload 는 아직 0건이다**(§1) — 제품 경로에서 tool 이 오지 않기 때문이다.
  그래서 §2·§3 의 판정은 **기준 팔의 성질**이고 제품 경로로 옮길 때 다시 봐야 한다.
- ⚠️ **콘텐츠 필터에 걸린 낱말을 특정하지 않았다**(§2-1) — 두 낱말을 한 번에 뺐다.
- ⚠️ **`resolve_dangling` 이 열린 두 행을 어떻게 수렴시키는지 재지 않았다**(§3-2).
