# Nova Sonic 연동용 IAM(SigV4) 설정 가이드

- 작성: 2026-08-25
- 대상: OhMyEnglish Phase 2 (Nova Sonic 실연동) 착수 전 캡틴이 직접 수행
- 관련: `docs/design/2026-08-24-first-vertical-slice-design.md` §4.1, `handoff/HANDOFF.md` 하드 블로커 절

---

## 1. 왜 필요한가 (실측 근거)

Nova Sonic 양방향 스트림은 **Bedrock API Key(bearer)를 서비스 차원에서 거부한다.** 2026-08-25 us-west-2 실측:

| 엔드포인트 | 현재 bearer token |
|---|---|
| `/invoke` (Claude) | HTTP 200 ✅ |
| `/invoke-with-response-stream` | HTTP 200 ✅ |
| `/invoke-with-bidirectional-stream` (Nova) | **HTTP 403 `This operation does not support API Keys`** ❌ |

같은 키가 다른 연산에선 통과하므로 키 문제가 아니라 **연산 자체의 제약**이다. Python SDK(`aws-sdk-bedrock-runtime`)도 SigV4만 지원한다(`HTTPAuthSchemeResolver`가 SigV4 옵션만 반환).

**방침 (설계서 §4.1)**: 백엔드는 SigV4 단일 경로로 통일한다 — SigV4는 Nova 양방향과 Claude invoke 양쪽에 다 쓸 수 있다. 현재 `AWS_BEARER_TOKEN_BEDROCK`은 Claude Code 세션용으로만 남긴다.

## 2. 방식 선택 (캡틴 결정 필요)

| 방식 | 장점 | 단점 | 적합도 |
|---|---|---|---|
| **A. 전용 IAM user access key → `.env`** (권장) | 상시 구동 로컬 서버에 재로그인 불필요, 가장 단순 | 장기 자격증명 — 유출 시 로테이션 필요 | 로컬 단독 개인 도구에 적합 ✅ |
| B. IAM Identity Center (`aws login`) | 임시 자격증명 자동 순환 — 더 안전 | 세션 만료마다 재로그인, 백그라운드 서버와 궁합 나쁨 | 나중에 상시 배포 시 재검토 |
| C. 기존 admin 키 재사용 | 설정 0 | 최소권한 위반 — 학습 앱이 계정 전체 권한을 가짐 | ❌ 비권장 |

아래는 **A안 기준** 절차다.

## 3. A안 절차 — 전용 IAM user 생성 (AWS 콘솔)

> 현재 로컬에 SigV4 자격증명이 없어 IAM 조작용 CLI를 못 쓴다 (`aws sts get-caller-identity` 실패, bearer는 Bedrock 전용). **콘솔에서 진행한다.**

1. **IAM → Users → Create user**
   - 이름 예: `ohmyenglish-local`
   - ⚠️ "Provide user access to the AWS Management Console" **체크 안 함** (프로그래밍 전용)
2. **권한: 인라인 정책으로 아래 JSON 첨부** (Attach policies directly → Create inline policy → JSON)
3. 생성 후 **Security credentials 탭 → Create access key**
   - Use case: `Local code` 선택
   - Access key ID / Secret access key를 안전하게 복사 (Secret은 이때 한 번만 표시)

### 최소권한 정책 JSON

`<ACCOUNT_ID>`를 실제 계정 ID(12자리)로 교체한다.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "NovaSonicBidirectional",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithBidirectionalStream"
      ],
      "Resource": "arn:aws:bedrock:us-west-2::foundation-model/amazon.nova-2-sonic-v1:0"
    },
    {
      "Sid": "ClaudeAnalysis",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:us-west-2:<ACCOUNT_ID>:inference-profile/us.anthropic.claude-opus-5",
        "arn:aws:bedrock:*::foundation-model/anthropic.claude-opus-5*"
      ]
    }
  ]
}
```

> 참고: `us.` 추론 프로필은 미국 리전들로 라우팅되므로, 프로필 ARN과 함께 **각 리전의 기반 모델 ARN**(`arn:aws:bedrock:*::foundation-model/...`)에도 권한이 필요하다. 위 JSON이 둘 다 커버한다. 첫 호출에서 AccessDenied가 나면 오류 메시지에 찍힌 정확한 ARN을 Resource에 추가한다.

> ⚠️ **실측 정정 (2026-08-26).** `NovaSonicBidirectional`에 처음에는 `bedrock:InvokeModelWithBidirectionalStream`만 넣었는데 **HTTP 403이 났다.** 서비스가 돌려준 실제 이유:
>
> ```
> User: arn:aws:iam::<ACCOUNT_ID>:user/ohmyenglish-local is not authorized to perform:
> bedrock:InvokeModel on resource:
> arn:aws:bedrock:us-west-2::foundation-model/amazon.nova-2-sonic-v1:0
> because no identity-based policy allows the bedrock:InvokeModel action
> ```
>
> 즉 양방향 스트림 연산도 **`bedrock:InvokeModel` 권한을 함께 요구한다.** 위 JSON은 두 action을 모두 넣도록 고쳤다.
>
> 이 메시지를 얻는 데 진단 장치가 필요했다 — `aws-sdk-bedrock-runtime` 0.10.0은 403 응답 **본문을 버리고** `AccessDeniedException('')`만 남긴다. 빈 메시지로는 "정책 누락"과 "모델 접근 미승인"을 구분할 수 없다. `scripts/spike_nova_bidirectional.py`의 `DiagnosticTransport`가 그 본문을 붙잡아 출력하므로, 다음 AccessDenied에서도 같은 방식으로 원인을 읽을 수 있다.

## 4. `.env` 구성 (OhMyEnglish 백엔드 전용)

프로젝트 루트 `.env` (이미 `.gitignore` 대상 — 커밋되지 않음):

```bash
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-west-2
```

⚠️ **주의**
- 백엔드 프로세스 환경에 `AWS_BEARER_TOKEN_BEDROCK`을 넣지 않는다 — SigV4 단일 경로 원칙(설계서 §4.1). 셸 전역에 있는 bearer 변수가 백엔드로 상속되지 않게 `.env`만 로드한다.
- 이 키는 브라우저·프론트엔드에 절대 노출하지 않는다 (`HANDOFF.md` 보안 원칙).

## 5. 발급 후 검증 절차 (순서대로)

```bash
# ① 자격증명 자체 확인 — ohmyenglish-local ARN이 나와야 함
env -i AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=... AWS_REGION=us-west-2 \
  aws sts get-caller-identity

# ② Claude SigV4 경로 확인 — HTTP 200 + "ok" 응답
env -i AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=... \
  aws bedrock-runtime invoke-model --region us-west-2 \
  --model-id us.anthropic.claude-opus-5 \
  --body '{"anthropic_version":"bedrock-2023-05-31","max_tokens":16,"messages":[{"role":"user","content":"say ok"}]}' \
  --cli-binary-format raw-in-base64-out /tmp/out.json && cat /tmp/out.json

# ③ Nova 양방향 스파이크 — "스트림 열림"이 나와야 최종 통과
cd app/backend && .venv/bin/python ../../scripts/spike_nova_bidirectional.py
#   불투명한 AccessDeniedException('')이 나오면 본문 포착을 켜서 원인을 읽는다:
#   OMY_SPIKE_CAPTURE_BODY=1 .venv/bin/python ../../scripts/spike_nova_bidirectional.py
```

③이 통과하면 Nova 실연동(Phase 2) 착수 조건이 충족된다. 설계서 §10-1 관문.

### 5.1 스파이크의 판정 기준 (2026-08-26 실측으로 재정의)

처음에는 `await_output()`이 값을 돌려주는 것을 성공 조건으로 잡았는데 **그것이 틀렸다** — Nova Sonic은 클라이언트가 전체 초기화 시퀀스(sessionStart → promptStart → contentStart …)를 보내기 전까지 아무 이벤트도 내보내지 않는다. 그 프로토콜 구현은 Phase 2의 몫이다.

스파이크가 판정하는 것은 **자격증명이 이 연산에 통하는가** 하나다. 인증·인가는 요청 시점에 평가되므로 실패하면 즉시 4xx가 온다(실측: 권한 부족 시 1초 안에 403). 따라서 **4xx·예외 → FAIL / 정해진 시간 조용히 유지 → PASS**다.

"조용함 = 성공"은 위험한 기준이라 **음성 대조군**을 함께 돌린다 — 존재하지 않는 모델(`amazon.nova-sonic-v1:0`, "2"가 없는 쪽)로 같은 호출을 해 하네스가 실패를 실제로 잡아내는지 먼저 확인한다. 대조군이 조용하면 하네스가 고장 난 것이므로 판정하지 않는다.

**본문 포착은 기본 꺼짐**이다. 응답 본문은 한 번만 읽을 수 있고 `response.body`가 읽기 전용이라 되돌릴 수 없어, 켜면 SDK의 예외 타입이 `SmithyError: premature EOF`로 바뀐다 — 즉 **진단이 진단을 가린다**(실측: 대조군의 `ValidationException`이 가려졌다). 불투명한 AccessDenied를 만났을 때만 켠다.

> SDK 함정 (실측): 이 SDK는 자격증명 실패를 즉시 예외로 주지 않고 **무응답(타임아웃)**으로 나타낸다. 스파이크에 단계별 타임아웃을 걸어야 원인을 구분할 수 있다 — 설계서 §4.2.

## 6. 보안 수칙

- Secret access key는 `.env` 외 어디에도 저장하지 않는다 (메모, Slack, 커밋 금지 — 이 문서에도 실키를 적지 않는다)
- 유출 의심 시 IAM 콘솔에서 해당 access key를 즉시 Deactivate → 새 키 발급 → `.env` 교체
- 이 user에는 Bedrock invoke 외 어떤 권한도 추가하지 않는다

### ⛔ 2026-09-09 — 로테이션을 하지 않기로 결정했다 (캡틴 결정 41). 위 둘째 항목의 예외다

`TASK-38`이 *"키가 대화 기록을 경유해 노출됐다"*로 열려 있었고 **캡틴이 로테이션을 면제했다.**
**이것은 위 둘째 수칙("유출 의심 시 즉시 Deactivate")의 명시적 예외이므로 조용히 두지 않고
여기 적는다.**

**확인한 것** (2026-09-09, 팀리드 직접): **이 저장소의 추적 파일에 키가 0건이다** —
`git grep -nE "AKIA[0-9A-Z]{16}|aws_secret_access_key\s*=\s*[A-Za-z0-9/+=]{40}"` 가 빈 출력이다.
즉 노출 경로는 **리포 밖**(대화 기록)이고 리포에서 지울 것은 없었다. 위 첫째 수칙이 지켜졌다.

⚠️ **받아들이는 잔여 위험 — 이것이 이 결정의 대가다**: 그 키는 **계속 유효**하고 노출된 기록은
회수할 수 없다. 권한이 Bedrock invoke로 좁혀져 있다는 것(위 셋째 항목)이 피해 범위를 제한하는
유일한 방어다. **비용 청구를 관측하면 즉시 이 결정을 다시 본다** — 그것이 이 예외의 유효 조건이다.
