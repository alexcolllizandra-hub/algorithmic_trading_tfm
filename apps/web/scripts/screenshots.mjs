// Capture desktop + mobile screenshots of the redesigned research platform.
// Usage: node scripts/screenshots.mjs  (web on :3000 or :3002, API on :8000)
import { chromium } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import path from "node:path";

const BASE = process.env.WEB_BASE ?? "http://localhost:3000";
const API = process.env.API_BASE ?? "http://localhost:8000/api/v1";
const OUT = path.resolve(process.cwd(), "../../docs/platform/screenshots");

async function firstDevRunId() {
  const res = await fetch(`${API}/runs?limit=50`);
  const body = await res.json();
  const dev = (body.items ?? []).find((r) => r.kind === "development");
  return dev?.run_id ?? body.items?.[0]?.run_id ?? null;
}

async function shoot(page, name, url, { fullPage = true } = {}) {
  await page.goto(url, { waitUntil: "networkidle" });
  await page.waitForTimeout(1500);
  await page.screenshot({ path: path.join(OUT, `${name}.png`), fullPage });
  console.log("saved", name);
}

async function main() {
  await mkdir(OUT, { recursive: true });
  const runId = await firstDevRunId();
  if (!runId) throw new Error("No runs from API; start the API with real artifacts.");
  console.log("using run", runId);

  const browser = await chromium.launch();

  // Desktop dark (default)
  const desktopDark = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const d = await desktopDark.newPage();
  await shoot(d, "01_research_overview", `${BASE}/`);
  await shoot(d, "02_data_timeline", `${BASE}/datos-eda?run=${runId}`);
  await shoot(d, "03_eda_key_findings", `${BASE}/datos-eda?run=${runId}`);
  await shoot(d, "04_eda_gallery", `${BASE}/datos-eda#galeria-completa`);
  await shoot(d, "05_methodology", `${BASE}/metodologia`);
  await shoot(d, "06_experiments_fairness", `${BASE}/experimentos?run=${runId}&tab=fairness`);
  await shoot(d, "07_results_aggregate", `${BASE}/resultados?run=${runId}`);
  await shoot(
    d,
    "08_results_fold_detail",
    `${BASE}/resultados?run=${runId}&method=random_search&fold=0`
  );
  await shoot(d, "09_diagnostics", `${BASE}/diagnostico?run=${runId}`);
  await desktopDark.close();

  // Desktop light
  const desktopLight = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    colorScheme: "light",
  });
  const dl = await desktopLight.newPage();
  await dl.addInitScript(() => window.localStorage.setItem("perp-lab-theme", "light"));
  await shoot(dl, "10_overview_light_1280", `${BASE}/`);
  await desktopLight.close();

  // Mobile
  const mobile = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const m = await mobile.newPage();
  await shoot(m, "11_overview_mobile", `${BASE}/`, { fullPage: true });
  await mobile.close();

  await browser.close();
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
