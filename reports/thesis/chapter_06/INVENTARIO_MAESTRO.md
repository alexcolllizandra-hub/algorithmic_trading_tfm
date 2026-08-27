# Inventario maestro de familias, rondas y experimentos (verificado contra artefactos)

Compilado a mano desde los artefactos citados; cada recuento de evaluaciones
está sumado directamente de los `*_candidates.parquet` de los run_dirs de cada
estudio (no de los README). Protocolo común salvo indicación: walk-forward
expansivo 15 pliegues (purga 96 / embargo 118), 1h, costes 4+1 pb/lado +
funding realizado, RS confirmatorio con paridad de presupuesto frente al GA.
CSV gemelo: `INVENTARIO_MAESTRO.csv`.

## Universo confirmatorio

| Familia (ronda) | Estado | Activos × semillas × folds | Presupuesto/fold/motor | Evals únicas | Artefactos | ¿En el cierre de 13? |
|---|---|---|---|---|---|---|
| momentum (R2 rebaseline) | confirmatoria, cerrada | 2 × 10 × 15 | 300 | 180.000 | `multiseed_momentum_r2_clean_v2/` (+`study_robustness.json`) | SÍ |
| breakout (R3) | confirmatoria, cerrada | 2 × 10 × 15 | 100 | 60.000 | `r3_full_budget100_ga21/breakout/` | SÍ |
| mean_reversion (R3) | ídem | ídem | 100 | 60.000 | ídem | SÍ |
| volatility_breakout (R3) | ídem (señal parcial: 6/10 semillas BTC) | ídem | 100 | 60.000 | ídem | SÍ |
| funding (R3) | ídem | ídem | 100 | 60.000 | ídem | SÍ |
| BTC_ETH_confirmation (R3) | ídem | ídem | 100 | 60.000 | ídem | SÍ |
| mtf_trend_consensus (S1-B) | **solo piloto** | **BTC × 1 × 15** | **25** | 750 | run `s1b_pilot_*` + `gate_s1b/s1b_pilot_report.json` | SÍ (nivel piloto) |
| funding_reversal (S1-B) | solo piloto (señal parcial, p crudo 0,060) | BTC × 1 × 15 | 25 | 750 | ídem | SÍ (nivel piloto) |
| intraday_seasonality (S1-B) | solo piloto | BTC × 1 × 15 | 25 | 750 | ídem | SÍ (nivel piloto) |
| xasset_spread_reversion (S1-B) | solo piloto | BTC × 1 × 15 | 25 | 750 | ídem | SÍ (nivel piloto) |
| taker_flow_extreme (S2-B) | solo piloto | 2 × 3 × 15 | 25 | 4.500 | runs `s2b_pilot_*` + `gate_s2b/` | SÍ (nivel piloto) |
| illiquidity_reversion (S2-B) | solo piloto | 2 × 3 × 15 | 25 | 4.500 | ídem | SÍ (nivel piloto) |
| flow_price_divergence (S2-B) | solo piloto | 2 × 3 × 15 | 25 | 4.500 | ídem | SÍ (nivel piloto) |
| **Subtotal cierre de 13** | | **284 unidades (fam×activo×semilla×motor)** | | **496.500** ✓ verificado | `study_closure/` (2026-08-13, commit 232bc372) | — |
| CRT_INTRADAY_V1 — 9 familias: pdl_reclaim_long, pdh_reclaim_short, crt_htf_range_reversal, session_liquidity_sweep, session_range_rotation, opening_range_breakout_retest, failed_breakout_reversal, double_sweep_reversal, crt_three_candle_model (nombres del `frozen_order` de `crt_v1_execution.json`) | confirmatoria, cerrada (0/18 celdas) | 2 × 10 × 15 cada una | 100 | 540.000 (9×60.000, verificado por parquets) | `crt_v1_budget100/<fam>/study_robustness.json` + `crt_v1_execution.json` | **NO — posterior al cierre; sin Holm/BH/DSR/PBO ampliados (no calculado)** |
| macro_event_brake (S3) | confirmatoria, cerrada (0/10 semillas) | 2 × 10 × 15 | 100 | 60.000 (verificado por parquets; piloto de 750 aparte, abajo) | `multiseed_20260826T165028Z_0d3a92/` + ADR 0019 + `docs/thesis/resultados_s3.md`* | **NO — posterior; N:=N+1 declarado; corrección ampliada no calculada** |

\* `docs/thesis/` no viaja al repo público de entrega; el veredicto S3 vive también en los artefactos del estudio.

## Ejecuciones exploratorias y descartadas (no confirmatorias, nunca en el cierre)

| Bloque | Estado | Runs / evals | Motivo de exclusión | Artefactos |
|---|---|---|---|---|
| Smoke (fase A) | exploratoria técnica | 21 / 621 | validez técnica sintética, sin lectura de rentabilidad | runs `smoke_*` |
| Desarrollo (slice vertical, momentum) | exploratoria | 29 / 9.244 | anterior al contrato congelado | runs `development_*` |
| Pilotos R2/R3 (6 familias) | exploratoria (no-futilidad) | 19 / 20.760 | el protocolo prohíbe citar Sharpe de piloto como evidencia | runs `pilot_*` |
| CRT v1 abortado | **descartada** | 31 / 93.000 (verificado: 24.000 en `crt_v1_ABORTED_fc662f9` + 9.000 + 60.000 en `_DESCARTADO_huella_arbol_sucio`) | huella de identidad sobre árbol sucio → invalidada y re-ejecutada limpia | `crt_v1_ABORTED_fc662f9/`, `_DESCARTADO_huella_arbol_sucio/` |
| Piloto S3 | exploratoria (screen técnico) | 1 / 750 | mismo trato que los pilotos R2/R3: superado por el estudio completo | `search_macro_event_brake_20260826T164228Z_d02e91` |
| S1-C configs (4 familias, estudio completo) | **implementada, NO ejecutada** | 0 | decisión humana pendiente («NOT YET EXECUTED» en las configs) | `configs/search_s1c_*.yaml` |
| Checkpoint S3 abandonado | descartada | 7 / 18.000 (6×3.000 + 1 parcial) | huella distinta tras cambios de código; relanzado limpio | `multiseed_20260826T164332Z_4c7762/` |
| momentum baseline R1 | **sustituida** | (runs pre-R2) | contaminación de pliegue externo detectada → ADR 0011/0012/0013 | `multiseed_momentum_baseline/`, ADRs |

## Capas no-familia (otros capítulos)

| Bloque | Estado | Alcance | Artefactos | Capítulo |
|---|---|---|---|---|
| Meta-labeling sintético | ejecutado (validación de maquinaria, edge plantado) | mercados sintéticos | `reports/meta_labeling_synthetic/` + ADR 0017 | 9 |
| Meta-labeling real | ejecutado | primaria momentum BTC 1h, 15 folds, 3 modelos preregistrados/fold, triple barrera 2 ATR/24 barras con costes del estudio | `reports/meta_labeling_real/` + `reports/tables/ml/` | 9 |
| Vol-forecast (HAR vs LSTM) | ejecutado, regla congelada → «no material improvement» | 2 activos, 15 folds, semillas {42,43,44} | `artifacts/volforecast/results.json` + spec congelada | anexo/11 |
| Alt-data (F&G + macro events) | ejecutado, descriptivo | desarrollo | `reports/figures/thesis_altdata`\*/eda + manifiestos | 5/11 |
| Monte Carlo / cuenta fondeada | ejecutado | mejor familia del cierre | `reports/tables|figures/montecarlo/` | 8 |

## Alcance exacto de cada diagnóstico del capítulo 6

| Diagnóstico | Universo que cubre | CRT | S3 |
|---|---|---|---|
| Holm / BH (t04) | los 13 p-valores de familia del cierre | **no calculado** | no calculado |
| Sensibilidad del conteo (t05: 13/22/142/496.500) | ídem | no incluido en los conteos | no incluido |
| DSR (t06) | mejor familia del cierre (volatility_breakout) | no calculado | no calculado |
| PBO/CSCV (0,486) | matriz 13 × 32.385 del cierre | no calculado | no calculado |
| White RC / Hansen SPA | batches S1-B (4 candidatos) y S2-B | no calculado | no calculado |
| C1–C6 por celda (bootstrap incluido) | **todas** las rondas confirmatorias: R2, R3, S1-B, S2-B, **CRT v1**, **S3** | ✔ calculado | ✔ calculado |

**Sobre un análisis global ampliado (si se quisiera):** el universo correcto
sería 13 + 9 + 1 = 23 hipótesis de familia (N de Holm/BH), con la advertencia
de que la evidencia por familia es heterogénea (10 semillas en R2/R3/CRT/S3;
1–3 en S1/S2) y los presupuestos difieren (25–300/fold), de modo que los
p-valores no provienen de diseños intercambiables; y el denominador del DSR
pasaría de 496.500 a **496.500 + 540.000 (CRT válido) + 60.000 (S3) =
1.096.500** configuraciones confirmatorias válidas (1.097.250 si se contara
también el piloto S3 de 750, que este inventario excluye por el mismo motivo
que los pilotos R2/R3: quedó superado por el estudio completo). Cada sumando
está verificado sumando los `*_candidates.parquet` de los run-dirs. No se ha
ejecutado; requeriría reconstruir la matriz OOS con las 23 series
concatenadas y re-correr las cuatro correcciones.
