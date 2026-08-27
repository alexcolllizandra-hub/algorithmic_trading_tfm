# Nota de aclaraciones del paquete chapter7_export

Cuatro aclaraciones solicitadas, cada una verificada contra los artefactos o
el código citados. Ninguna revela un problema que afecte a resultados; el
punto 3 documenta una trampa latente de configuración (sin efecto en los
runs ejecutados) que ya está señalada en `ch7_hypotheses_rules.md`.

## 1. Recuentos por alcance (verificados sumando `*_candidates.parquet`)

| Alcance | Evaluaciones únicas | Composición |
|---|---|---|
| **Estudios completos** | **1.080.000** | R2 180.000 + R3 300.000 + CRT v1 540.000 + S3 60.000 |
| Pilotos retenidos en el cierre | 16.500 | S1-B 3.000 (4 fam × 2 motores × 375) + S2-B 13.500 (3 fam × 2 activos × 3 semillas × 2 motores × 375) |
| **Total confirmatorio (cierre + rondas posteriores)** | **1.096.500** | 1.080.000 + 16.500 |
| Piloto S3 (screen técnico, superado por el estudio completo) | 750 | `search_macro_event_brake_20260826T164228Z_d02e91` |
| Descartadas (nunca evidencia) | 141.625 | CRT abortado/árbol sucio 93.000 (31 runs) + checkpoint S3 abandonado 18.000 + pilotos R2/R3 20.760 + desarrollo 9.244 + smoke 621 |

El cierre de 13 familias (496.500) = R2 180.000 + R3 300.000 + los 16.500 de
pilotos S1-B/S2-B; los estudios CRT y S3 (600.000) son posteriores al cierre.

## 2. Criterios de R2: qué se calculó y qué no

Los **cuatro criterios calculados** para R2 (en `per_run.tests` y en los
conteos de `by_symbol_and_engine` de
`artifacts/runs/multiseed_momentum_r2_clean_v2/study_robustness.json`) son:
`positive_total_return`, `bootstrap_sharpe_ci_excludes_zero`,
`survives_double_costs` y `beats_buy_and_hold`.

Los otros dos (`survives_drop_top_trades`, `not_confined_to_one_fold`)
**no se ejecutaron para R2** — no es un problema de exportación. Evidencia
doble: (a) el artefacto de robustez de R2 es anterior al bloque
`r3_promotion` que introdujo esos criterios (las claves del JSON de R2 son
solo `per_run`, `by_symbol_and_engine`, `method_note`); (b) el cierre tampoco
los calculó retroactivamente: en
`reports/study_closure/study_dashboard.json` las dos celdas de momentum
llevan `criteria: null`, mientras las familias R3 llevan los seis. El
rechazo de R2 se sostiene en los cuatro computados (0/10 semillas positivas
en las cuatro celdas activo×motor); los dos ausentes se citan como
"no calculado" y no al revés.

## 3. `pierce_bps` y `pivot_span`: valores efectivos, rejilla y hashes

- **Valores efectivos en todos los runs CRT**: `pierce_bps = 0.0` y
  `pivot_span = 2`. Son los defaults del motor
  (`src/perp_lab/crt/states.py:115` `InteractionConfig.pierce_bps = 0.0`;
  `src/perp_lab/crt/entries.py:137` `EntryConfig.pivot_span = 2`), porque
  `_crt_mechanics()` en `src/perp_lab/search/registry.py` no reenvía esos dos
  campos del modelo de configuración al motor.
- **Coinciden con la intención**: los defaults del modelo de configuración
  (`src/perp_lab/config/experiment.py:613` y `:624`) son exactamente 0.0 y 2,
  y `configs/experiment.yaml` no redeclara la mecánica CRT. Por tanto el
  comportamiento ejecutado es el pre-registrado; **ningún resultado queda
  afectado**.
- **No están en la rejilla buscada**: la rejilla CRT es `CrtIntradayGrid`
  (`config/experiment.py:629-636`) + los añadidos por familia; ninguna incluye
  estos campos.
- **No entran en el hash de candidato**: `SearchSpace.candidate_hash`
  (`src/perp_lab/search/space.py:326-333`) es SHA-1 de
  `familia|versión_del_espacio|JSON canónico de los parámetros activos
  buscados` — la mecánica fija no participa, así que la deduplicación y la
  paridad de presupuesto no se ven afectadas. Sí entran, como todo el config
  resuelto, en el `config_sha256` de la identidad del run
  (`run_identity.json`).
- **Trampa latente documentada**: si alguien cambiara `pierce_bps` o
  `pivot_span` en la configuración, la identidad del run cambiaría pero el
  comportamiento no (el motor seguiría en sus defaults). No ocurrió en
  ninguna ronda ejecutada; queda anotado en `ch7_hypotheses_rules.md`
  ("Known documentation gaps") como corrección pendiente de código, a hacer
  después de la entrega para no tocar huellas.

## 4. Controles de riesgo: fuentes concretas y commits reales

Fuentes que demuestran qué estaba activo/inactivo:

- **Activo** (motor, `src/perp_lab/backtesting/engine.py`, `run_backtest`):
  ejecución next-bar-open (`position = side.shift(1)`, ~L222), fee
  (`turnover * fee_bps/1e4`, ~L242), slippage siempre adverso (~L243),
  funding realizado as-of-past (~L111-125, L245).
- **Inactivo — no existe en el motor**: sizing (multiplica la posición ±1 de
  la estrategia; no hay volatility targeting ni apalancamiento), stop-loss /
  take-profit del motor, límite de trades diarios (no hay ningún contador en
  `engine.py`).
- **Config muerto** (existe, no se consume): `strategies.stop_loss_atr`,
  `take_profit_atr`, `position_sizing` (marcado provisional) y el bloque
  `risk:` de `configs/experiment.yaml:243-247`, cuyo comentario ("applied
  inside the backtester") no se corresponde con el código.
- **Risk engine CRT inactivo**: implementado y testeado en
  `src/perp_lab/crt/risk.py`, pero `FamilyMechanics.risk = None` por defecto
  (`src/perp_lab/crt/strategies.py:723`) y `_crt_mechanics()`
  (`registry.py:~881-897`) nunca pasa `risk=` → `ledger = None` → tamaño 1.0
  (`crt/strategies.py:~594`). Los únicos controles CRT activos viven en la
  estrategia: rechazo pre-entrada por R:R neto, stop/parciales/breakeven/
  time-stop/session-end (`crt/exits.py`), una posición a la vez.

Commits reales por estudio (de `checkpoint.json → meta` de cada estudio; la
identidad completa, incluidos los hashes de diff/untracked de árboles sucios,
está en cada `run_identity.json`):

| Estudio | Commit | Árbol | Huella (diff / untracked) | run_identity |
|---|---|---|---|---|
| R2 `multiseed_momentum_r2_clean_v2` | `aac33577c14c` | dirty | null / `8e7f94c9025c` | `48f61ce9fdeca881` |
| R3 `r3_full_budget100_ga21` | `aac33577c14c` | dirty | `4073dba60103` / `97ca909987a7` | `95f9192fec92173f` (breakout; una por familia) |
| CRT v1 `crt_v1_budget100` | `bcf8e6a7ff88` | **clean** | null / null | `04768d73f875ed5b` (pdl; una por familia) |
| S3 `multiseed_20260826T165028Z_0d3a92` | `de5b9d82a591` | flag dirty, sin diff/untracked bajo los directorios vigilados | null / null | `2ef073644f6569e2` |

El cierre de 13 familias se generó en el commit `232bc372`
(`study_dashboard.json → study.source_commit`). Este paquete se exporta desde
el commit `aaef166322135fe0ad5d24a1564c8d1f5ab5cd61` de `main`.
