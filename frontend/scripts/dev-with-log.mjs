import { spawn } from "node:child_process";
import { createWriteStream, mkdirSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = dirname(fileURLToPath(import.meta.url));
const frontendDir = resolve(scriptDir, "..");
const repoRoot = resolve(frontendDir, "..");
const logRoot = resolve(repoRoot, process.env.LOG_PATH || join("data", "logs"));
const logDir = join(logRoot, "web");

mkdirSync(logDir, { recursive: true });

const combinedLog = createWriteStream(join(logDir, "web-frontend.log"), { flags: "a" });
const stdoutLog = createWriteStream(join(logDir, "web-frontend.out.log"), { flags: "a" });
const stderrLog = createWriteStream(join(logDir, "web-frontend.err.log"), { flags: "a" });

function writeLine(stream, text) {
  stream.write(`[${new Date().toISOString()}] ${text}\n`);
}

writeLine(combinedLog, `Starting Vite dev server. Log directory: ${logDir}`);

const viteBin = process.platform === "win32" ? "vite.cmd" : "vite";
const child = spawn(viteBin, ["--host", "127.0.0.1", "--port", "5173"], {
  cwd: frontendDir,
  env: process.env,
  shell: process.platform === "win32",
});

child.stdout.on("data", (chunk) => {
  process.stdout.write(chunk);
  combinedLog.write(chunk);
  stdoutLog.write(chunk);
});

child.stderr.on("data", (chunk) => {
  process.stderr.write(chunk);
  combinedLog.write(chunk);
  stderrLog.write(chunk);
});

child.on("exit", (code, signal) => {
  writeLine(combinedLog, `Vite dev server exited with code=${code ?? ""} signal=${signal ?? ""}`);
  combinedLog.end();
  stdoutLog.end();
  stderrLog.end();
  process.exit(code ?? 0);
});
