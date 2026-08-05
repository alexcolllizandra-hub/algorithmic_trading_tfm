import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { RunKindBadge } from "@/components/ui/Badge";

describe("RunKindBadge", () => {
  it("labels synthetic-smoke runs so they cannot be mistaken for research", () => {
    render(<RunKindBadge kind="synthetic-smoke" />);
    expect(screen.getByText("SYNTHETIC SMOKE")).toBeInTheDocument();
  });

  it("labels development runs", () => {
    render(<RunKindBadge kind="development" />);
    expect(screen.getByText("DEVELOPMENT DATA")).toBeInTheDocument();
  });

  it("labels final holdout runs", () => {
    render(<RunKindBadge kind="final-holdout" />);
    expect(screen.getByText("FINAL HOLDOUT")).toBeInTheDocument();
  });

  it("falls back to unknown", () => {
    render(<RunKindBadge kind="unknown" />);
    expect(screen.getByText("UNKNOWN")).toBeInTheDocument();
  });
});
