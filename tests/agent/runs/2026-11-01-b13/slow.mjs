// 회차 b13 — 화면을 찍을 틈을 만들려고 브라우저 쪽에서만 세션 소켓 메시지 전달을 늦춤(앱 코드는 그대로).
// stub 세션은 0.1초 안팎에 끝나 세션 화면이 찍히지 않음. 짧은 JSON 메시지(오디오가 아닌 것)마다 DELAY ms 를 두고,
// close 는 앞 메시지가 다 전달된 뒤에 넘김. 메시지 순서는 바꾸지 않음.
export const slowSocket = (delay = 700) => `(() => { const O = window.WebSocket; const D = ${delay};
  window.__wsTypes = [];
  class W extends O { constructor(...a) { super(...a); if (!String(a[0]).includes('/ws/session')) return; let q = Promise.resolve(); const self = this;
      const pm = Object.getOwnPropertyDescriptor(O.prototype, 'onmessage'), pc = Object.getOwnPropertyDescriptor(O.prototype, 'onclose');
      Object.defineProperty(this, 'onmessage', { configurable: true, set(fn) { pm.set.call(self, (ev) => { let t = null; try { t = JSON.parse(ev.data).type; } catch {}
          window.__wsTypes.push(t); const wait = typeof ev.data === 'string' && ev.data.length < 4000 ? D : 0;
          q = q.then(() => new Promise((r) => setTimeout(r, wait))).then(() => fn && fn.call(self, ev)); }); }, get() { return pm.get.call(self); } });
      Object.defineProperty(this, 'onclose', { configurable: true, set(fn) { pc.set.call(self, (ev) => { q = q.then(() => new Promise((r) => setTimeout(r, D))).then(() => fn && fn.call(self, ev)); }); }, get() { return pc.get.call(self); } });
  } }
  window.WebSocket = W; })()`;
