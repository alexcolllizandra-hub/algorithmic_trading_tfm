# Auditoría de calidad e ingeniería

Fecha: 2026-08-19. Severidades: crítica / alta / media / baja. Cada hallazgo lleva
evidencia (ruta) y coste estimado de arreglo.

## 1. Reproducibilidad

| Hallazgo | Severidad | Evidencia | Coste |
|---|---|---|---|
| La huella de identidad hashea el diff del árbol **entero**: `RELEVANT_DIRS = ("src","tests","configs","docs/methodology")` se aplica a untracked pero no al diff | **Crítica** (operativa, no científica: no falsea resultados, los invalida administrativamente) | `src/perp_lab/tracking/identity.py:111` (`_git(["diff","HEAD","--"])` sin rutas); consecuencia: `artifacts/runs/crt_v1_budget100/_DESCARTADO_huella_arbol_sucio/POR_QUE.md` | 30 min código + test, 1 h ADR. **No aplicar hasta que cierre CRT V1**: cambiaría la huella de la ronda en curso |
| Semillas: derivación determinista por unidad/stream | OK | `src/perp_lab/utils/seeds.py` (`SeedScheduler.stream(...)` keyed por símbolo/fold); regímenes estocásticos con stream propio (`search/evaluator.py`, `build_folds_data`) | — |
| Entorno fijado | OK | `uv.lock` versionado; Python fijado en `pyproject.toml` | — |
| Determinismo de la búsqueda | OK | Todo muestreo pasa por `np.random.Generator` inyectado (`search/space.py`: «nothing samples from global RNG state»); smoke reproducido en sesión del 16-08 | — |
| ¿Ronda entera desde cero hoy? | Sí con matiz | Checkpoint/resume probado bajo 3 caídas reales (17/18-08); lo único no reproducible por diseño es la lectura del holdout (partición consumida, `docs/methodology/holdout_audit_status.md` §5.1) | — |
| LightGBM preregistrado pero no instalado: los estudios meta corren 2/3 modelos | Media | `src/perp_lab/meta_labeling/model.py` (import perezoso con error explícito); `reports/meta_labeling_real/meta_labeling_real.json` («models»: lr, rf) | 15 min (`uv add --optional ml lightgbm`) + reejecutar estudio meta (~10 min) |

## 2. Contratos de datos

| Hallazgo | Severidad | Evidencia | Coste |
|---|---|---|---|
| Contrato congelado y aplicado por código | OK | `configs/data_contract.yaml` (base 5m, derivados 15m/1h, cutoff 2026-07-01 exclusivo); `src/perp_lab/config/models.py`; holdout resuelto en `data/splits.py:29` | — |
| Validación estructural + calidad | OK | Pandera en `validation/schemas.py` (strict=True: columnas inesperadas fallan); huecos/duplicados/OHLC/extremos en `validation/quality.py`; extremos marcados, nunca borrados | — |
| Integridad por hash | OK | `data/manifests/*.json` con SHA-256; el receipt se muestra hasta en la landing (`apps/web/src/components/landing/Integrity.tsx`) | — |
| Timezone | OK | `pl.Datetime(time_unit="ms", time_zone="UTC")` obligatorio en esquema (`validation/schemas.py:14`) | — |
| Carga development-safe por defecto | OK | `eda/datasets.py` (`DataLake`): partición development filtra `< holdout_start` y ejecuta `assert_no_holdout`; leer holdout exige pedirlo explícitamente | — |

## 3. Fugas de información

| Hallazgo | Severidad | Evidencia | Coste |
|---|---|---|---|
| Purga y embargo derivados, no elegidos a ojo | OK | `validation/walk_forward.py` (embargo ≥ purge, derivados de label_horizon/max_holding vía config) | — |
| Aislamiento por fold físico, no por disciplina | OK | `search/evaluator.py`: `single_fold_bundle` — el evaluador no contiene referencias a otros folds; `FoldIsolationError` si se le pide uno ajeno. ADR 0012 | — |
| Escalado/regímenes dentro del fold | OK | Regime model y scaler ajustados solo en train y aplicados causalmente (`build_folds_data`) | — |
| Selección de hiperparámetros | OK | Fitness solo sobre validación; test se puntúa una vez sobre el ganador congelado con fingerprint («freeze first, evaluate second», `search/runner.py`) | — |
| Verificación activa, no pasiva | OK | 7 tests de causalidad sobre datos reales; fuga plantada falla al instante; `scripts/audit_study_isolation.py` 100/100 en R3 y 20/20 en las familias CRT cerradas | — |
| Meta-labeling: umbral y calibración | OK (en rama) | `meta_labeling/model.py`: `fit_meta_model` no acepta test; tres bloques cronológicos disjuntos | — |

Veredicto de la sección: es la parte más sólida del repo. Un tribunal que ataque
por fugas se va a encontrar el terreno minado a favor del autor.

## 4. Costes de transacción

| Hallazgo | Severidad | Evidencia | Coste |
|---|---|---|---|
| Modelo: fee 4 bps + slippage 1 bps por lado, funding real por barra | OK | ADR 0005 (provisional, declarado); defaults en `meta_labeling/study.py` (`LabelCosts`); motor cobra giro largo→corto como 2 unidades de nocional (`backtesting/engine.py`) | — |
| ¿Conservador o generoso? Realista en fee (taker Binance), ligeramente generoso en slippage para tamaños no triviales | Media (declarativa) | La batería lo cubre: stress 2× fee y 2× slippage en `evaluation/study_robustness.py` (`cost_stress_2x`), y la erosión por bps está medida y publicada (`reports/tables/backtest/t02_cost_sensitivity.*`) | 0 — ya mitigado; solo declararlo en la memoria |
| Funding nunca se supone cero en silencio | OK | `require_funding` hace fallar el motor si falta la serie (`search/config.py`, engine) | — |

## 5. Tests

- Cobertura: 95 ficheros en `tests/unit/` + 6 en `tests/integration/`. La lógica
  crítica está cubierta: `test_multiple_testing.py`, `test_walk_forward.py`,
  `test_quality.py`, `test_meta_labeling.py` (en rama), causalidad de features,
  `test_search_config_families.py` (23 tests que impiden la deriva de vocabulario
  que causó el fallo CRT del 16-08).
- Rotos conocidos: 7 tests de `/guia` en `apps/web` (mock de router pendiente;
  decisión previa: arreglar mockeando, nunca tocando `Sidebar.tsx`).
- **El primer test que escribiría**: uno que fije que `run_identity` es invariante
  ante cambios fuera de `RELEVANT_DIRS` — crear repo temporal, computar huella,
  tocar `apps/web/x.tsx` y un `docs/foo.md`, verificar huella idéntica; tocar
  `src/x.py`, verificar que cambia. Es el test del hallazgo crítico #3 y el que
  habría ahorrado ~23 unidades de cómputo el 17-08.

## 6. Estructura de carpetas

Propuesta concreta con comandos en `03_reorganizacion_propuesta.md`. Resumen: el
árbol ya es legible; los cambios valiosos son quirúrgicos (raíz, `apps/api`,
`docs/roadmap.md`), no una reorganización general, que además invalidaría huellas
de identidad de futuros runs y ensuciaría `git blame` sin ganancia para el tribunal.

## 7. Estilo de código

- Idioma: ya es inglés en los 154 ficheros de `src/perp_lab/` (verificado por
  tokenizer el 18-08: cero comentarios en español). El encargo pedía traducir; no
  hay nada que traducir.
- La pasada de estilo pedida (menos comentarios narrativos, sin banners, POR QUÉ
  en vez de QUÉ) está hecha para `validation/` y `search/` en la rama
  `style/comment-pass` (commits `ac84f44`, `7fdb741`), con garantía AST verificada
  (cero cambios de lógica). Esa rama es la plantilla de estilo.
- Ficheros que más se alejan del estilo objetivo (pendientes de la misma pasada,
  por orden de valor para la memoria): `src/perp_lab/backtesting/engine.py`,
  `src/perp_lab/features/{spec,registry,causal}.py`,
  `src/perp_lab/evaluation/{multiple_testing,study_robustness}.py`,
  `src/perp_lab/crt/strategies.py`. Ninguno tiene banners decorativos graves
  (solo quedaba uno en `search/registry.py`, ya retirado en la rama); el patrón a
  limpiar es docstring-que-repite-firma y comentarios de sección.
- Los notebooks generados tienen el problema inverso: prosa en inglés y plantilla
  repetitiva («Interpretation (2.1)») impuesta por `.cursor/rules/notebook-policy.mdc`.
  El plan de reescritura (bilingüe con la memoria, tono humano) está aprobado en
  sesión y pendiente de ejecutar; ver Bloque B3.
