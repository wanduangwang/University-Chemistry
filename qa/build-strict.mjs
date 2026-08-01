import { spawnSync } from "node:child_process";

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

console.log("Strict MyST build passed with no error/warning diagnostics.");
