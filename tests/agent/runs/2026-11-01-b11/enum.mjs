// 회차 b11 — 눌 수 있는 요소 목록 식
export const ENUM = `(() => {
  const sel = 'a[href],button,input,select,textarea,summary,[role=button],[role=tab],[role=switch],[role=link],[tabindex]:not([tabindex="-1"]),video,iframe';
  const set = new Set(document.querySelectorAll(sel));
  for (const el of document.querySelectorAll('body *')) { const k = Object.keys(el).find(k => k.startsWith('__reactProps')); if (k && el[k] && typeof el[k].onClick === 'function') set.add(el); }
  return [...set].map((el, i) => { const r = el.getBoundingClientRect(); const cs = getComputedStyle(el);
    return { i, tag: el.tagName.toLowerCase(), tid: el.dataset.testid ?? null, text: (el.innerText || el.value || el.getAttribute('aria-label') || el.title || '').trim().replace(/\\s+/g,' ').slice(0, 80),
      href: el.getAttribute('href'), type: el.getAttribute('type'), disabled: !!el.disabled, ariaDisabled: el.getAttribute('aria-disabled'), current: el.getAttribute('aria-current'),
      pressed: el.getAttribute('aria-pressed'), title: el.title || null, visible: r.width > 0 && r.height > 0 && cs.visibility !== 'hidden', inNav: !!el.closest('nav,aside,header'),
      rect: [Math.round(r.x), Math.round(r.y + scrollY), Math.round(r.width), Math.round(r.height)] }; }).filter(e => e.visible);
})()`;

// ENUM 의 i 와 같은 순서의 요소 배열
export const SET = `(() => { const sel = 'a[href],button,input,select,textarea,summary,[role=button],[role=tab],[role=switch],[role=link],[tabindex]:not([tabindex="-1"]),video,iframe';
  const set = new Set(document.querySelectorAll(sel));
  for (const el of document.querySelectorAll('body *')) { const k = Object.keys(el).find(k => k.startsWith('__reactProps')); if (k && el[k] && typeof el[k].onClick === 'function') set.add(el); }
  return [...set]; })()`;
