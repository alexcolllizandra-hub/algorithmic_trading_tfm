# Inventario real del repositorio

Fecha: 2026-08-19. Cada afirmación lleva la ruta donde se comprobó. Estados:
`IMPLEMENTADO Y TESTEADO` (IT) / `IMPLEMENTADO SIN TEST` (IS) / `DECLARADO PERO
INEXISTENTE` (DPI).

## 1. Árbol anotado por módulos

Propósito deducido del código, no del docstring. El paquete instala como
`perp-lab`, importa como `perp_lab` (`pyproject.toml`).

| Módulo | Propósito real | Estado |
|---|---|---|
| `src/perp_lab/data/` | Descarga masiva de data.binance.vision + incrementales CCXT; particionado development/holdout (`splits.py`) | IT |
| `src/perp_lab/validation/` | Esquemas Pandera (`schemas.py`), calidad con extremos marcados-nunca-borrados (`quality.py`), walk-forward con purga/embargo derivados (`walk_forward.py`) | IT (`tests/unit/test_quality.py`, `test_walk_forward.py`) |
| `src/perp_lab/features/` | Motor causal declarativo: cada feature declara ventana, warm-up e instante de conocibilidad (`spec.py`, `registry.py`, `causal.py`) | IT (7 tests de causalidad sobre datos reales) |
| `src/perp_lab/strategies/` | Familias interpretables R2/R3: momentum, breakout, mean_reversion, volatility_breakout, funding, cross-asset (`base.py` fija `SIDE_COL` ∈ {−1,0,+1}) | IT |
| `src/perp_lab/crt/` | Las 9 familias CRT_INTRADAY_V1: máquina de estados AVAILABLE→SWEPT→RECLAIMED→RETESTED→… (`strategies.py`) | IT |
| `src/perp_lab/backtesting/` | Motor next-bar: señal al cierre de t, ejecución en open de t+1, `oo_return`; fees+slippage+funding reales o fallo (`engine.py`) | IT |
| `src/perp_lab/search/` | Espacios tipados con hash canónico (`space.py`), RS y GA a presupuesto de evaluaciones únicas (`random_search.py`, `genetic_algorithm.py`), evaluador aislado por fold — ADR 0012 (`evaluator.py`), runner (`runner.py`, 46 KB) | IT |
| `src/perp_lab/evaluation/` | Corrección múltiple completa: DSR, PBO/CSCV, Holm, BH, White RC, Hansen SPA, bootstrap estacionario (`multiple_testing.py`, 582 líneas); robustez de estudio y gate R3 (`study_robustness.py`) | IT (`test_multiple_testing.py`) |
| `src/perp_lab/labeling/` | Triple barrera sobre retornos netos, fill `next_open` coherente con el motor (`triple_barrier.py`) | IT |
| `src/perp_lab/meta_labeling/` | En este árbol solo `model.py` (clasificadores+calibración). El estudio completo (`study.py` 920 líneas, `synthetic.py`, `diagnostics.py`, `metrics.py`) vive en la rama `feat/m1m2-synthetic-validation`, fusionada en `feat/meta-labeling-real-data` | IT en rama; **no en main ni en study-closure** |
| `src/perp_lab/regimes/` | Threshold/KMeans/GMM ajustados solo en train (`models.py`) | IT |
| `src/perp_lab/tracking/` | `run_identity` = config+contrato+hashes+commit+diff (`identity.py`; defecto en línea 111, ver auditoría) | IT, con defecto conocido |
| `src/perp_lab/experiments/` | Orquestación multi-seed con checkpoint/resume (`multi_seed.py`); apertura sancionada de holdout (`final_holdout.py`) | IT |
| `src/perp_lab/reporting/` | Cierre de estudio, dashboard JSON, informes por gate (`study_closure.py`, `study_dashboard.py`, `s1_pilot.py`) | IS parcial |
| `src/perp_lab/api/` | FastAPI real, 2.104 líneas (455 en `services.py`): sirve runs, estudio cerrado, salud | IS |
| `src/perp_lab/dashboard/` | Dashboard Streamlit v0 (`loader.py`, `app.py`) — **superseded** por `apps/web`; sigue funcionando vía `perp-lab dashboard` | IS, candidato a legacy |
| `src/perp_lab/eda/` | 24 módulos de análisis con scipy.stats (Kruskal, Dunn, colas, bootstrap) | IT parcial |
| `src/perp_lab/stochastic/` | GBM y benchmarks estocásticos — solo en las ramas m1m2/meta-labeling | IT en rama |
| `apps/web/` | Next.js 14 App Router, ES único, landing + panel; lee JSON estático de `public/data/` | IS (vitest: 7 tests de `/guia` rotos por mock de router pendiente) |
| `apps/api/` | **Sin código Python (0 ficheros .py)**: Dockerfile + README. La API real está en `src/perp_lab/api` | DPI como servicio separado |
| `scripts/` | 40+ utilidades: builders de notebooks, rondas (`run_crt_v1.py`, `run_r3_full.py`), auditoría de aislamiento, export de evidencia web | IS (son drivers) |
| `notebooks/` | 5 notebooks 01–05 **generados** por `scripts/build_*_notebook.py`; regla en `.cursor/rules/notebook-policy.mdc` | IT vía builders |
| `supabase/`, `migrations/` | Auth y persistencia de la plataforma (fuera del núcleo de investigación) | IS |

## 2. Artefactos de resultados

| Ruta | Contenido | Generado por | ¿Reproducible hoy? |
|---|---|---|---|
| `reports/study_closure/study_level_multiple_testing.json` | Cierre canónico: 13 familias, p mínimo 0.3455, PBO 0.4857/70 splits, sensibilidad 13→496.500 | `perp-lab` study-closure reporting | Sí (partición development intacta) |
| `reports/study_closure/final_holdout.json` | La apertura del holdout del 13-08 (lectura retenida) | `experiments/final_holdout.py` | **No debe reejecutarse** (partición consumida) |
| `reports/r3_gate/r3_full_budget100_ga21/thesis_report.json` | Informe R3 verificado por reporter | rama `feat/r3-thesis-reporting` | Sí |
| `artifacts/runs/r3_full_budget100_ga21/` | Estudio R3 completo: 5 familias × 20 units, 100/100 auditados | `run_r3_full.py` | Sí (~horas de cómputo) |
| `artifacts/runs/crt_v1_budget100/` | Ronda CRT en curso: 4/9 familias completas a 19-08; `crt_v1_execution.json` con `promotion_possible:false` | `scripts/run_crt_v1.py` | En ejecución |
| `artifacts/runs/crt_v1_budget100/_DESCARTADO_huella_arbol_sucio/` | ~23 unidades computadas bajo árbol sucio + `POR_QUE.md` | incidente 17-08 | Provenance, no tocar |
| `artifacts/runs/crt_v1_ABORTED_fc662f9/` | Primer intento CRT abortado | ídem | Provenance |
| `artifacts/runs/r3_full/`, `r3_full_budget100/` | Raíces de proceso fallidas, retenidas por ADR 0015 §5 | — | Provenance |
| `artifacts/runs/multiseed_momentum_*` (3 dirs) | Baseline momentum R1/R2 (ADR 0011/0013) | multi-seed runner | Sí |
| `artifacts/runs/search_*` (~300 dirs) | Runs individuales por familia/seed/fecha | runner | Sí, unitariamente |
| `reports/figures/` (51 PNG+PDF) | eda 25 · features 9 · backtest 6 · search 6 · closure 4 · experiments 1 | notebooks 01–05 | Sí, pero **no versionadas** (`.gitignore:54`) |
| `reports/tables/` (~100 CSV+MD) | Tablas t01–t39 por capa | notebooks | Versionadas |
| `reports/meta_labeling_real/` | RQ3 sobre datos reales (18-08) | `scripts/run_meta_labeling_real.py` | Solo en rama `feat/meta-labeling-real-data` |
| `reports/data_provenance/data_provenance_audit.json` | Auditoría de procedencia de datos | script homónimo | Sí |
| `data/manifests/*.json` | SHA-256 por dataset | ingesta | Sí |

## 3. Código muerto / duplicado / legacy

| Elemento | Evidencia | Recomendación |
|---|---|---|
| Notebooks legacy LSTM/Transformer/Optuna/DEAP/stacking del encargo | grep en todo el árbol: solo falsos positivos en base64 de imágenes | **No existen (DPI).** Nada que archivar |
| `src/perp_lab/dashboard/` (Streamlit) | Superseded por `apps/web`; sin tests de UI; `docs/research_dashboard.md` lo documenta como v0 | Archivar tras la defensa: mover a `legacy/` o borrar con tag. Mientras, una línea en su docstring: "superseded by apps/web" |
| `apps/api/` sin código | 0 `.py`; Dockerfile huérfano | Decidir: cablear (mover el arranque de `src/perp_lab/api` aquí) o borrar el directorio y documentar el despliegue en `docs/platform/` |
| `docs/roadmap.md` | Se autodeclara «superseded», duplica `docs/roadmap/README.md` | `git rm` (la historia queda en git); ya listado como superseded en `docs/roadmap/README.md` |
| Raíz: `ingest.log`, `ingest2.log`, `perp_lab_repo.zip` | No trackeados, cubiertos por `.gitignore` (líneas 40, 85) | `rm` local cuando cierre la ronda (tocarlos ahora no rompe la huella por ser untracked, pero mejor una sola limpieza) |
| `artifacts/runs/search_*` ~300 dirs | Runs unitarios ya agregados en study dirs | Conservar: son la evidencia primaria de los agregados. No es código muerto, es provenance |
| Worktrees colgantes: `../tfm-dashboard-redesign`, `../tfm-outer-fold-leakage` | `git worktree list` | Cerrar tras verificar que sus ramas no tienen commits únicos pendientes (dashboard-redesign +2, outer-fold-leakage +3 sobre study-closure) |

## 4. Deriva de nombres de marca

Medida por grep sobre `apps/`, `docs/`, `src/`, configs:

| Nombre | Ficheros | Dónde |
|---|---|---|
| `perp_lab` / `perp-lab` | 141 / 30 | Paquete Python, CLI, docs técnicos |
| `Alx Systems` | 8 | Web pública: metadatos, títulos, aviso legal (`apps/web/src/app/(site)/aviso-legal/page.tsx`, `icon.tsx`, layout) |
| `alxsystems` | 1 | `apps/web/src/lib/legal.ts` (`soporte.alxsystems@gmail.com`) |
| `Quantivela` | 1 | Remitente de email transaccional (`Quantivela <hola@quantivelasystems.com>`, config de Resend/Supabase) |

Tres identidades conviven: la marca pública es **Alx Systems**, el motor es
**perp-lab**, y el correo saliente firma **Quantivela**. Un usuario que se registre
en la web de Alx Systems recibirá un email de Quantivela: eso es un bug de
confianza, no solo de estilo. Recomendación mínima antes de publicar: unificar el
remitente con la marca pública (cambiar el From en la config de Resend) y dejar
perp-lab como nombre del motor citado en la web («motor de investigación
perp-lab»), que ya es como lo trata la landing.
