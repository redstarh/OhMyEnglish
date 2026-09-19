begin;
delete from analysis_jobs where id='b1c00000-0000-4000-8000-000000000003';
delete from utterances where session_id in (
  'b1a10000-0000-4000-8000-000000000002','b1a10000-0000-4000-8000-000000000003');
delete from learning_sessions where user_id='b1000000-0000-4000-8000-000000000001';
delete from users where id='b1000000-0000-4000-8000-000000000001';
commit;
