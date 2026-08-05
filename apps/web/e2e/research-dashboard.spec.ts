import { expect, test } from "@playwright/test";

const RUN_ID = "fixture_synthetic_momentum_e2e_run01";

test.beforeEach(async ({ page }) => {
  page.on("pageerror", (err) => console.log("PAGEERROR:", err.message));
});

test("1. abre la visión general de investigación", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("h1")).toContainText("Visión general de la investigación");
  await expect(page.getByText(/Resultados exploratorios/i).first()).toBeVisible();
});

test("2-3. selecciona piloto y revisa timeline en Datos y EDA", async ({ page }) => {
  await page.goto(`/datos-eda?run=${RUN_ID}`);
  await expect(page.locator("h1")).toContainText("Datos y análisis exploratorio");
  await expect(page.getByRole("heading", { name: "Línea temporal del experimento" })).toBeVisible();
});

test("4. abre un hallazgo EDA principal", async ({ page }) => {
  await page.goto("/datos-eda");
  await expect(page.getByRole("heading", { name: "Hallazgos clave" })).toBeVisible();
  await expect(page.getByText(/Forma de la distribución de retornos/i).first()).toBeVisible();
});

test("5. navega a Metodología", async ({ page }) => {
  await page.goto("/metodologia");
  await expect(page.locator("h1")).toContainText("Metodología experimental");
  await expect(page.getByText(/walk-forward/i).first()).toBeVisible();
});

test("6. compara Random Search y GA en Experimentos", async ({ page }) => {
  await page.goto(`/experimentos?run=${RUN_ID}&tab=fairness`);
  await expect(page.getByText("RS evaluados").first()).toBeVisible();
  await expect(page.getByText("GA evaluados").first()).toBeVisible();
  await expect(page.getByText(/Evaluaciones efectivas RS vs GA/i)).toBeVisible();
});

test("7-8. selecciona fold y verifica coherencia en Resultados", async ({ page }) => {
  await page.goto(`/resultados?run=${RUN_ID}&method=genetic_algorithm&fold=0`);
  await expect(page.getByText("Periodo test").first()).toBeVisible();
  await expect(page.getByText("1.0400").first()).toBeVisible();
  await expect(page.getByText("Operaciones").first()).toBeVisible();
});

test("9. abre detalles técnicos en Diagnóstico", async ({ page }) => {
  await page.goto(`/diagnostico?run=${RUN_ID}`);
  await expect(page.locator("h1")).toContainText("Diagnóstico y trazabilidad");
  await expect(page.getByText(/artefacto/i).first()).toBeVisible();
});

test("10. theme toggle alterna la clase dark en html", async ({ page }) => {
  await page.addInitScript(() => window.localStorage.setItem("perp-lab-theme", "dark"));
  await page.goto("/");

  const toggle = page.getByRole("button", { name: /Switch to (light|dark) theme/i });
  await expect(toggle).toBeVisible();
  const html = page.locator("html");
  await expect.poll(() => html.evaluate((el) => el.classList.contains("dark"))).toBe(true);

  await toggle.click();
  await expect.poll(() => html.evaluate((el) => el.classList.contains("dark"))).toBe(false);
});
