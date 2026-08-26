# Capítulo 4 — Tablas 4.1, 4.2 y 4.3, cierres [VERIFICAR] y correcciones

Todos los valores están verificados contra el repositorio; cada fila cita su
fuente. Ningún número de este documento es una estimación.

Figuras: `reports/figures/thesis_ch4/` (builder: `scripts/build_ch4_figures.py`;
la 4.11 es una captura real del panel en marcha, variantes EN y ES).

---

## Tabla 4.1 — Stack tecnológico con versiones exactas

**Fuente:** `pyproject.toml` + `uv.lock` (versiones resueltas y bloqueadas) y
`apps/web/package.json`. El entorno se reconstruye con `uv sync`; no hay
contenedor — el lockfile de uv es el mecanismo de fijación (ver corrección C4).

| Capa | Tecnología | Versión bloqueada | Papel |
|---|---|---|---|
| Lenguaje | Python | 3.12 (`requires-python >=3.12`; intérprete del venv 3.12.3) | todo el backend de investigación |
| Datos | Polars | 1.43.1 | motor columnar principal (ingesta, features, backtest) |
| | PyArrow | 25.0.0 | Parquet I/O |
| | DuckDB | 1.5.5 | consultas analíticas sobre el catálogo (`catalog/analytics.py`) |
| Modelado | NumPy / SciPy | 2.5.1 / 1.18.0 | numérica y tests estadísticos |
| | scikit-learn | 1.9.0 | utilidades ML |
| | LightGBM / SHAP | 4.7.0 / 0.50.0 | meta-labeling (validado en sintético, ADR 0017) |
| | statsmodels | 0.14.6 | diagnósticos econométricos |
| Contratos | pydantic | 2.13.4 | validación de configuración |
| | pandera | 0.32.1 | esquemas de DataFrames |
| Registro | SQLAlchemy + SQLite | (stdlib sqlite) | registro de experimentos (`data/catalog/catalog.sqlite`) |
| Serving | FastAPI / uvicorn | 0.141.1 / 0.52.1 | API de solo lectura |
| Descarga | ccxt | 4.5.70 | metadatos de exchange (la historia masiva llega por `data.binance.vision`) |
| Calidad | pytest | 9.1.1 | 1 539 tests recogidos (1 538 no-red en CI) |
| | ruff | 0.16.0 | lint + formato |
| | pyright | 1.1.411 | tipado estático (local, pre-release) |
| Figuras | matplotlib | 3.11.1 | todas las figuras congeladas |
| Entorno | uv (lockfile `uv.lock`) | — | reproducibilidad del entorno; sin contenedor |
| Frontend | Next.js / React | ^14.2.35 / 18.3.1 | panel bilingüe |
| | TypeScript | ^5.6.3 | tipado del frontend y del laboratorio en navegador |
| | Recharts / SWR | ^2.13.3 / ^2.2.5 | gráficos / fetching |
| | vitest | ^2.1.4 | 112 tests del motor TS y del laboratorio |
| CI | GitHub Actions | `.github/workflows/ci.yml` | gate en cada push y PR |

---

## Tabla 4.2 — Índice real de ADRs (`docs/decisions/`)

18 registros, todos fechados. La columna «papel en la tesis» es sugerencia de
redacción, no está en los ADRs.

| ADR | Título | Estado | Fecha | Papel en la tesis |
|---|---|---|---|---|
| 0001 | Record architecture decisions | Accepted | 2026-07-30 | meta: el mecanismo mismo |
| 0002 | Binance USDT-M bulk data, 5m base con 15m/1h derivados | Accepted | 2026-07-30 | contrato de datos (Cap. 3) |
| 0003 | Cutoff date and frozen holdout window | Accepted | 2026-07-30 | partición final congelada |
| 0004 | Chapter 5 methodology and experimental contract | Accepted | 2026-08-03 | contrato metodológico |
| 0005 | Provisional transaction-cost assumptions | **Proposed** (provisional) | 2026-08-03 | costes 4+1 pb; único ADR no «Accepted» |
| 0006 | First experimental vertical slice and run-tracking | Accepted | 2026-08-03 | nacimiento del tracking |
| 0007 | Configuration-driven causal feature engine | Accepted | 2026-08-03 | features por YAML |
| 0008 | Experimental foundation: regimes, family, backtester, WF | Accepted | 2026-08-04 | motor + walk-forward |
| 0009 | Strategy-search framework — RS and GA | Accepted | 2026-08-04 | dos motores, paridad de presupuesto |
| 0010 | OOS evaluation layer — baselines, robustness | Accepted | 2026-08-05 | batería C1–C6 |
| 0011 | Multi-seed baseline (momentum) | **Superseded** por ADR 0013 | 2026-08-05 | trazabilidad del error |
| 0012 | Outer-fold contamination in candidate search | Accepted (implementado 2026-08-09) | 2026-08-08 | **el bug metodológico y su corrección** |
| 0013 | Clean momentum re-baseline | Accepted | 2026-08-09 | re-línea base limpia (R2) |
| 0014 | R3 budget bounded by smallest finite search space | Accepted | 2026-08-10 | presupuesto honesto |
| 0015 | Gate R3 closes with zero promotions | Accepted | 2026-08-10 | primer cierre negativo |
| 0016 | Gate S1 batch 01 pre-specified and frozen | Accepted | 2026-08-11 | prerregistro operativo |
| 0017 | Meta-labeling validated on synthetic data | Accepted | 2026-08-11 | capa ML sin tocar candidatos |
| 0018 | Run-identity diff scoped to RELEVANT_DIRS | Accepted | 2026-08-19 | refinamiento de identidad |

Narrativa citable: la secuencia 0011 → 0012 → 0013 documenta un error real
(contaminación del pliegue externo), su detección, su corrección y la
invalidación explícita de la evidencia anterior — exactamente el comportamiento
que el capítulo defiende como MLOps científico.

---

## Tabla 4.3 — Coste computacional por ronda (medido, no estimado)

**Fuente:** los 447 directorios de `artifacts/runs/`. Evaluaciones = filas de
`{random_search,genetic_algorithm}_candidates.parquet` (una fila = una
configuración evaluada en un pliegue por un motor). Tiempo = suma del ledger de
paridad de presupuesto (`comparison_summary.json: budget_parity.per_engine.
per_fold.seconds`), que cubre la búsqueda; excluye reporting y la batería de
robustez. Agrupación por el prefijo del `label` del run.

| Ronda | Runs | Familias | Semillas | Evaluaciones | Tiempo de búsqueda registrado |
|---|---|---|---|---|---|
| Fase A — smoke (validez técnica) | 21 | 1 | 5 | 621 | no registrado (anterior al ledger) |
| Desarrollo exploratorio (slice vertical) | 29 | 1 | 11 | 9 244 | no registrado (anterior al ledger) |
| Fase B — piloto | 19 | 6 | 2 | 20 760 | ≥ 5,8 min (8 runs sin ledger) |
| R2 — re-línea base limpia (momentum) | 20 | 1 | 10 | 180 000 | 121,9 min |
| R3 — estudio completo (5 familias) | 102 | 5 | 10 | 306 000 | 72,4 min |
| S1 batch 01 (4 familias, prerregistradas) | 4 | 4 | 1 | 3 000 | 0,4 min |
| S2 batch (3 familias) | 18 | 3 | 3 | 13 500 | 2,5 min |
| CRT battery (9 familias) | 214 | 9 | 10 | 642 000 | 2 527,3 min (≈ 42,1 h) |
| **Total (runs de búsqueda)** | **427** | — | — | **1 175 125** | **≈ 45,5 h registradas** |

Notas verificadas:

- Los 20 directorios restantes hasta 447 no son búsquedas comparativas
  (estudios multi-seed agregados, un run abortado, etc.).
- La aritmética cuadra donde el protocolo lo exige: R3 y CRT dan exactamente
  3 000 evaluaciones por run = 100 candidatos × 15 pliegues × 2 motores. R2 usó
  300 por pliegue y motor (presupuesto ampliado de la re-línea base, ADR 0013).
- Todo corre en 1 h (`timeframe: "1h"` en los 427 runs); las familias CRT son
  ~9× más caras por evaluación por su maquinaria de estados.
- La cifra que ya usa el panel — 496 500 configuraciones del artefacto de
  cierre — es el subconjunto que entra en el veredicto (R2+R3+CRT+S: las fases
  confirmatorias). El 1,18 M de aquí incluye además smoke, desarrollo y piloto.
  Conviene citar cada cifra con su alcance para que no parezcan contradictorias.

---

## Cierres de los [VERIFICAR] del borrador

| Ítem del borrador | Cierre verificado |
|---|---|
| Versiones del stack | Tabla 4.1 (de `uv.lock`, no de `pyproject`, que solo fija mínimos) |
| Índice de ADRs | Tabla 4.2 — la carpeta real es `docs/decisions/`, no `docs/adr/` |
| Política exacta de QC | **Descarte no, forward-fill no, exclusión no: se marca y se reporta.** `validation/quality.py` solo tiene funciones de detección (`find_gaps`, `find_duplicates`, `check_ohlc_consistency`, `flag_extreme_returns`, `quality_report`); no existe ninguna ruta de reparación. En la ventana de desarrollo el punto es discutible: cobertura 100 %, 0 huecos, 0 duplicados, 0 OHLC inválidos; la única clase de anomalía son barras de volumen cero (66 BTC / 47 ETH en 5 m), que se conservan y se señalan (Fig. 4.4) |
| Lockfile / contenedor | `uv.lock` committeado; **no hay contenedor**. Redactar «environment pinned via uv's lockfile», no «containerised» |
| Nº de tests | **1 539 recogidos por pytest** (1 538 al excluir el único test marcado `network`, que es lo que corre CI) **+ 112 vitest** en `apps/web`. Citar «1 538 non-network Python tests and 112 TypeScript tests» |
| Proveedor de CI y etapas | GitHub Actions (`.github/workflows/ci.yml`), job único `gate` en ubuntu-latest, timeout 25 min: checkout → `uv sync --extra dev` → `ruff check` → `ruff format --check` → **stale-claims sweep** (`scripts/check_stale_claims.py`) → `pytest -m "not network"`. pyright y el check de determinismo de cuadernos quedan locales a propósito (el segundo necesita el data lake). Dispara en push a `main`/`feat/**`/`fix/**`/`docs/**`/`style/**`/`chore/**` y en cada PR |
| Evaluaciones y horas por ronda | Tabla 4.3 |

---

## Correcciones al borrador del capítulo 4

Cuatro afirmaciones del texto no sobreviven al contraste con el código. Las dos
primeras importan porque el tribunal puede abrir el repo.

**C1. «Content-addressed paths» — falso; el modelo real es mejor contado tal
cual es.** Los paths son deterministas y legibles
(`data/validated/BTCUSDT/fundingRate.parquet`), no derivados del contenido. La
integridad viene de otro sitio: cada dataset lleva un manifiesto con su SHA-256
(`data/manifests/*.json`) y la verificación es re-hashear los bytes contra el
manifiesto — un mismatch aborta el run. Redacción sugerida:

> Artefacts live at deterministic, human-readable paths; integrity is enforced
> not by content-addressing but by a SHA-256 recorded in a per-dataset
> manifest and re-verified against the bytes, so re-running a download either
> reproduces the recorded hash or fails loudly.

El incidente del 2026-08-19 (re-ingesta completa byte-idéntica) es la
demostración empírica de esta afirmación y vale la pena citarlo aquí además de
en el Cap. 3.

**C2. «Runs identified by the hash of their configuration» — a medias, y la
distinción es precisamente la interesante.** El *id* del run es
`<kind>_<UTC-stamp>_<6-hex aleatorio>` (`tracking/run.py: generate_run_id`) —
una dirección ordenable y única, deliberadamente **no** derivada de la
configuración. La identidad-por-hash existe pero es un artefacto separado: el
*fingerprint* de `tracking/identity.py` (SHA-256 sobre configuración resuelta +
contratos + SHA-256 de las particiones legibles + commit/branch/diff **incluidos
los ficheros sin trackear** bajo `src/`, `tests/`, `configs/`), guardado en
`run_identity.json`. Dos runs son el mismo experimento si y solo si coinciden
sus fingerprints, con independencia de sus ids (Fig. 4.9). Redacción sugerida:

> Each run receives two names: an address — a timestamped identifier used for
> storage — and an identity — a SHA-256 fingerprint over the resolved
> configuration, the frozen contracts, the hashes of every readable data
> partition and the exact code state, including untracked files. Two runs are
> the same experiment iff their fingerprints match; the address is
> deliberately not derived from the configuration, so identity can never be
> confused with mere naming.

**C3. «Golden tests» — no hay tests con ese nombre; la garantía equivalente
existe con otra forma.** Lo que hay: 17 tests unitarios del motor
(`tests/unit/test_backtesting*.py`) que fijan salidas exactas calculadas a mano
(`pytest.approx` sobre retornos, costes y equity en entradas fijas), más los
tests de invariantes y de no-fuga. En el frontend, los 112 tests de vitest
cumplen el mismo papel para el port TS. Sugerencia: sustituir «golden tests»
por «pinned-output unit tests that fix the engine's exact arithmetic on
hand-computed fixtures» — misma garantía, nombre que sí resiste un grep.

**C4. Entorno: lockfile sí, contenedor no.** Si el borrador dice o insinúa
contenedor/Docker, quitarlo: la reproducibilidad del entorno es
`uv.lock` + `uv sync` (y CI lo usa con caché). No hay Dockerfile en el repo.

Menores: la carpeta de ADRs es `docs/decisions/` (no `docs/adr/`); el registro
es SQLite vía SQLAlchemy con DuckDB **solo** para consultas analíticas (no es
la base del registro); y si el texto menciona Streamlit como dashboard, el
dashboard real del proyecto es la app Next.js (`apps/web`) — streamlit figura
como extra opcional en `pyproject.toml` pero el panel citable es el web.

---

## ¿Cómo lo acabaría? — puntos de mejora del capítulo

Estructura: el borrador está bien armado; lo que le falta es (a) cerrar las
cuatro correcciones de arriba, (b) anclar cada afirmación a un artefacto igual
que hacen los caps. 3 y 6, y (c) tres añadidos que lo suben de descripción de
sistema a argumento:

1. **Contar la cadena de identidad como contribución, no como fontanería.** La
   distinción dirección/identidad (C2) + el sweep de stale-claims en CI + el
   registro append-only del holdout forman un argumento único: *el sistema hace
   estructuralmente difícil mentirse*. Merece una subsección propia (4.x
   "Integrity by construction") que remate con el incidente del 2026-08-19
   como test de fuego no planeado.

2. **El sweep de stale-claims es la pieza más original del CI y el borrador no
   lo explota.** Un gate que rompe la build si un documento committeado afirma
   un resultado sin artefacto detrás es MLOps aplicado a la *escritura* de la
   tesis. Dedícale un párrafo con un ejemplo concreto de fallo.

3. **Tabla 4.3 como argumento de honestidad presupuestaria.** La aritmética
   100 × 15 × 2 = 3 000 evaluaciones/run cuadra exactamente en R3 y CRT — es
   la prueba de que el presupuesto declarado en el protocolo es el ejecutado.
   Señálalo explícitamente; y aclara el doble alcance 496 500 (confirmatorio)
   vs 1,18 M (total) para blindarte ante una pregunta del tribunal.

4. **Limitaciones honestas del apartado (medio párrafo, gana credibilidad):**
   un solo entorno de ejecución (Windows local; CI en ubuntu — la
   reproducibilidad cross-OS de los parquets no está verificada bit a bit),
   sin contenedor, pyright fuera de CI, el tiempo de la batería de robustez no
   está en el ledger, y el registro SQLite es mono-máquina por diseño.

5. **Figura 4.11:** usar la captura EN (`fig_4_11_dashboard.png`) por
   coherencia con el idioma de la tesis; existe la variante ES
   (`fig_4_11_dashboard_es.png`). La captura muestra el estado real: API en
   línea, 427 runs, 13 familias, 496 500 configuraciones, 0 supervivientes,
   PBO 0,486 — ninguna cifra maquetada.

6. **Orden de figuras sugerido sin cambios de numeración:** el borrador ya las
   coloca bien; solo mover la 4.9 (cadena de reproducibilidad) para que
   preceda a la discusión del registro (4.8) si la sección 4.x de integridad
   del punto 1 se adopta — la cadena es la premisa, el registro la
   consecuencia.

---

## Addendum — profundidad de ingeniería para la versión final del capítulo

La versión final del capítulo (7 figuras) queda cubierta así por los ficheros
de `reports/figures/thesis_ch4/`:

| Figura final | Fichero | Nota |
|---|---|---|
| 4.1 arquitectura end-to-end | `fig_4_1_architecture` | planos + gobernanza |
| 4.2 linaje de datos y particiones | `fig_4_2_data_dag` (+ `fig_4_3_storage_layout` como apoyo) | |
| 4.3 contrato temporal (2 paneles) | **`fig_4_3_temporal_contract`** | compuesta nueva: A agregación causal + B ejecución next-open |
| 4.4 orquestación + captura de evidencia | **`fig_4_4_orchestration_evidence`** | compuesta nueva: búsqueda + paquete de evidencia + catálogo |
| 4.5 cadena de identidad | `fig_4_9_reproducibility_chain` | |
| 4.6 quality gates | `fig_4_10_ci_pipeline` | |
| 4.7 dashboard | `fig_4_11_dashboard` (EN) / `_es` | captura real |

Y las cuatro figuras de ingeniería adicionales que pediste, numerables donde
prefieras (sugerencia entre paréntesis):

| Fichero | Contenido | Inserción sugerida |
|---|---|---|
| **`fig_4x_module_map`** | mapa real del monorepo: 22 paquetes, 172 ficheros, 42.380 líneas, agrupados por plano con su papel | §4.1, tras la Fig. 4.1 (como Fig. 4.2 nueva o apéndice) |
| **`fig_4x_catalog_erd`** | ERD detallado del catálogo con las columnas reales de las 12 tablas + mixins (Provenance/Status/CoreMetrics) | §4.4, junto al párrafo del catálogo |
| **`fig_4x_config_lifecycle`** | ciclo config-as-code: YAML congelado → pydantic → configuración resuelta → gate del registro de familias | §4.4, primer párrafo |
| **`fig_4x_seed_derivation`** | árbol de semillas determinista con los valores reales de un run (base 278037 → streams por motor/pliegue) | §4.4, párrafo de independencia estocástica |

Párrafos en inglés listos para insertar (verificados contra el repo):

**§4.1 — organización del código (con `fig_4x_module_map`):**

> The monorepo contains twenty-two Python packages totalling roughly 42,000
> lines, organised along the four operational planes of Figure 4.1. The data
> plane (`data`, `validation`, `features`, `labeling`) owns everything that
> touches raw observations; the research engine (`strategies`, `crt`,
> `backtesting`, `search`, `experiments`, `meta_labeling`) defines and
> simulates hypotheses; the evidence plane (`evaluation`, `catalog`,
> `tracking`, `reporting`, `eda`) turns simulations into auditable artefacts;
> and the consumption plane (`api`, plus the Next.js application) exposes
> them read-only. Configuration contracts and deterministic utilities cut
> across all planes. The command-line layer is deliberately thin:
> orchestration logic lives in importable, tested modules, so every pipeline
> step can be exercised by the test suite without a subprocess.

**§4.4 — esquema del catálogo (con `fig_4x_catalog_erd`):**

> The catalogue schema mirrors the experimental hierarchy: a study contains
> rounds and families; families freeze specifications; runs bind a family,
> asset, engine and seed schedule to a resolved configuration and an identity
> fingerprint; and per-run children record seeds, folds, fold results,
> candidate evaluations, metrics, gate verdicts and artefact receipts. Three
> mixins give the schema its scientific character. Every table inherits
> provenance columns (source artefact, SHA-256, Git commit, code version,
> ingestion time); result-bearing tables add a status pair so that partial or
> superseded evidence remains distinguishable from clean results; and
> performance tables share one fixed metric vocabulary, which prevents the
> same quantity from appearing under different names in different rounds.
> Ingestion enforces referential integrity as a research rule: a metric row
> that cannot be traced to a concrete measurement raises an integrity error
> rather than being stored as an orphan number.

**§4.4 — ciclo de configuración (con `fig_4x_config_lifecycle`):**

> Configuration follows a single lifecycle. The frozen YAML contracts and the
> researcher's abbreviated invocation are parsed into typed pydantic models,
> which reject unknown feature kinds, invalid windows or malformed parameter
> ranges before any data is read. The fully resolved configuration is then
> written into the run directory verbatim and hashed into the run fingerprint,
> so the authoritative description of an experiment is always what executed,
> never what was typed.

Cifras de apoyo verificadas: 172 ficheros / 42.380 líneas en `src/perp_lab`
(el builder las imprime al regenerar); 22 paquetes; 447 paquetes de evidencia
en `artifacts/runs`; purga 96 / embargo 118 en la tabla `folds`; token
`OPEN_FINAL_HOLDOUT` y registro append-only en `holdout_registry`
(coincide con §4.5 del borrador).
