// 관측 수단 점검 — 같은 가짜 장치를 직접 열어 AudioContext 상태와 입력 세기를 잰다(앱 무관).
import { open, APP, sleep } from "./lib.mjs";
import { writeFileSync } from "node:fs";
const p = await open();
await p.nav(`${APP}/course`);
const r = await p.ev(`(async () => {
  const s = await navigator.mediaDevices.getUserMedia({ audio: true });
  const tr = s.getAudioTracks()[0];
  const ac = new AudioContext(); await ac.resume(); const an = ac.createAnalyser(); an.fftSize = 512;
  ac.createMediaStreamSource(s).connect(an); const buf = new Float32Array(512); const env = [];
  const t0 = performance.now();
  for (let i = 0; i < 260; i++) { await new Promise(r => setTimeout(r, 20)); an.getFloatTimeDomainData(buf); let e = 0; for (const v of buf) e += v * v; env.push([Math.round(performance.now() - t0), Math.round(Math.sqrt(e / 512) * 1000)]); }
  const st = { label: tr.label, settings: tr.getSettings(), state: ac.state, sr: ac.sampleRate, ct: ac.currentTime, max: Math.max(...env.map(x => x[1])), onsets: env.filter((x, i) => x[1] > 20 && (i === 0 || env[i-1][1] <= 20)) };
  tr.stop(); await ac.close(); return st; })()`);
writeFileSync(process.argv[2], JSON.stringify(r, null, 1)); console.log(JSON.stringify(r).slice(0, 900)); p.c.close();
