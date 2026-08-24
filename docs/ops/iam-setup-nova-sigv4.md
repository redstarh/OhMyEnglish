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
      "Action": "bedrock:InvokeModelWithBidirectionalStream",
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

# ③ Nova 양방향 스파이크 재실행 — "스트림 열림"이 나와야 최종 통과
#    (Phase 1에서 폐기한 스파이크를 재작성해 실행: aws-sdk-bedrock-runtime 0.10.0,
#     Python 3.12+, invoke_model_with_bidirectional_stream(amazon.nova-2-sonic-v1:0))
```

③이 통과하면 Nova 실연동(Phase 2) 착수 조건이 충족된다. 설계서 §10-1 관문.

> SDK 함정 (실측): 이 SDK는 자격증명 실패를 즉시 예외로 주지 않고 **무응답(타임아웃)**으로 나타낸다. 스파이크에 단계별 타임아웃을 걸어야 원인을 구분할 수 있다 — 설계서 §4.2.

## 6. 보안 수칙

- Secret access key는 `.env` 외 어디에도 저장하지 않는다 (메모, Slack, 커밋 금지 — 이 문서에도 실키를 적지 않는다)
- 유출 의심 시 IAM 콘솔에서 해당 access key를 즉시 Deactivate → 새 키 발급 → `.env` 교체
- 이 user에는 Bedrock invoke 외 어떤 권한도 추가하지 않는다
