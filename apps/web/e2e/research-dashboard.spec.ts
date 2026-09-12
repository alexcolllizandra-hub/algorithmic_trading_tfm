import { expect, test } from "@playwright/test";

const RUN_ID = "fixture_synthetic_momentum_e2e_run01";

test.beforeEach(async ({ page }) => {
  page.on("pageerror", (err) => console.log("PAGEERROR:", err.message));
});

test("1. la landing presenta la investigación", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("h1")).toContainText("Detección y validación de estrategias intradía");
  await expect(page.locator('a[href="/panel"]').first()).toBeVisible();
});

test("2-3. Datos y EDA muestra procedencia y particiones con hash", async ({ page }) => {
  await page.goto(`/datos-eda?run=${RUN_ID}`);
  await expect(page.locator("h1")).toContainText("Datos y análisis exploratorio");
  await expect(page.getByRole("heading", { name: /Procedencia y particiones/i })).toBeVisible();
  await expect(page.getByText(/Solo partición de desarrollo/).first()).toBeVisible();
});

test("4. abre un hallazgo EDA principal", async ({ page }) => {
  await page.goto("/datos-eda");
  await expect(
    page.getByRole("heading", { name: /Distribución de retornos horarios/i })
  ).toBeVisible();
  await expect(page.getByText(/Los hallazgos EDA orientan el diseño/i).first()).toBeVisible();
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

test("7-8. el laboratorio guía el flujo completo del estudio", async ({ page }) => {
  await page.goto("/laboratorio");
  await expect(
    page.getByText("El flujo completo, en el mismo orden que el estudio")
  ).toBeVisible();
  for (const step of ["Diseña", "Ejecuta", "Compara", "Optimiza", "Valida", "Veredicto"]) {
    await expect(page.getByRole("link", { name: new RegExp(step) }).first()).toBeVisible();
  }
  await expect(page.getByRole("button", { name: "Ejecutar backtest" })).toBeVisible();
  // Steps are screens: the optimiser only shows once its step is selected.
  await expect(page.getByText("Optimizador: búsqueda aleatoria")).toBeHidden();
  await page.getByRole("link", { name: /Optimiza/ }).first().click();
  await expect(page.getByText("Optimizador: búsqueda aleatoria")).toBeVisible();
  await expect(page.getByRole("button", { name: "Buscar" })).toBeVisible();
});

test("9. abre detalles técnicos en Diagnóstico", async ({ page }) => {
  await page.goto(`/diagnostico?run=${RUN_ID}`);
  await expect(page.locator("h1")).toContainText("Diagnóstico y trazabilidad");
  await expect(page.getByText(/artefacto/i).first()).toBeVisible();
});

test("10. theme toggle alterna la clase dark en html", async ({ page }) => {
  await page.addInitScript(() => window.localStorage.setItem("perp-lab-theme", "dark"));
  // The public landing ships its own committed look; the toggle lives on the
  // research pages' topbar.
  await page.goto("/resultados");

  const toggle = page.getByRole("button", { name: /Switch to (light|dark) theme/i });
  await expect(toggle).toBeVisible();
  const html = page.locator("html");
  await expect.poll(() => html.evaluate((el) => el.classList.contains("dark"))).toBe(true);

  await toggle.click();
  await expect.poll(() => html.evaluate((el) => el.classList.contains("dark"))).toBe(false);
});
