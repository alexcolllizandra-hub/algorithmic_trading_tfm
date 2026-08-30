# Platform screenshots

Captures of the local web platform reading the real study artefacts. No sample
or placeholder data: every number on screen comes from the exported payloads
under `apps/web/public/data/`.

- Commit: `0920e423d63e188744296b29e80089f9ee836747` (`main`, tag `v1.1-tfm`),
  plus the copy and `/experimentos` fixes described below, which belong to the
  same commit as this manifest
- Date captured: 2026-08-30
- Backend: FastAPI on `http://localhost:8000`; frontend: Next.js dev server on
  `http://localhost:3000`

| File | URL captured | Region |
|---|---|---|
| `fig_4_13a_web_cierre_estudio.png` | `/resultados` | "Resultado del estudio" and the table "Todos los backtests del estudio" |
| `fig_4_13b_web_correccion_multiple.png` | `/resultados` | "Corrección por comparaciones múltiples", from the closure conclusion to "Criterio aplicado en cada ronda" |
| `fig_4_14_web_explorador_pdl.png` | `/estrategias` | `pdl_reclaim_long` on BTCUSDT: header, "Equity fuera de muestra", "Métricas completas" |
| `fig_4_15_web_explorador_montecarlo.png` | `/estrategias` | Same family: "Configuración ganadora por pliegue" and "Monte Carlo, dispersión bajo remuestreo" |
| `fig_4_16a_web_lab_bateria.png` | `/laboratorio` | "Batería de contraste (out-of-sample)", seven checks, result 0/7 |
| `fig_4_16b_web_lab_equity_senales.png` | `/laboratorio` | "Curva de equity" with its drawdown panel, and "Precio y señales" |
| `fig_4_16c_web_lab_fases_maefe.png` | `/laboratorio` | "Métricas por fase" (21 metrics x 4 columns) and "Excursión máxima por operación (MAE / MFE)" |
| `fig_4_16d_web_lab_tornado_regimen.png` | `/laboratorio` | "Sensibilidad de parámetros (tornado)", "Métricas por régimen de volatilidad", "Sus intentos de esta sesión" |
| `fig_4_17_web_experimentos_presupuesto.png` | `/experimentos` | "Comparación de métodos" (full seven-column table), "Sharpe OOS agregado" bar chart, and "Verificación presupuesto equitativo": 375 unique evaluations per method, verdict COINCIDE |

## Laboratory run reproduced in figure 4.16

Family `momentum` on BTCUSDT, default parameters `fast = 24`, `slow = 168`,
`direction = both`, no stop, take-profit, trailing or time exit, all three
volatility regimes allowed, costs 4 bps fee and 1 bps slippage per side, and an
in-sample / out-of-sample split at 70%. The laboratory dataset is 52,608 hourly
bars from 2020-01-01 to 2025-12-31: `scripts/export_lab_data.py` filters at
`HOLDOUT_START = 2026-01-01`, so the reserved partition is excluded by
construction and cannot reach any of these panels.

## Capture settings

Chromium through Playwright, viewport 1600 x 1200 CSS pixels, device scale
factor 2, locale `es-ES`, colour scheme light, theme toggled to light through
the interface control. Each file is an unedited clip of the rendered page taken
with the document scrolled to the top so the sticky header stays outside the
frame: x offset 256, width 1344 CSS pixels, vertical extent from the bounding
boxes of the named cards plus 24 pixels of margin. No browser chrome, no cursor,
no page header and no footer are inside any clip. The capture script was ad hoc
and is not retained in the repository; the settings above are the whole of it.

## Copy fix applied before capturing

The laboratory battery subtitle read "Cuatro comprobaciones" and its disclaimer
read "Un 4/4 aquí" while the battery runs seven checks and the heading renders
"0/7". Stale copy from when the battery had four checks. Corrected to "Siete" and
"7/7" in `es.ts`, and to "Seven" and "7/7" in `en.ts`, so figure 4.16a does not
contradict itself.

## What is visible, and what is not

Figures 4.13a and 4.13b show 13 families, 496,500 configurations evaluated, 0
survivors after correction, PBO 0.486, lowest raw p-value 0.3455, zero
rejections under both Holm-Bonferroni and Benjamini-Hochberg, and all 22
family-by-asset rows marked "Rechazado". The funded always-long perpetual
benchmark in figure 4.14 reads +52.3% over the out-of-sample window.

No figure from the reserved partition appears anywhere. The only reference to it
inside a clip is the badge on `pdl_reclaim_long` in figure 4.14, which states
that the family was evaluated after closure and is not promotable because the
partition was consumed. It carries no metric. No name, email address, session
control or token is inside any clip.

## Defects found on `/experimentos`, fixed before this capture

Three problems were found while framing figure 4.17 and corrected in the same
commit this manifest belongs to. The card "Comparación de métodos" sat in a
half-width grid cell, so its rightmost columns clipped behind an unsignalled
horizontal scroll; the two cards now stack at full width. The chart "Sharpe OOS
agregado" rendered empty because recharts' automatic domain on an all-negative
series excludes zero while bars grow from zero; the domain is now forced to
contain zero, with a reference line at it. Both card subtitles came from
English artefact strings; they now come from the bilingual dictionary. The
figure shows the corrected page.
