// inventory.json 요약 — 화면마다 testid·문구·태그·href·모양. 기록 화면의 날짜 줄은 종류별 개수로 줄임.
import { readFileSync, writeFileSync } from "node:fs";
const OUT = new URL("./evidence/", import.meta.url).pathname;
const inv = JSON.parse(readFileSync(OUT + "inventory.json", "utf8"));
const lines = [];
for (const [W, screens] of Object.entries(inv)) {
  for (const [name, s] of Object.entries(screens)) {
    if (!s.items) {
      lines.push(`## ${W} ${name} ${JSON.stringify(s)}`);
      continue;
    }
    lines.push(`## ${W} ${name} url=${s.url}${s.requested ? " requested=" + s.requested : ""}`);
    const grouped = {};
    for (const it of s.items) {
      const key = ["history-day-link", "history-session-link"].includes(it.testid) || (it.tag === "summary")
        ? `${it.tag}:${it.testid}`
        : null;
      if (key) {
        grouped[key] = grouped[key] ?? { n: 0, sample: it };
        grouped[key].n += 1;
        continue;
      }
      lines.push(`- ${it.tag} ${it.testid ?? "-"} "${it.text}" ${it.href ?? ""} | omy=${it.omy} pri=${it.primary} h=${it.h} fs=${it.fontSize} bg=${it.bg} r=${it.radius}${it.disabled ? " DISABLED" : ""}${it.ariaDisabled ? " aria-dis=" + it.ariaDisabled : ""}${it.ariaPressed ? " pressed=" + it.ariaPressed : ""}`);
    }
    for (const [k, g] of Object.entries(grouped)) {
      const it = g.sample;
      lines.push(`- [${g.n}개] ${k} 예 "${it.text}" ${it.href ?? ""} | omy=${it.omy} h=${it.h} fs=${it.fontSize} bg=${it.bg}`);
    }
  }
}
writeFileSync(OUT + "inventory-summary.txt", lines.join("\n"));
console.log(lines.join("\n"));
