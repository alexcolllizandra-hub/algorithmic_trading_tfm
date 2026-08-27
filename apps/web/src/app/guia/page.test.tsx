import { render, screen, waitFor, within } from "@testing-library/react";
import { SWRConfig } from "swr";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import GuiaPage from "@/app/guia/page";
import { GUIDE_PANEL_IDS, panelCopy, panelParts } from "@/lib/guia";
import { I18nProvider } from "@/lib/i18n";
import { es } from "@/lib/i18n/es";
import { HOLDOUT_LEAK_PROBE, HOLDOUT_LEAK_SENTINELS, resolveFixture } from "@/mock/fixtures";

// The shell's Sidebar highlights the active entry via usePathname(), which
// returns null outside a Next router. Mocking the hook keeps the fix in the
// test, where the gap is, rather than making production code defend against a
// situation that cannot happen in the app.
vi.mock("next/navigation", async () => {
  const actual = await vi.importActual<typeof import("next/navigation")>("next/navigation");
  return { ...actual, usePathname: () => "/guia" };
});

// The guide is served the synthetic fixtures, except for the holdout: that one
// gets the leak probe, a locked payload that carries a full reading. The page
// must render the locked state and none of the numbers.
function stubApi() {
  vi.stubGlobal("fetch", async (input: RequestInfo | URL) => {
    // The API base is whatever NEXT_PUBLIC_API_BASE says: it can be absolute
    // (http://localhost:8000/api/v1) or relative (/mock-api/v1), so resolve
    // against an origin and keep only what follows the version prefix.
    const url = new URL(String(input), "http://localhost");
    const path = url.pathname.replace(/^.*\/v1/, "");
    const data =
      path === "/study/holdout" ? HOLDOUT_LEAK_PROBE : resolveFixture(path, url.searchParams);
    const status = data == null ? 404 : 200;
    return new Response(JSON.stringify(data ?? { detail: `no fixture for ${path}` }), {
      status,
      headers: { "content-type": "application/json" },
    });
  });
}

function renderGuide() {
  // These assertions are written against the Spanish copy, so the locale is
  // pinned: jsdom reports navigator.language as en-US, which would otherwise
  // render the page in English underneath them.
  return render(
    <SWRConfig value={{ provider: () => new Map(), dedupingInterval: 0 }}>
      <I18nProvider forceLocale="es">
        <GuiaPage />
      </I18nProvider>
    </SWRConfig>
  );
}

beforeEach(() => {
  // recharts measures its container; jsdom has no ResizeObserver.
  vi.stubGlobal(
    "ResizeObserver",
    class {
      observe() {}
      unobserve() {}
      disconnect() {}
    }
  );
  stubApi();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("/guia", () => {
  it("renders the thirteen panels in order", async () => {
    renderGuide();
    await waitFor(() =>
      expect(screen.getByRole("heading", { name: es.study.table.title })).toBeInTheDocument()
    );

    const sections = Array.from(document.querySelectorAll("[data-guide-panel]"));
    expect(sections).toHaveLength(13);
    expect(sections.map((s) => s.getAttribute("data-guide-panel"))).toEqual([...GUIDE_PANEL_IDS]);

    for (const id of GUIDE_PANEL_IDS) {
      expect(
        screen.getByRole("heading", { level: 2, name: panelCopy(id, es).title })
      ).toBeInTheDocument();
    }
  });

  // This is the requirement most likely to be broken silently later: a panel
  // added or edited without its four labelled parts.
  it("gives every one of the thirteen panels the four labelled parts", async () => {
    renderGuide();
    await waitFor(() =>
      expect(screen.getByRole("heading", { name: es.study.table.title })).toBeInTheDocument()
    );

    for (const id of GUIDE_PANEL_IDS) {
      const section = document.querySelector<HTMLElement>(`[data-guide-panel="${id}"]`);
      expect(section, `panel ${id} is missing`).not.toBeNull();
      const scope = within(section as HTMLElement);

      expect((section as HTMLElement).querySelectorAll("[data-guide-part]")).toHaveLength(4);
      for (const part of panelParts(id, es)) {
        expect(scope.getByText(part.label)).toBeInTheDocument();
        expect(scope.getByText(part.text)).toBeInTheDocument();
      }
    }
  });

  it("shows no holdout metric even though the API sends a full reading", async () => {
    renderGuide();
    await waitFor(() =>
      expect(screen.getByRole("heading", { name: es.study.holdout.title })).toBeInTheDocument()
    );
    // Either surface is acceptable: the panel heading or the status badge. Both
    // moved off the word "bloqueado" when the holdout language was unified.
    await waitFor(() =>
      expect(screen.getAllByText(/Holdout (abierto una vez|retenido)/).length).toBeGreaterThan(0)
    );

    const text = document.body.textContent ?? "";
    for (const sentinel of HOLDOUT_LEAK_SENTINELS) {
      expect(text, `holdout sentinel leaked: ${sentinel}`).not.toContain(sentinel);
    }

    // Inside the locked card there is no metric at all: no table and no figure
    // that could be read as a return, a Sharpe or a drawdown.
    const card = screen
      .getByRole("heading", { name: es.study.holdout.title })
      .closest("div.rounded-card") as HTMLElement;
    expect(card).not.toBeNull();
    expect(within(card).queryAllByRole("table")).toHaveLength(0);
    expect(card.textContent ?? "").not.toMatch(/[-+]?\d+[.,]\d+\s?%/);

    // The reserved window and the reason are state, not a reading, and the
    // deliberate absence of metrics is stated on screen.
    expect(screen.getByText(es.study.holdout.period)).toBeInTheDocument();
    expect(screen.getAllByText(es.study.holdout.deliberateAbsence).length).toBeGreaterThan(0);
    expect(screen.getByText(es.guia.labels.holdoutWithheld)).toBeInTheDocument();
  });

  it("labels every didactic drawing as an illustrative example", async () => {
    renderGuide();
    await waitFor(() =>
      expect(screen.getByRole("heading", { name: es.guia.concepts.title }).textContent).toBeTruthy()
    );

    const figures = Array.from(document.querySelectorAll("figure"));
    expect(figures.length).toBeGreaterThanOrEqual(14);
    for (const figure of figures) {
      expect(figure.textContent).toContain(es.guia.illustrative.badge);
      expect(figure.textContent).toContain(es.guia.illustrative.note);
    }
  });

  it("separates fine-tuning from hyperparameter optimisation on screen", async () => {
    renderGuide();
    expect(await screen.findByText(es.guia.concepts.fineTuningTitle)).toBeInTheDocument();
    expect(screen.getByText(es.guia.concepts.fineTuningBody2)).toBeInTheDocument();
    expect(
      screen.getByText(es.guia.concepts.items.fineTuning.term, { selector: "h3" })
    ).toBeInTheDocument();
    expect(
      screen.getByText(es.guia.concepts.items.hiper.term, { selector: "h3" })
    ).toBeInTheDocument();
  });

  it("offers a jump control for each panel through the sticky index", async () => {
    renderGuide();
    const nav = await screen.findByRole("navigation", { name: es.guia.toc.navLabel });
    const buttons = within(nav).getAllByRole("button");
    expect(buttons).toHaveLength(13);
    expect(buttons[0]).toHaveAttribute(
      "aria-label",
      es.guia.toc.jump.replace("{n}", "1").replace("{title}", panelCopy("pregunta", es).title)
    );
    expect(within(nav).getByRole("progressbar")).toHaveAttribute("aria-valuenow", "8");
  });

  it("reports a status instead of a number when the study payload is missing", async () => {
    vi.stubGlobal(
      "fetch",
      async () =>
        new Response(JSON.stringify({ detail: "artifact missing" }), {
          status: 503,
          headers: { "content-type": "application/json" },
        })
    );
    renderGuide();
    // Every panel that would have shown a study figure reports the outage instead.
    expect((await screen.findAllByText(es.study.unavailable.title)).length).toBeGreaterThan(0);

    // The didactic panels stay readable: the guide degrades to states, not zeros.
    expect(document.querySelectorAll("[data-guide-panel]")).toHaveLength(13);
    expect(document.querySelectorAll("[data-guide-part]")).toHaveLength(52);
  });
});
