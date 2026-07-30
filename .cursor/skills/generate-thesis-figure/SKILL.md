---
name: generate-thesis-figure
description: Produce a consistent, publication-ready figure for the thesis and save it under reports/figures with a caption. Use when creating or updating a figure for the EDA or results chapters of the perp-lab thesis.
disable-model-invocation: true
---

# Generate thesis figure

## Workflow

1. Build the figure with a `perp_lab.eda.plots` helper (or add one there if the
   chart type is new and reusable).
2. Save with `save_figure(fig, "reports/figures/<chapter>_<slug>.png")`.
3. Record a caption and the exact source (function, parameters, dataset id +
   manifest hash) so the figure is reproducible.

## Conventions

- Numbering: correlative across the thesis (Figure 1, Figure 2, ...).
- Axes: time axis labeled "Time (UTC)"; state units explicitly.
- One idea per figure; prefer clarity over decoration.
- Regenerate from code; never hand-edit an exported image.
- Figures come from the development partition unless the figure is explicitly a
  final-holdout result in the results chapter.
