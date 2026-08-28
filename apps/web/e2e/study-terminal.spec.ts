import { expect, test } from "@playwright/test";

// Runs against the synthetic study fixtures served by /mock-api/v1.
test.beforeEach(async ({ page }) => {
  page.on("pageerror", (err) => console.log("PAGEERROR:", err.message));
  await page.goto("/estudio");
});

test("1. la cabecera resume el estudio con cifras de la API", async ({ page }) => {
  await expect(page.locator("h1")).toContainText("Resultados y cierre del estudio");
  await expect(page.getByText("Familias probadas").first()).toBeVisible();
  await expect(page.getByText("Configuraciones evaluadas").first()).toBeVisible();
  await expect(page.getByText("12,345").first()).toBeVisible();
  await expect(page.getByText("Supervivientes tras corrección").first()).toBeVisible();
});

test("2. la tabla maestra filtra por activo", async ({ page }) => {
  await expect(
    page.getByRole("heading", { name: "Todos los backtests del estudio" })
  ).toBeVisible();
  await expect(page.getByText("4 de 4 filas").first()).toBeVisible();
  await page.getByLabel("Activo", { exact: true }).selectOption("ETHUSDT");
  await expect(page.getByText("1 de 4 filas").first()).toBeVisible();
});

test("3. el detalle muestra la hipótesis, las semillas y el abanico", async ({ page }) => {
  await page.getByRole("button", { name: "ver" }).first().click();

  await expect(page.getByText(/hipótesis de ejemplo para volatility_breakout/i)).toBeVisible();
  await expect(page.getByText("Media de las semillas").first()).toBeVisible();
  await expect(page.getByText("Semillas individuales (3)")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Abanico de remuestreo" })).toBeVisible();
  await expect(page.getByText(/RIESGO DE TRAYECTORIA, no significancia/).first()).toBeVisible();
  await expect(page.getByText("path_risk_not_significance")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Criterios de promoción" })).toBeVisible();
  await expect(page.getByText("C1 positive return")).toBeVisible();
  await expect(page.getByText("Veto: mínimo de operaciones fuera de muestra")).toBeVisible();
});

test("4. el panel de comparaciones múltiples cita la conclusión y el PBO", async ({ page }) => {
  await expect(
    page.getByRole("heading", { name: "Corrección por comparaciones múltiples" })
  ).toBeVisible();
  await expect(page.getByText(/Ninguna familia de este fixture sobrevive/)).toBeVisible();
  await expect(page.getByText("0.472").first()).toBeVisible();
  await expect(page.getByText("Línea de ruido: 0,5")).toBeVisible();
});

test("5. el panel de regímenes es exploratorio", async ({ page }) => {
  await expect(
    page.getByRole("heading", { name: "Análisis por régimen de mercado" })
  ).toBeVisible();
  await expect(page.getByText(/Bloque EXPLORATORIO/)).toBeVisible();
});

test("6. el holdout aparece bloqueado y sin métricas", async ({ page }) => {
  const card = page.getByRole("heading", { name: "Holdout final" }).locator("../../..");
  await expect(
    card.getByText("Holdout abierto una vez: resultado no auditado").first()
  ).toBeVisible();
  await expect(card.getByText("Ventana reservada", { exact: true })).toBeVisible();
  await expect(card.getByText("Motivo del aislamiento", { exact: true })).toBeVisible();
  await expect(card.getByText(/Auditoría independiente del pipeline/)).toBeVisible();
  await expect(card.getByText(/La ausencia de métricas es deliberada/)).toBeVisible();

  // No holdout reading may leak into the UI: no metric table and no percentages.
  await expect(card.getByRole("table")).toHaveCount(0);
  expect(await card.innerText()).not.toMatch(/[-+]?\d+[.,]\d+\s?%/);
});
