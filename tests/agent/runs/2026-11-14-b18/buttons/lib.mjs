// 회차 b18 버튼 탭 공용 — CDP 9462 에 붙고, 증거를 이 폴더의 evidence/ 에 떨어뜨림.
// b16 lib.mjs 를 바탕으로 포트를 바꾸고, b17 live.mjs 의 가짜 인식기와 판정 요청 대역을 더했음.
import { mkdirSync, writeFileSync } from "node:fs";
import { chromium } from "/Users/redstar/MyProject/OhMyEnglish/tests/agent/tools/node_modules/playwright/index.mjs";

export const APP = "http://localhost:3000";
export const API = "http://localhost:8002";
export const OUT = new URL("./evidence/", import.meta.url).pathname;
mkdirSync(OUT, { recursive: true });

export async function connect() {
  const browser = await chromium.connectOverCDP("http://127.0.0.1:9462");
  return { browser, ctx: browser.contexts()[0] };
}

export async function newPage(ctx, width, height = width < 600 ? 844 : 900) {
  const page = await ctx.newPage();
  await page.setViewportSize({ width, height });
  return page;
}

export function save(name, data) {
  writeFileSync(OUT + name, typeof data === "string" ? data : JSON.stringify(data, null, 2));
}

/** 판정 한 줄 — {id, screen, action, expect, actual, verdict} */
export function verdicts(name) {
  const rows = [];
  return {
    rows,
    add(row) {
      rows.push(row);
      console.log(`[${row.verdict}] ${row.id} ${row.action} — ${row.actual}`);
      save(name, rows); // 중간에 죽어도 그때까지의 판정이 남게 매번 씀
    },
    flush() {
      save(name, rows);
    },
  };
}

/** 화면의 보이는 버튼·링크(summary 포함) 목록과 계산된 모양. */
export async function inventory(page) {
  return page.evaluate(() => {
    const out = [];
    for (const el of document.querySelectorAll("a, button, summary, [role=button]")) {
      const r = el.getBoundingClientRect();
      const cs = getComputedStyle(el);
      if (r.width === 0 || r.height === 0 || cs.visibility === "hidden" || cs.display === "none" || (el.checkVisibility && !el.checkVisibility())) continue;
      out.push({
        tag: el.tagName.toLowerCase(),
        testid: el.getAttribute("data-testid"),
        text: (el.innerText || el.getAttribute("aria-label") || "").replace(/\s+/g, " ").trim().slice(0, 60),
        href: el.getAttribute("href"),
        omy: el.classList.contains("omy-button"),
        primary: el.classList.contains("omy-button-primary"),
        disabled: el.disabled === true,
        ariaDisabled: el.getAttribute("aria-disabled"),
        ariaPressed: el.getAttribute("aria-pressed"),
        h: Math.round(r.height * 10) / 10,
        w: Math.round(r.width * 10) / 10,
        top: Math.round(r.top + window.scrollY),
        fontSize: cs.fontSize,
        bg: cs.backgroundColor,
        color: cs.color,
        radius: cs.borderRadius,
      });
    }
    return out;
  });
}

export async function waitUrl(page, pred, ms = 8000) {
  const end = Date.now() + ms;
  while (Date.now() < end) {
    if (pred(new URL(page.url()))) return true;
    await page.waitForTimeout(100);
  }
  return false;
}

export async function shot(page, name) {
  try {
    await page.screenshot({ path: OUT + name, fullPage: false });
  } catch {
    /* 보조 증거 — 실패해도 판정과 무관 */
  }
}

export async function home(page) {
  await page.goto(APP + "/", { waitUntil: "domcontentloaded" });
  await page.waitForSelector('[data-testid="home-hero"][data-state="ready"]', { timeout: 20000 });
  await page.waitForTimeout(800);
}

/** b17 live.mjs 의 가짜 인식기 — 각본(window.__srScript)대로 결과·오류를 냄. 음성 합성은 0.3초로 끝냄. */
export function installFakes() {
  const state = { calls: [], instances: 0, timers: [] };
  window.__sr = state;
  window.__srScript = [];
  class FakeRecognition {
    constructor() {
      state.instances += 1;
      this.segments = [];
      this.onresult = this.onerror = this.onend = this.onaudiostart = null;
      this.ended = false;
    }
    emit(text, isFinal) {
      this.segments = [...this.segments.filter((s) => s.isFinal), { text, isFinal }];
      const results = this.segments.map((s) => Object.assign([{ transcript: s.text }], { isFinal: s.isFinal }));
      this.onresult?.({ results, resultIndex: 0 });
    }
    end() {
      if (this.ended) return;
      this.ended = true;
      this.onend?.();
    }
    clear() {
      state.timers.forEach(clearTimeout);
      state.timers = [];
    }
    start() {
      state.calls.push(["start", Math.round(performance.now())]);
      state.timers.push(setTimeout(() => this.onaudiostart?.(), 100));
      for (const step of window.__srScript) {
        state.timers.push(
          setTimeout(() => {
            state.calls.push([step.type, Math.round(performance.now()), step.text ?? step.error ?? ""]);
            if (step.type === "interim") this.emit(step.text, false);
            else if (step.type === "final") this.emit(step.text, true);
            else if (step.type === "error") this.onerror?.({ error: step.error });
            else if (step.type === "end") this.end();
          }, 100 + step.at),
        );
      }
    }
    stop() {
      state.calls.push(["stop", Math.round(performance.now())]);
      this.clear();
      const pending = this.segments.find((s) => !s.isFinal);
      setTimeout(() => {
        if (pending) this.emit(pending.text, true);
        this.end();
      }, 50);
    }
    abort() {
      state.calls.push(["abort", Math.round(performance.now())]);
      this.clear();
      setTimeout(() => {
        this.onerror?.({ error: "aborted" });
        this.end();
      }, 10);
    }
  }
  window.SpeechRecognition = FakeRecognition;
  window.webkitSpeechRecognition = FakeRecognition;
  if (window.speechSynthesis) {
    window.speechSynthesis.speak = (utterance) => {
      setTimeout(() => utterance.onstart?.(), 10);
      setTimeout(() => utterance.onend?.(), 300);
    };
    window.speechSynthesis.cancel = () => {};
  }
}

/** 판정 요청과 진도 저장을 page.route 로 받아 가짜 응답을 줌 — 요청 본문만 기록하고 DB 에 쓰지 않음. */
export async function routeCourse(page) {
  const posts = [];
  const progress = [];
  const counts = {};
  await page.route("**/api/course/sentences/*/attempts/text", async (route) => {
    const request = route.request();
    const key = request.url().split("/sentences/")[1].split("/")[0];
    const body = request.postDataJSON();
    posts.push({ key, body, at: Date.now() });
    counts[key] = (counts[key] ?? 0) + 1;
    const words = String(body.transcript).split(/\s+/).map((word) => ({ word, verdict: "match" }));
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ transcript: body.transcript, words, attempts: 100 + counts[key] }) });
  });
  await page.route("**/api/course/days/*/progress", async (route) => {
    progress.push({ url: route.request().url(), body: route.request().postDataJSON() });
    await route.fulfill({ status: 204, body: "" });
  });
  const pcm = [];
  await page.route("**/api/course/sentences/*/attempts", async (route) => {
    pcm.push(route.request().url());
    await route.fulfill({ status: 500, body: "" });
  });
  return { posts, progress, pcm };
}
