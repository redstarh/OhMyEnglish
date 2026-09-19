begin;
insert into users (id, display_name, timezone, current_level)
values ('b1000000-0000-4000-8000-000000000001', 'TS-22 b1 isolated fixture', 'Asia/Seoul', 'A2');

-- A: no_utterances / 영구 (발화 0건 · job 0건)
insert into learning_sessions (id, user_id, mode, status, started_at, ended_at)
values ('b1a10000-0000-4000-8000-000000000001','b1000000-0000-4000-8000-000000000001','speaking','completed',now(),now());

-- B: no_utterances / 회복 대상 (발화 1건 · job 0건)
insert into learning_sessions (id, user_id, mode, status, started_at, ended_at)
values ('b1a10000-0000-4000-8000-000000000002','b1000000-0000-4000-8000-000000000001','speaking','completed',now(),now());
insert into utterances (id, session_id, speaker, utterance_type, transcript, sequence_no)
values ('b1b00000-0000-4000-8000-000000000002','b1a10000-0000-4000-8000-000000000002','user','learning','I go to gym yesterday.',1);

-- C: analyzing (job 1건 running · lease 신선 → claim 대상 아님)
insert into learning_sessions (id, user_id, mode, status, started_at, ended_at)
values ('b1a10000-0000-4000-8000-000000000003','b1000000-0000-4000-8000-000000000001','speaking','completed',now(),now());
insert into utterances (id, session_id, speaker, utterance_type, transcript, sequence_no)
values ('b1b00000-0000-4000-8000-000000000003','b1a10000-0000-4000-8000-000000000003','user','learning','She have two cat.',1);
insert into analysis_jobs (id, job_type, utterance_id, status, locked_at, locked_by)
values ('b1c00000-0000-4000-8000-000000000003','analyze_utterance','b1b00000-0000-4000-8000-000000000003','running',now(),'ts22-b1-fixture-not-claimable');
commit;
