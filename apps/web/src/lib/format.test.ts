import { describe, expect, it } from "vitest";

import {
  fmtInt,
  fmtNumber,
  fmtPercent,
  fmtSignedPercent,
  fmtTimestamp,
  signClass,
} from "@/lib/format";

const DASH = "\u2014";

describe("format helpers", () => {
  it("formats numbers with fixed digits", () => {
    expect(fmtNumber(1.23456, 2)).toBe("1.23");
    expect(fmtNumber(1000, 0)).toBe("1,000");
  });

  it("returns an em dash for null / non-finite", () => {
    expect(fmtNumber(null)).toBe(DASH);
    expect(fmtNumber(Number.NaN)).toBe(DASH);
    expect(fmtInt(undefined)).toBe(DASH);
    expect(fmtPercent(Infinity)).toBe(DASH);
    expect(fmtTimestamp(null)).toBe(DASH);
  });

  it("formats percentages", () => {
    expect(fmtPercent(0.1234, 2)).toBe("12.34%");
    expect(fmtSignedPercent(0.05)).toBe("+5.00%");
    expect(fmtSignedPercent(-0.05)).toBe("-5.00%");
  });

  it("formats integers rounding", () => {
    expect(fmtInt(3.7)).toBe("4");
  });

  it("formats ISO timestamps", () => {
    expect(fmtTimestamp("2020-01-01T00:00:00+00:00")).toBe("2020-01-01 00:00:00Z");
  });

  it("chooses sign classes", () => {
    expect(signClass(1)).toBe("text-positive");
    expect(signClass(-1)).toBe("text-negative");
    expect(signClass(0)).toBe("text-fg");
    expect(signClass(null)).toBe("text-muted");
  });
});
