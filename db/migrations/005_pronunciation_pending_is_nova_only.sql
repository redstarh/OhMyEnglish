-- 005_pronunciation_pending_is_nova_only.sql
-- "대답 기다림(pending) 상태는 Nova tool만 만든다"를 표가 강제한다.
--
-- 왜 앱이 아니라 표인가: 이 불변조건을 앱에서만 지키면 규칙이 세 곳으로 흩어진다 —
--   ① 보조 신호 함수의 outcome 값역을 좁히고
--   ② 판정 UPDATE가 `signal_source = 'nova_tool'`을 매번 필터하고
--   ③ 그 필터가 실제로 동작하는지 보는 테스트를 따로 둔다.
-- 제약 한 줄로 옮기면 ②③이 필요 없어지고, raw INSERT로도 우회할 수 없다.
--
-- 무엇이 사라지는가: "보조 신호가 만든 열린 행을 Nova 판정이 닫아버려 signal_source가
-- 뒤섞이는" 케이스 자체다(코드 리뷰가 실측 재현한 결함). 케이스를 막는 코드가 아니라
-- 케이스가 존재할 수 없게 만든다.
--
-- 생명주기 요약 (설계서 §3.2):
--   Nova tool  → pending 으로 열리고 판정으로 닫힌다. 안 닫히면 종료 시 incorrect 로 수렴.
--   보조 신호  → 항상 판정된 상태로 태어난다. 열리지 않으므로 닫을 것도 없다.
--
-- 0행 표라 무손실이다 (2026-08-28 dev DB 실측).

alter table pronunciation_attempts
  add constraint pronunciation_attempts_pending_is_nova_only
  check (outcome <> 'pending' or signal_source = 'nova_tool');
