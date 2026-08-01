import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const EXPECTED_TABLES = 138;
const EXPECTED_TABLE_FORMULAE = 1154;

const npm = process.platform === "win32" ? "npm.cmd" : "npm";
const result = spawnSync(npm, ["run", "build:raw", "--silent"], {
  cwd: new URL("..", import.meta.url),
  encoding: "utf8",
  shell: process.platform === "win32",
});

const output = `${result.stdout ?? ""}${result.stderr ?? ""}`;
process.stdout.write(output);
const diagnostics = output
  .split(/\r?\n/)
  .filter((line) => line.includes("⛔️") || line.includes("⚠️"));

if (result.status !== 0 || diagnostics.length > 0) {
  if (result.error) console.error(result.error);
  console.error(
    `Strict MyST build failed: exit=${result.status}, diagnostics=${diagnostics.length}`,
  );
  process.exit(result.status || 1);
}

function htmlFiles(directory) {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const filename = path.join(directory, entry.name);
    if (entry.isDirectory()) return htmlFiles(filename);
    return entry.isFile() && entry.name.endsWith(".html") ? [filename] : [];
  });
}

const htmlRoot = fileURLToPath(new URL("../_build/html/", import.meta.url));
let tableCount = 0;
let formulaCount = 0;
let emptyFormulaCount = 0;
for (const filename of htmlFiles(htmlRoot)) {
  const html = fs.readFileSync(filename, "utf8");
  for (const match of html.matchAll(/<table\b[\s\S]*?<\/table>/gi)) {
    const table = match[0];
    tableCount += 1;
    formulaCount += [...table.matchAll(/<span class="katex"[^>]*>/gi)].length;
    emptyFormulaCount += [
      ...table.matchAll(/<span class="katex"[^>]*>\s*<\/span>/gi),
    ].length;
  }
}

if (
  tableCount !== EXPECTED_TABLES ||
  formulaCount !== EXPECTED_TABLE_FORMULAE ||
  emptyFormulaCount !== 0
) {
  console.error(
    "Strict MyST build failed table-math verification: " +
      `tables=${tableCount}, formulae=${formulaCount}, ` +
      `empty=${emptyFormulaCount}`,
  );
  process.exit(1);
}

console.log(
  "Strict MyST build passed with no error/warning diagnostics; " +
    `${formulaCount} table formulae rendered in ${tableCount} tables.`,
);
