import { expect, test } from "@playwright/test";

// Runs against the synthetic study fixtures served by /mock-api/v1.
const PANEL_IDS = [
  "pregunta",
  "datos",
  "estrategia",
  "backtest",
  "particiones",
  "walkForward",
  "purgeEmbargo",
  "semillasFolds",
  "costes",
  "estrategiasProbadas",
  "resultados",
  "rechazo",
  "conclusion",
];

const PANEL_TITLES = [
  "¿Qué pregunta intenta responder esto?",
  "¿Qué datos usa?",
  "¿Qué es una estrategia?",
  "¿Qué es un backtest?",
  "¿Qué son train, validación y fuera de muestra?",
  "¿Qué es la validación walk-forward?",
  "¿Qué son el purge y el embargo?",
  "¿Qué son las semillas y los folds?",
  "¿Qué costes se aplican?",
  "¿Qué estrategias se probaron?",
  "¿Qué resultados se obtuvieron?",
  "¿Por qué una estrategia que parece rentable puede rechazarse?",
  "¿A qué conclusión científica se llega?",
];

const PART_LABELS = [
  "Qué estoy viendo",
  "Por qué importa",
  "Cómo se interpreta",
  "Conclusión obtenida",
];

test.beforeEach(async ({ page }) => {
  page.on("pageerror", (err) => console.log("PAGEERROR:", err.message));
  await page.goto("/guia");
});

test("1. la guía carga y se alcanza desde la navegación", async ({ page }) => {
  await expect(page.locator("h1")).toContainText("Guía del estudio, paso a paso");
  await expect(page.getByRole("link", { name: "Guía" }).first()).toBeVisible();
  await expect(page.getByRole("navigation", { name: /Índice de los 13 paneles/ })).toBeVisible();
});

test("2. los trece paneles están presentes y en orden", async ({ page }) => {
  const panels = page.locator("[data-guide-panel]");
  await expect(panels).toHaveCount(13);

  // Panels reuse study components that bring their own h2, so the panel heading
  // is addressed by the id the section points at with aria-labelledby.
  for (const [i, title] of PANEL_TITLES.entries()) {
    await expect(panels.nth(i)).toHaveAttribute("data-guide-panel", PANEL_IDS[i]);
    await expect(page.locator(`h2#panel-${PANEL_IDS[i]}-title`)).toHaveText(title);
  }
});

test("3. cada panel lleva las cuatro partes etiquetadas", async ({ page }) => {
  const panels = page.locator("[data-guide-panel]");
  await expect(panels).toHaveCount(13);

  for (let i = 0; i < 13; i += 1) {
    const panel = panels.nth(i);
    await expect(panel.locator("[data-guide-part]")).toHaveCount(4);
    for (const label of PART_LABELS) {
      await expect(panel.getByText(label, { exact: true })).toBeVisible();
    }
  }
});

test("4. el índice navega entre paneles", async ({ page }) => {
  const nav = page.getByRole("navigation", { name: /Índice de los 13 paneles/ });
  await expect(nav.getByRole("button")).toHaveCount(13);
  await expect(nav.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "8");

  await nav.getByRole("button", { name: /^Ir al panel 9:/ }).click();
  const costes = page.locator('[data-guide-panel="costes"]');
  await expect(costes).toBeFocused();
  await expect(page.locator("h2#panel-costes-title")).toBeInViewport();

  // The index keeps working with the keyboard alone.
  await nav.getByRole("button", { name: /^Ir al panel 13:/ }).focus();
  await page.keyboard.press("Enter");
  const conclusion = page.locator('[data-guide-panel="conclusion"]');
  await expect(conclusion).toBeFocused();
  await expect(page.locator("h2#panel-conclusion-title")).toBeInViewport();
});

test("5. todo dibujo didáctico se etiqueta como ejemplo ilustrativo", async ({ page }) => {
  const figures = page.locator("figure");
  const count = await figures.count();
  expect(count).toBeGreaterThanOrEqual(14);

  for (let i = 0; i < count; i += 1) {
    const figure = figures.nth(i);
    await expect(figure.getByText("ejemplo ilustrativo")).toHaveCount(1);
    await expect(figure).toContainText("Dibujo didáctico con valores inventados");
  }
});

test("6. la aclaración de fine-tuning aparece en pantalla", async ({ page }) => {
  await expect(
    page.getByText("Aclaración necesaria: fine-tuning no es optimización de hiperparámetros")
  ).toBeVisible();
  await expect(
    page.getByText(/NO es fine-tuning: es optimización de hiperparámetros/).first()
  ).toBeVisible();
  await expect(page.getByRole("heading", { name: "Fine-tuning (reajuste fino)" })).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Optimización de hiperparámetros", exact: true })
  ).toBeVisible();
});

test("7. el panel 13 no publica ninguna métrica del holdout", async ({ page }) => {
  const panel = page.locator('[data-guide-panel="conclusion"]');
  await expect(panel.getByRole("heading", { name: "Holdout final" })).toBeVisible();
  await expect(panel.getByText("Holdout bloqueado").first()).toBeVisible();
  await expect(panel.getByText(/La lectura del holdout queda retenida/)).toBeVisible();
  await expect(panel.getByText(/La ausencia de métricas es deliberada/).first()).toBeVisible();

  // No reading may leak: the locked card carries no metric table.
  const card = panel.getByRole("heading", { name: "Holdout final" }).locator("../../..");
  await expect(card.getByRole("table")).toHaveCount(0);
  expect(await card.innerText()).not.toMatch(/[-+]?\d+[.,]\d+\s?%/);
});

// The app shell reserves a fixed 256px sidebar and the page adds 24px of padding
// per side, so a 360px reading column is a 664px viewport. Every wide element of
// the guide must scroll inside its own container, never widen the page.
test("8. con una columna de lectura de 360px no hay desbordamiento horizontal", async ({
  page,
}) => {
  await page.setViewportSize({ width: 664, height: 900 });
  await expect(page.locator("[data-guide-panel]")).toHaveCount(13);
  await page.locator('[data-guide-panel="resultados"]').scrollIntoViewIfNeeded();
  await page.locator('[data-guide-panel="conclusion"]').scrollIntoViewIfNeeded();

  const overflow = await page.evaluate(() => {
    const main = document.querySelector("main") as HTMLElement;
    const panels = Array.from(document.querySelectorAll<HTMLElement>("[data-guide-panel]"));
    return {
      readingColumn: main.clientWidth - 48,
      main: main.scrollWidth - main.clientWidth,
      worstPanel: Math.max(...panels.map((p) => p.scrollWidth - p.clientWidth)),
    };
  });

  expect(overflow.readingColumn).toBe(360);
  expect(overflow.main).toBeLessThanOrEqual(1);
  expect(overflow.worstPanel).toBeLessThanOrEqual(1);
});
