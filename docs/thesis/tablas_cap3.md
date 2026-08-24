# Capítulo 3 — Tablas 3.1, 3.2 y 3.3

Todos los valores están verificados contra el repositorio; cada fila cita su
fuente. Ningún número de este documento es una estimación.

---

## Tabla 3.1 — Contratos de datos congelados

**Fuente:** `configs/data_contract.yaml` (v0.1.0) y los manifiestos de
`data/manifests/*.json` (recuentos de filas y SHA-256).

| Elemento | Especificación | Fuente |
|---|---|---|
| Exchange / mercado | Binance, USDⓈ-M (linear) perpetual futures | `data_contract.yaml: exchange, market_type` |
| Símbolos | BTCUSDT (listing 2019-09-08), ETHUSDT (listing 2019-11-27) | `data_contract.yaml: symbols` |
| Granularidad base | 5 minutos (descarga masiva desde `data.binance.vision`) | `base_timeframe: "5m"` |
| Granularidades derivadas | 15 m y 1 h, **construidas** por agregación causal desde las barras de 5 m y contrastadas contra las klines nativas en QC | `derived_timeframes: ["15m", "1h"]` |
| Series auxiliares | `fundingRate` (evento nominal cada 8 h), `markPriceKlines` | `aux_streams` |
| Exclusión declarada | `openInterest` queda fuera: solo disponible por REST para historia reciente, no en el archivo masivo | comentario en `aux_streams` |
| Ventana de desarrollo | 2020-01-01 → 2025-12-31 · **52 608 barras de 1 h por símbolo** (683 424 de 5 m) | manifiestos `*_klines_1h_development` |
| Partición final | 2026-01-01 → 2026-06-30 · **4 344 barras de 1 h por símbolo** | `holdout: {months: 6, start: "2026-01-01"}` |
| Corte global | 2026-07-01 (exclusivo): solo se ingieren meses cerrados | `cutoff_date` |
| Eventos de funding | 7 119 por símbolo en el rango completo (6 576 dentro de desarrollo) | manifiestos `*_fundingRate` |
| Garantía de integridad | Manifiesto por dataset con origen, símbolo, periodo, nº de filas y SHA-256; validación de esquema (huecos, duplicados, OHLC imposible, volumen negativo) | `data/manifests/`, `validation/schemas` |
| Inmutabilidad | `data/raw` de solo lectura; toda corrección vive en una copia derivada | ADR de contrato + `Paths.raw_dir` |

> Nota de reproducibilidad citable en el texto: el 2026-08-19 la carpeta
> `data/` se vació accidentalmente y la re-descarga completa desde
> `data.binance.vision` reprodujo **cada dataset con idéntico SHA-256** (p. ej.
> ETHUSDT 1 h desarrollo `8c2b03db…6917`), verificando el contrato de extremo a
> extremo.

---

## Tabla 3.2 — Criterios de promoción y señal parcial

**Fuente:** `src/perp_lab/evaluation/study_robustness.py`
(`PROMOTION_TESTS`, `REJECTION_TESTS`, `_majority_required`,
`R3_DROP_TOP_K = 5`, `R3_MIN_OOS_TRADES = 5`, `R3_PRIMARY_ENGINE =
"random_search"`) y la tabla congelada
`reports/tables/closure/t02_promotion_criteria.md`.

Regla de agregación: cada criterio se evalúa **por celda familia × activo**
sobre las 10 semillas, y se considera cumplido si lo superan **≥ 6 de 10
semillas** (mayoría simple, `n//2 + 1`). Una familia se promociona **solo si
los seis criterios se cumplen simultáneamente**.

| # | Criterio | Clave en el código | Definición operativa | Umbral | Cierre real (celdas de 10 que lo cumplen) |
|---|---|---|---|---|---|
| C1 | Retorno total positivo | `positive_total_return` | Retorno compuesto neto OOS > 0 | ≥ 6/10 semillas | **1 / 10** (9% de semillas) |
| C2 | IC bootstrap del Sharpe excluye cero | `bootstrap_sharpe_ci_excludes_zero` | Bootstrap estacionario del Sharpe OOS; el IC no contiene 0 | ≥ 6/10 semillas | **0 / 10** (0%) |
| C3 | Sobrevive al doble de costes | `survives_double_costs` | Re-precio del ledger con comisión y deslizamiento ×2; retorno sigue > 0 | ≥ 6/10 semillas | **0 / 10** (5%) |
| C4 | Bate a comprar y mantener | `beats_buy_and_hold` | Retorno OOS > B&H sobre exactamente las mismas barras y costes | ≥ 6/10 semillas | **0 / 10** (4%) |
| C5 | No depende de pocas operaciones | `survives_drop_top_trades` | Eliminando las **5** mejores operaciones (`R3_DROP_TOP_K`) el retorno sigue > 0; exige ≥ **5** operaciones OOS (`R3_MIN_OOS_TRADES`) | ≥ 6/10 semillas | **0 / 10** (0%) |
| C6 | No confinado a un pliegue | `not_confined_to_one_fold` | La ganancia no se concentra en un único pliegue walk-forward | ≥ 6/10 semillas | **10 / 10** (94%) |

**Criterios de rechazo** (`REJECTION_TESTS`, disparan veredicto negativo
explícito): `zero_seeds_positive`, `no_bootstrap_ci_excludes_zero`,
`zero_seeds_survive_double_costs`, `depends_on_few_trades`,
`confined_to_one_fold`.

**Señal parcial.** Configuración que cumple un subconjunto estricto de C1–C6.
Se registra y se reporta, pero no desbloquea nada. Ejemplo del estudio
(`docs/roadmap/phase_gates.md`, cierre R3): `volatility_breakout` BTC con
**6/10 semillas positivas** en random search pero **0/10** IC bootstrap
excluyendo cero en ninguno de los dos activos.

**Motor confirmatorio.** `random_search` es el motor primario declarado; el
algoritmo genético se reporta en paralelo con presupuesto idéntico, pero el
veredicto se lee sobre RS.

**Restricciones de fitness** (aplican durante la búsqueda, no son criterios de
promoción; `configs/experiment.yaml: fitness.constraints`, marcadas
`provisional: true`): `min_trades_total: 50`, `min_trades_per_fold: 3`,
`max_leverage: 3.0`.

---

## Tabla 3.3 — Modelo de costes

**Fuente:** `configs/experiment.yaml`, bloque `costs` (marcado
`provisional: true`) y el motor `src/perp_lab/backtesting/engine.py`.

| Componente | Parámetro | Valor | Aplicación |
|---|---|---|---|
| Comisión | `fee_model` | `taker` (supuesto conservador: se cruza el spread) | Por lado |
| | `taker_fee_bps` | **4,0 pb** (0,040%) por lado | `fee_b = turnover_b × 4/10⁴` |
| | `maker_fee_bps` | 2,0 pb (0,020%) — declarado, no usado en el estudio | — |
| Deslizamiento | `slippage.baseline_bps` | **1,0 pb** por lado, fijo sobre la apertura siguiente | `slippage_b = turnover_b × 1/10⁴` |
| | `slippage.scenarios_bps` | Barrido de robustez: **0, 1, 2, 5 pb** | Capítulo 8 |
| Funding | `funding.treatment` | `realized`: se paga/cobra el funding real en las posiciones abiertas | `funding_b = position_b × rate_in_bar_b` |
| | `funding.align` | `as_of_past`: la tasa se conoce antes de la barra en que se cobra (sin fuga) | Join backward as-of |
| Mínimo de orden | `min_notional_usdt` | 100 USDT (mínimo provisional del exchange) | — |
| Rotación | — | Un giro largo→corto mueve **dos** unidades de nocional y se cobra como dos | `turnover_b = \|pos_b − pos_{b−1}\|` |

**Coste total por vuelta completa:** 2 × (4 + 1) = **10 pb** (0,10%).

**Magnitud del funding** (medido, Sección 2.2): media de +0,0117% por evento de
8 h en BTC y +0,0140% en ETH sobre la ventana de desarrollo, es decir
**+12,8% y +15,3% anualizados en contra de un largo permanente**. El motor
falla en vez de asumir cero si un experimento exige funding y la serie no está
disponible.

**Punto de equilibrio medido** (cuaderno 07, tabla `t04_barrido_costes`): el
retorno de la mejor familia se anula al multiplicar la estructura de costes por
**×2,28**; todo su margen aparente vive por debajo de ese factor.

---

## Correcciones al borrador del capítulo 3

Tres precisiones sobre el texto enviado, todas verificadas:

**1. Purga y embargo son derivados, no constantes numéricas.** El borrador dice
«fold count, purge and embargo widths … are protocol constants». Lo que está
congelado es la **regla de derivación**, no el número:
`purge.derive_from: "max(label_horizon, max_holding)"` y el embargo
`= purge + 0,01 × ventana de test` (`configs/experiment.yaml`, ambos con
`bars: null`, calculados en tiempo de ejecución). Ahora bien, bajo la
configuración congelada de etiquetado y holding, la derivación produce
**exactamente 96 y 118 barras en las 20 familias que llegaron a ejecutarse**
(verificado sobre los `folds.json` de todos los runs). Es decir, tu frase es
empíricamente correcta y el argumento sale reforzado: los anchos no se
eligieron a ojo ni se ajustaron por familia — se derivan de una regla común y
resultan idénticos para todas. Redacción sugerida:

> …separated by a purge and an embargo whose widths are *derived* from the
> maximum label horizon and holding period rather than chosen, a rule fixed
> once in the protocol. Under the frozen labelling configuration this yields 96
> and 118 bars identically for every one of the families evaluated.

**2. Geometría walk-forward: parámetros exactos.** Esquema `expanding`
(entrenamiento anclado que crece), `initial_train_days: 730`,
`validation_days: 90`, `test_days: 90`, `step_days: 90` (ventanas OOS no
solapadas), `min_folds: 8`.

**3. Anualización del Sharpe.** El borrador usa A = 105 120 (barras de 5 min).
El estudio **evalúa en barras de 1 hora**, de modo que la constante efectiva es
**A = 8 760** (convención 24/7, 365 días; `backtesting/metrics.py: bars_per_year`).
Las de 5 y 15 minutos existen en el contrato de datos pero ninguna familia
evaluada opera sobre ellas. Conviene ajustar la frase para evitar una
inconsistencia que el tribunal detectaría al leer el capítulo 6.

---

## Nota 3 del autor — geometría primaria vs CSCV (confirmado)

Sí, la dualidad existe y hay que explicitarla. Verificado en el repo:

- **Geometría primaria para veredictos:** walk-forward expansivo de 15 pliegues
  (`configs/experiment.yaml: walk_forward`), con purga de 96 barras y embargo de
  118 barras derivados del periodo máximo de mantenimiento, y una constante de
  protocolo **`min_folds: 8`** (`experiment.py:1148`): por debajo de ocho
  pliegues válidos el run aborta en vez de reportar métricas.
- **CSCV solo para PBO:** la probabilidad de sobreajuste se estima con
  validación cruzada combinatoriamente simétrica
  (`evaluation/multiple_testing.py: probability_of_backtest_overfitting`), que
  particiona la matriz de rendimiento en S bloques y evalúa todas las
  combinaciones — en el cierre, **70 particiones**. No sustituye a la geometría
  temporal: es un diagnóstico sobre la matriz de resultados ya producida por
  ella.

Frase sugerida para 3.4:

> The protocol uses two distinct partitioning schemes for two distinct
> purposes: an expanding walk-forward geometry over the development window,
> which produces every reported verdict, and a combinatorially symmetric
> cross-validation (CSCV) over the resulting performance matrix, used
> exclusively to estimate the probability of backtest overfitting in Chapter 6.
> The latter never selects a configuration and never produces a performance
> figure.
