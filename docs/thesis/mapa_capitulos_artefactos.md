# Mapa capítulos ↔ artefactos

Fecha: 2026-08-19. `SUPUESTO:` entrega ~15-09-2026. Objetivo total ~22.000
palabras. Estados: **escribible ya** / **falta ejecutar** / **falta decidir**.

## Tabla maestra

| Cap | Sección | Estado | Artefactos que lo sostienen | Figuras/tablas disponibles | Qué falta exactamente |
|---|---|---|---|---|---|
| 1 | Introducción y motivación | **escribible ya** | textos ES de la landing (`apps/web/src/components/landing/Hero.tsx`, `PlainExplanation.tsx`, `Overfitting.tsx`) | — | Redacción (ensamblar, ~2.000 palabras). Sin dependencias |
| 2 | Estado del arte | **falta decidir** | 8 referencias citadas en el repo (`evaluation/multiple_testing.py` docstring; ADRs) | — | El único hueco real: hay que escribir ~3.500 palabras y ampliar bibliografía. Cont NO está citado en el repo: no usarlo sin añadir la referencia primero |
| 3 | Objetivos y preguntas | **escribible ya** | `docs/methodology/experimental_design.md` §1-2 (RQ1-5, H1-5) [TRADUCIR] | — | Traducir y adaptar (~1.200) |
| 4 | Diseño experimental | **escribible ya** — borrador en `borradores/04_diseno_experimental.md` | `configs/experiment.yaml`, `configs/data_contract.yaml`, `docs/experimental_protocol.md` [TRADUCIR], ADR 0003/0005 | `backtest/h05_walk_forward_geometry.png`, tablas `backtest/t05`, `t06` | Revisar borrador, insertar figuras |
| 5 | Metodología | **escribible ya** — borrador en `borradores/05_metodologia.md` | `docs/methodology/pipeline_end_to_end.md` (nuevo), `validation_protocol.md`, `strategy_search.md`, `feature_catalogue.md`, `study_level_multiple_testing.md` [TRADUCIR], ADR 0008/0009/0012/0014 | `features/g01-g09`, `search/i01-i06`, diagramas Mermaid del pipeline | Revisar borrador; exportar los 2 Mermaid a imagen |
| 6 | Resultados | parcial (1.878 palabras en `capitulo_06_resultados.md`) + **falta ejecutar** (CRT V1 en curso, 5/9 a 19-08) | `reports/study_closure/*.json`, `reports/r3_gate/*/thesis_report.json`, `artifacts/runs/crt_v1_budget100/` | `closure/j01-j04`, tablas `closure/t01-t09` | Esperar cierre CRT V1; añadir subsección CRT + RQ3 real; ampliar a ~2.500 |
| 7 | Limitaciones e integridad | **escribible ya** — borrador en `borradores/07_limitaciones_y_amenazas.md` | `docs/methodology/holdout_audit_status.md`, `crt_intraday.md` §6bis, `docs/thesis/incidente_holdout.md` (nuevo) | `closure/j02` (sensibilidad del recuento) | Revisar borrador |
| 8 | Discusión | parcial (1.186 en `capitulo_07_discusion.md`, renumerar a 08) | cierre + PBO + DSR | `closure/j03` | Ampliar con RQ3 real y potencia estadística (Bloque D3) |
| 9 | Conclusiones | casi listo (1.051 en `capitulo_08_conclusiones.md`, renumerar a 09) | — | — | Retoque final |
| 10 | Trabajo futuro | **escribible ya** | `crt_intraday_v2_prereg.md` (ES), `docs/roadmap/master_roadmap.md` [TRADUCIR], rama `feat/external-validation-nasdaq`, `docs/roadmap/future_architecture.md` | — | Ensamblar (~1.300); todo lo CRT/ICT/sesiones/NASDAQ vive aquí, no en el cuerpo |
| — | Anexo Monte Carlo | **escribible ya** (ejecutado 19-08) | `artifacts/runs/r3_full_budget100_ga21/volatility_breakout/` + `reports/tables/montecarlo/` | `montecarlo/k01-k05` | Redactar el texto del anexo desde el cuaderno 07 |

## Inventario de figuras existentes (51, en `reports/figures/`)

**No versionadas** (`.gitignore:54`) — primer arreglo de custodia pendiente.

| Grupo | Ficheros | Sección destino |
|---|---|---|
| `eda/f01-f24, fa2` (25) | huecos 5m, cobertura mensual, precio/drawdown, calendario, colas, boxplots, extremos, volatilidad, momentos rodantes, autocorrelación, liquidez, volumen, estacionalidad, order flow, basis, funding, cross-asset, temporalidades, regímenes (×5), eventos, bootstrap ICs, dependencia de colas | Cap 4 (datos) y anexo EDA |
| `features/g01-g09` (9) | mapa del registro, coste de warm-up, invariancia de prefijo, contraejemplo de fuga, distribuciones, redundancia, estabilidad anual, as-of join, roles temporales | Cap 5 |
| `backtest/h01-h06` (6) | semántica de ejecución, descomposición de costes, frontera de rotación, funding, geometría walk-forward, baselines | Caps 4-5 |
| `search/i01-i06` (6) | espacio vs presupuesto, optimismo de selección, estructura del optimismo, RS vs GA, inestabilidad por semilla, convergencia | Caps 5-6 |
| `closure/j01-j04` (4) | criterios de promoción, corrección múltiple, DSR y PBO, condicionado por régimen | Caps 6-7 |
| `experiments/` (1) | equity momentum dev | opcional |

## Figuras que faltan, con su comando

| Figura | Sección | Cómo se genera |
|---|---|---|
| ~~Distribución nula de Monte Carlo~~ **HECHA 19-08**: `montecarlo/k01-k05` + tablas `t01-t05` (nula por rotación con las 10 semillas dentro, percentiles 0,22-0,97; cruce de costes ~2,3x; prop-firm 31%/11,5%) | Cap 6/anexo — **la figura que resume el TFM es k03** | `scripts/build_montecarlo_notebook.py` (cuaderno 07); módulo `src/perp_lab/evaluation/montecarlo.py` con 8 tests; determinismo verificado 10/10 |
| Resultados CRT V1 agregados | Cap 6 | al cierre de la ronda: `uv run python scripts/summarise_multiseed.py artifacts/runs/crt_v1_budget100/<familia>` + builder de figura a añadir |
| `ml/m01-m05`: economía vs AUC por fold, calibración, SHAP, abstención (estudio meta real, trío LR/RF/LightGBM completado 19-08) | Cap 5.8 y 6 (RQ3) | `build_ml_notebook.py` (cuaderno 06 nuevo; el estudio ya corre con los tres modelos preregistrados + SHAP en la rama `feat/meta-labeling-real-data`, commit `c42e4c3`) |
| Pipeline y esquema temporal como imagen | Cap 5 | exportar los Mermaid de `docs/methodology/pipeline_end_to_end.md` (mmdc o captura) |

## Reparto de palabras (objetivo 22.000)

1: 2.000 · 2: 3.500 · 3: 1.200 · 4: 2.500 · 5: 5.000 · 6: 2.500 · 7: 2.000 ·
8: 1.800 · 9: 1.200 · 10: 1.300. Escrito hoy: 4.114 (caps 6/8/9 con numeración
antigua). Borradores nuevos de este bloque: caps 4, 5 y 7 (~5.500 adicionales en
`docs/thesis/borradores/`).

## Dependencias duras

- Nada del cap 6 sobre CRT hasta que `crt_v1_execution.json` diga
  `"status": "completed"`.
- La subsección RQ3 del cap 6 cita artefactos de la rama
  `feat/meta-labeling-real-data`; exige la fusión previa (plan en
  `docs/audit/03_reorganizacion_propuesta.md` §3).
- El anexo Monte Carlo depende del Bloque C.
