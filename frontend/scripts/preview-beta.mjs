import { spawn } from "node:child_process";
import net from "node:net";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const frontendRoot = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  ".."
);
const nextCommand = path.join(
  frontendRoot,
  "node_modules",
  "next",
  "dist",
  "bin",
  "next"
);
const envLocalPath = path.join(frontendRoot, ".env.local");

function checkPort(port, host) {
  return new Promise((resolve) => {
    const socket = net.createConnection({ port, host });
    socket.setTimeout(1000);
    socket.once("connect", () => {
      socket.destroy();
      resolve(true);
    });
    socket.once("timeout", () => {
      socket.destroy();
      resolve(false);
    });
    socket.once("error", () => resolve(false));
  });
}

if (!fs.existsSync(nextCommand)) {
  console.error(
    [
      "UniWay frontend dependencies are not installed.",
      "",
      "Run these commands once:",
      "  cd D:\\UniWay\\frontend",
      "  npm install",
      "",
      "Then start the beta preview:",
      "  npm run preview:beta"
    ].join("\n")
  );
  process.exit(1);
}

if (!fs.existsSync(envLocalPath)) {
  console.error(
    [
      "UniWay frontend environment file is missing.",
      "",
      "Create it once in PowerShell:",
      "  cd D:\\UniWay\\frontend",
      "  Copy-Item .env.example .env.local",
      "",
      "Or in Git Bash:",
      "  cd /d/UniWay/frontend",
      "  cp .env.example .env.local"
    ].join("\n")
  );
  process.exit(1);
}

if (await checkPort(3000, "127.0.0.1")) {
  console.error(
    [
      "Port 3000 is already in use.",
      "An UniWay preview may already be open at http://127.0.0.1:3000.",
      "Close the older preview terminal with Ctrl+C before starting another one."
    ].join("\n")
  );
  process.exit(1);
}

try {
  const response = await fetch("http://127.0.0.1:8000/api/v1/health/", {
    signal: AbortSignal.timeout(2500)
  });
  if (!response.ok) {
    console.warn(
      `UniWay backend health check returned HTTP ${response.status}.`
    );
  }
} catch {
  console.warn(
    [
      "UniWay backend is not reachable at http://127.0.0.1:8000.",
      "The interface will show a protected retry screen until the backend is available.",
      "Start the backend in another PowerShell window:",
      "  powershell -ExecutionPolicy Bypass -File D:\\UniWay\\backend\\scripts\\run-local-preview.ps1",
      ""
    ].join("\n")
  );
}

const child = spawn(
  process.execPath,
  [nextCommand, "dev", "--hostname", "127.0.0.1", "--port", "3000"],
  {
    cwd: frontendRoot,
    stdio: "inherit",
    shell: false
  }
);

child.on("exit", (code) => {
  process.exit(code ?? 1);
});
