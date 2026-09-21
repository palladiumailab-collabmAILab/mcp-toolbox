import { spawnSync } from "node:child_process";

const requiredSecrets = new Set(["GEMINI_API_KEY", "MCP_BEARER_TOKEN"]);
const npxCommand = process.platform === "win32" ? "npx.cmd" : "npx";
const result = spawnSync(npxCommand, ["wrangler", "secret", "list", "--format=json"], {
  encoding: "utf8",
  stdio: ["ignore", "pipe", "pipe"],
});

if (result.error || result.status !== 0) {
  console.error("Unable to list Worker secrets; refusing to deploy.");
  if (result.stderr?.trim()) {
    console.error(result.stderr.trim());
  }
  process.exit(1);
}

let secrets;
try {
  secrets = JSON.parse(result.stdout);
} catch {
  console.error("Wrangler returned invalid JSON while listing Worker secrets; refusing to deploy.");
  process.exit(1);
}

const configuredNames = new Set(
  (Array.isArray(secrets) ? secrets : (secrets?.secrets ?? []))
    .map((secret) => (typeof secret === "string" ? secret : secret?.name))
    .filter(Boolean),
);
const missingSecrets = [...requiredSecrets].filter((name) => !configuredNames.has(name));

if (missingSecrets.length > 0) {
  console.error(`Missing required Worker secret(s): ${missingSecrets.join(", ")}`);
  console.error("Provision them with `wrangler secret put` before deploying.");
  process.exit(1);
}

console.log("Deployment preflight passed: required Worker secrets are configured.");
