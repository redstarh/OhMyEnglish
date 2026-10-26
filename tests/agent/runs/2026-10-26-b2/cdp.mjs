// 회차 2026-10-26-b2 — 최소 CDP 클라이언트 (node 내장 WebSocket).
export const PORT = 9333;
export const R = "/Users/redstar/MyProject/OhMyEnglish/tests/agent/runs/2026-10-26-b2";
export const EV = `${R}/evidence`;

export async function pageTarget() {
  const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
  const page = list.find((t) => t.type === "page");
  if (!page) throw new Error("no page target");
  return page;
}

export async function connect(wsUrl) {
  const ws = new WebSocket(wsUrl);
  await new Promise((res, rej) => {
    ws.onopen = res;
    ws.onerror = rej;
  });
  let id = 0;
  const pending = new Map();
  const listeners = [];
  ws.onmessage = (msg) => {
    const data = JSON.parse(msg.data);
    if (data.id && pending.has(data.id)) {
      const { res, rej } = pending.get(data.id);
      pending.delete(data.id);
      if (data.error) rej(new Error(JSON.stringify(data.error)));
      else res(data.result);
    } else if (data.method) {
      for (const fn of listeners) fn(data);
    }
  };
  const send = (method, params = {}) =>
    new Promise((res, rej) => {
      const n = ++id;
      pending.set(n, { res, rej });
      ws.send(JSON.stringify({ id: n, method, params }));
    });
  return { ws, send, on: (fn) => listeners.push(fn), close: () => ws.close() };
}

export const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
