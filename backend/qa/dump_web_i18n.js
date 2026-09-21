// Loads web/i18n.js's `translations` table (everything before the DOM-dependent
// functions) and prints it as JSON, so Python QA checks can inspect it.
const fs = require("fs");
const vm = require("vm");
const path = require("path");
const src = fs.readFileSync(path.join(__dirname, "..", "..", "web", "i18n.js"), "utf8");
const cut = src.indexOf("function currentLang");
const head = src.slice(0, cut) + "\n;globalThis.__out = { SUPPORTED_LANGS, translations };";
const ctx = { globalThis: {} };
ctx.globalThis = ctx;
vm.createContext(ctx);
vm.runInContext(head, ctx);
process.stdout.write(JSON.stringify(ctx.__out));
