// 회차 b16 버튼 탭 공용 — CDP 9402 에 붙고, 증거를 이 폴더의 evidence/ 에 떨어뜨림.
import { mkdirSync, writeFileSync, appendFileSync } from "node:fs";
import { chromium } from "/Users/redstar/MyProject/OhMyEnglish/tests/agent/tools/node_modules/playwright/index.mjs";

export const APP = "http://localhost:3000";
export const API = "http://localhost:8002";
export const OUT = new URL("./evidence/", import.meta.url).pathname;
mkdirSync(OUT, { recursive: true });

export async function connect() {
  const browser = await chromium.connectOverCDP("http://127.0.0.1:9402");
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

export function logger(name) {
  const path = OUT + name;
  writeFileSync(path, "");
  return (...parts) => {
    const line = `${new Date().toISOString()} ${parts.map((p) => (typeof p === "string" ? p : JSON.stringify(p))).join(" ")}`;
    appendFileSync(path, line + "\n");
    console.log(line);
  };
}

/** 판정 한 줄 — {id, screen, action, expect, actual, verdict, evidence} */
export function verdicts(name) {
  const rows = [];
  return {
    rows,
    add(row) {
      rows.push(row);
      console.log(`[${row.verdict}] ${row.id} ${row.action} — ${row.actual}`);
    },
    flush() {
      save(name, rows);
    },
  };
}

/** 화면의 보이는 버튼·링크 목록과 계산된 모양. */
export async function inventory(page) {
  return page.evaluate(() => {
    const out = [];
    for (const el of document.querySelectorAll("a, button, [role=button]")) {
      const r = el.getBoundingClientRect();
      const cs = getComputedStyle(el);
      if (r.width === 0 || r.height === 0 || cs.visibility === "hidden" || cs.display === "none") continue;
      out.push({
        tag: el.tagName.toLowerCase(),
        testid: el.getAttribute("data-testid"),
        text: (el.innerText || el.getAttribute("aria-label") || "").replace(/\s+/g, " ").trim().slice(0, 60),
        href: el.getAttribute("href"),
        cls: (el.getAttribute("class") || "").slice(0, 160),
        omy: el.classList.contains("omy-button"),
        primary: el.classList.contains("omy-button-primary"),
        disabled: el.disabled === true,
        ariaDisabled: el.getAttribute("aria-disabled"),
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
