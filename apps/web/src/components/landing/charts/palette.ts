// Chart colours for the public site.
//
// Literal values rather than resolved CSS variables: the landing palette lives
// on a wrapper element (`.landing`), not on <html>, so a runtime lookup against
// the document root would return the dashboard theme instead. These mirror the
// `.landing` block in globals.css and must be changed together.

export const LANDING_CHART = {
  grid: "rgb(33 42 56)",
  axis: "rgb(139 152 169)",
  accent: "rgb(45 212 191)",
  accentSoft: "rgb(45 212 191 / 0.14)",
  secondary: "rgb(56 189 248)",
  holdout: "rgb(251 191 36)",
  holdoutSoft: "rgb(251 191 36 / 0.07)",
  reference: "rgb(139 152 169)",
  surface: "rgb(19 24 33)",
  border: "rgb(33 42 56)",
} as const;

export const ASSET_COLOR: Record<string, string> = {
  BTCUSDT: "rgb(45 212 191)",
  ETHUSDT: "rgb(56 189 248)",
};
