// shoot.mjs 측정에 body.scrollWidth 를 더함(문서 수준은 body overflow-x:hidden 에 가려짐 — probe-overflow.json)
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
const f = join(dirname(fileURLToPath(import.meta.url)), "shoot.mjs");
let s = readFileSync(f, "utf8");
const a = `    hOverflow: de.scrollWidth > de.clientWidth,`;
const b = `    bodyScrollWidth: document.body.scrollWidth,
    hOverflow: de.scrollWidth > de.clientWidth || document.body.scrollWidth > de.clientWidth,`;
if (!s.includes(a)) throw new Error("anchor missing");
s = s.replace(a, b);
writeFileSync(f, s);
console.log("patched");
