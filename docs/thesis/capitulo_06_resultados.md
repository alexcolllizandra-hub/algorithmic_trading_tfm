# Capítulo 6 — Resultados

## 6.1 Marco temporal y holdout

El contrato de datos fija un **holdout congelado** en el intervalo
`[2026-01-01 00:00 UTC, 2026-07-01)` y un conjunto de desarrollo estrictamente
anterior a esa fecha ([ADR 0003](../decisions/0003-cutoff-and-holdout-window.md)).
Las fases **ejecutadas** R1–R3 utilizaron exclusivamente la partición de
desarrollo; R4 quedó **SKIPPED** conforme al protocolo y no se ejecutó como gate
confirmatorio. El holdout no se abrió para EDA orientada a diseño, selección de
estrategias ni ajuste de hiperparámetros.

> **Estado posterior al cierre de R1–R4 (nota del 2026-08-16).** El 2026-08-13 la
> partición se abrió una vez, fuera del arco R1–R4, sobre `volatility_breakout`
> —la familia que R3 ya había rechazado—. La lectura está retenida a la espera de
> una auditoría de procedencia y **no se cita en ningún punto de este capítulo**;
> ninguna cifra de aquí procede de ella. La consecuencia relevante para el
> trabajo futuro es que la partición queda **consumida**: no existe ya una prueba
> confirmatoria limpia sobre este histórico. Véase
> [holdout_audit_status.md](../methodology/holdout_audit_status.md).

La validación temporal principal es **walk-forward** con quince pliegues externos
cronológicos. Tras la corrección de R1, la búsqueda de candidatos es
**independiente por pliegue externo**: cada pliegue selecciona su ganador usando
únicamente la ventana de validación de ese pliegue, congela el candidato y evalúa
el test **una sola vez** ([ADR 0012](../decisions/0012-outer-fold-contamination-in-candidate-search.md)).
Las ventanas OOS de los estudios R2 y R3 terminan como máximo el
`2025-12-09 22:00 UTC`, por debajo del inicio del holdout
(documentado en el cierre R3; ver
[ADR 0015](../decisions/0015-r3-family-evaluation-negative.md)).

**Motor confirmatorio de promoción:** Random Search (RS). El algoritmo genético
(GA) se mantiene como **diagnóstico secundario** y no decide la promoción familiar
([extracto R3](../../reports/r3_gate/r3_full_budget100_ga21/thesis_report.md)).

---

## 6.2 Gate R1 — Restauración de la validez temporal

**Objetivo.** Garantizar que la selección de candidatos en un pliegue externo no
utilice información de pliegues cronológicamente posteriores.

**Evidencia principal.**

| Elemento | Fuente |
|---|---|
| Decisión de protocolo y argumento de contaminación | [ADR 0012](../decisions/0012-outer-fold-contamination-in-candidate-search.md) |
| Criterios de cierre del gate | [phase_gates.md § R1](../roadmap/phase_gates.md#gate-r1--restore-temporal-validity--passed-2026-08-09) |
| Tests de aislamiento por pliegue | `tests/unit/test_search_fold_isolation.py` |
| Piloto real con protocolo corregido | `artifacts/runs/search_momentum_20260809T085829Z_c28e3b` |
| Medición de coste del nuevo protocolo | `scripts/benchmark_protocol_cost.py`, `reports/tables/protocol_cost.json` |

**Resultado.** R1 **aprobado** el 2026-08-09. Los tests demuestran que un
candidato evaluado en el pliegue *A* no cambia cuando se alteran datos del pliegue
*B*, que el ganador de test se evalúa exactamente una vez por pliegue y que la
paridad de presupuesto se mantiene **por pliegue** para RS y GA. El piloto real
alcanzó 60 evaluaciones por motor y pliegue en quince pliegues; el coste medido
fue ~1,00× en backtests y ~1,18× en tiempo de pared, no el factor ~15× temido
inicialmente ([phase_gates.md](../roadmap/phase_gates.md)).

**Consecuencia.** Ningún experimento posterior (R2–R3) se interpreta bajo el
protocolo contaminado. Los estudios previos quedan marcados como **supersedidos**
como evidencia inferencial, no borrados (`SUPERSEDED.json` en runs antiguos).

---

## 6.3 Gate R2 — Re-baseline de momentum y comparación RS–GA

**Objetivo.** Re-estimar el baseline de momentum y la comparación RS–GA bajo el
protocolo corregido de R1.

**Diseño.** Estudio `multiseed_momentum_r2_clean_v2`: BTCUSDT y ETHUSDT; diez
semillas derivadas de la semilla base 42; quince pliegues externos; **300**
evaluaciones únicas por pliegue y motor (4 500 por motor y unidad); veinte
unidades activo×semilla; inferencia sobre **quince pliegues calendario** tras
promediar semillas y luego activos dentro de cada pliegue
([ADR 0013](../decisions/0013-clean-momentum-rebaseline.md)).

**Resultados — momentum (Random Search y GA).**

| Activo / motor | Semillas positivas | Supera B&H | Sobrevive 2× costes | IC bootstrap Sharpe > 0 | Mediana retorno OOS |
|---|---:|---:|---:|---:|---:|
| BTCUSDT / RS | 0 / 10 | 0 / 10 | 0 / 10 | 0 / 10 | −35,0 % |
| BTCUSDT / GA | 0 / 10 | 0 / 10 | 0 / 10 | 0 / 10 | −45,5 % |
| ETHUSDT / RS | 0 / 10 | 0 / 10 | 0 / 10 | 0 / 10 | −47,5 % |
| ETHUSDT / GA | 0 / 10 | 0 / 10 | 0 / 10 | 0 / 10 | −50,7 % |

*Fuente: [ADR 0013](../decisions/0013-clean-momentum-rebaseline.md), tabla
«Results — Momentum».*

Las cuarenta combinaciones activo×semilla×motor pierden dinero en OOS. **Momentum
queda rechazado** y no se reajusta retrospectivamente.

**Resultados — comparación RS vs GA (secundaria inferencial).**

| Magnitud | Valor | Fuente |
|---|---:|---|
| Media pareada GA − RS | −0,061 | ADR 0013 |
| IC 95 % | [−0,399 ; +0,277] | ADR 0013 |
| Cohen's d_z | −0,100 | ADR 0013 |
| Pliegues a favor GA / RS / empates | 5 / 9 / 1 | ADR 0013 |

El intervalo incluye cero: **no hay evidencia de superioridad del GA** bajo el
protocolo limpio. La expectativa pre-registrada se cumple: el antiguo +0,183
(bajo protocolo contaminado) se desplaza hacia cero y ligeramente negativo.

**Consecuencia.** R2 **aprobado** el 2026-08-09. El baseline queda descartado antes
de evaluar familias adicionales en R3.

---

## 6.4 Gate R3 — Evaluación de las cinco familias

**Objetivo.** Dar a cada familia implementada una audiencia comparable bajo el
mismo protocolo temporal y de costes.

**Diseño.** Cinco familias en orden congelado: breakout, mean_reversion,
volatility_breakout, funding, BTC_ETH_confirmation. Por familia: 2 activos × 10
semillas × 15 pliegues; presupuesto **100** evaluaciones únicas por pliegue y
motor ([ADR 0014](../decisions/0014-r3-budget-bounded-by-search-space.md));
raíz de estudio `artifacts/runs/r3_full_budget100_ga21/`. Cierre:
`CLOSED_NEGATIVE`, **0 promociones**, **5 rechazos**
([ADR 0015](../decisions/0015-r3-family-evaluation-negative.md);
`r3_gate_verdict.json`).

**Criterios de promoción (RS, ambos activos).** Seis criterios con mayoría
≥6/10 semillas por activo: (C1) retorno total positivo; (C2) IC bootstrap del
Sharpe excluye cero; (C3) sobrevive al doble de costes; (C4) supera
buy-and-hold; (C5) sobrevive al eliminar las cinco mejores operaciones; (C6) no
confinado a un solo pliegue. **`min_oos_trades_met` es un veto separado**
(mínimo cinco operaciones OOS por semilla), no un séptimo criterio de promoción
([phase_gates.md § R3](../roadmap/phase_gates.md);
[thesis_report.md](../../reports/r3_gate/r3_full_budget100_ga21/thesis_report.md)).

**Ejecución verificada.** 100/100 unidades completadas; auditoría documental de
aislamiento en cierre: 100/100 auditadas, 0 fallos
(`r3_scientific_closure_report.json`, citado como **documentary** en el extracto
R3). El reporter de tesis no reabrió el holdout (`reporter_holdout_accessed:
false`).

### Tabla 6.1 — Resumen por familia y activo (Random Search)

| Familia | Activo | C1 | C2 | C3 | C4 | C5 | C6 | Veto min. trades | Med. ret. OOS | Med. Sharpe OOS | Med. B&H | Veredicto |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| breakout | BTC | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 10/10 | 10/10 | −15,8 % | −0,73 | +52,3 % | RECHAZADA |
| breakout | ETH | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 10/10 | 10/10 | −25,5 % | −1,05 | −21,9 % | RECHAZADA |
| mean_reversion | BTC | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 10/10 | 10/10 | −60,0 % | −0,50 | +52,3 % | RECHAZADA |
| mean_reversion | ETH | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 10/10 | 10/10 | −79,9 % | −0,89 | −21,9 % | RECHAZADA |
| volatility_breakout | BTC | 6/10 | 0/10 | 3/10 | 2/10 | 0/10 | 6/10 | 10/10 | +6,5 % | 0,22 | +52,3 % | RECHAZADA* |
| volatility_breakout | ETH | 1/10 | 0/10 | 1/10 | 1/10 | 0/10 | 9/10 | 10/10 | −73,5 % | −0,66 | −21,9 % | RECHAZADA |
| funding | BTC | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 10/10 | 10/10 | −40,9 % | −0,27 | +52,3 % | RECHAZADA |
| funding | ETH | 1/10 | 0/10 | 1/10 | 1/10 | 0/10 | 10/10 | 10/10 | −59,9 % | −0,32 | −21,9 % | RECHAZADA |
| BTC_ETH_confirmation | BTC | 1/10 | 0/10 | 0/10 | 0/10 | 0/10 | 9/10 | 10/10 | −65,8 % | −0,55 | +52,3 % | RECHAZADA |
| BTC_ETH_confirmation | ETH | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 10/10 | 10/10 | −68,3 % | −0,30 | −21,9 % | RECHAZADA |

*Fuente: [thesis_report.md](../../reports/r3_gate/r3_full_budget100_ga21/thesis_report.md)
(reporter_verified contra artefactos en `artifacts/runs/r3_full_budget100_ga21/`).*

\* **volatility_breakout / BTC:** señal parcial no robusta (6/10 semillas con C1
positivo), **no elegible para promoción**. En ningún activo alcanzó 0/10 semillas
con IC bootstrap del Sharpe excluyendo cero; falló costes, B&H y robustez de
operaciones en la mayoría de semillas. **No constituye una estrategia aprobada.**

**Patrones comunes de fallo (R3).**

1. C2 = 0/10 en todos los activos y familias (IC bootstrap nunca excluye cero).
2. Retorno mediano OOS negativo en al menos un activo por familia.
3. Ninguna familia supera B&H en mayoría de semillas en **ambos** activos.

**Diagnóstico RS–GA (no decisorio).** Ninguna familia muestra evidencia
confirmatoria de superioridad del GA sobre RS en promoción; la fila de
mean_reversion registra GA − RS = +0,179 con IC [+0,012 ; +0,346] como evidencia
OOS de desarrollo **secundaria**, sin implicación holdout
([thesis_report.md](../../reports/r3_gate/r3_full_budget100_ga21/thesis_report.md)).

**Consecuencia.** La pregunta de R3 — ¿alguna familia muestra un efecto que
sobreviva múltiples semillas en ambos activos? — se responde **no**, con
evidencia registrada. No hay candidato congelado para evaluación holdout.

---

## 6.5 Gate R4 — Robustez extendida

**Estado:** **SKIPPED** — **no ejecutado** como gate confirmatorio.

R4 exige al menos una familia **promovida** en R3. Al cerrar R3 con cero
promociones, la batería extendida (perturbación de parámetros, métricas por
régimen, bootstrap de la trayectoria de operaciones) **no se aplicó** a ningún
candidato ([phase_gates.md § R4](../roadmap/phase_gates.md);
[ADR 0015](../decisions/0015-r3-family-evaluation-negative.md)). El campo
`r4_required` en el veredicto de cierre es `false` (reporter_verified); el
estado de aplicación documental es «SKIPPED»
([thesis_report.md](../../reports/r3_gate/r3_full_budget100_ga21/thesis_report.md)).

La maquinaria de R4 permanece implementada en el código con fines metodológicos,
pero **no altera** el veredicto R3.

---

## 6.6 Tabla 6.2 — Síntesis de gates R1–R4

| Gate | Pregunta | Evidencia principal | Resultado | Consecuencia |
|---|---|---|---|---|
| **R1** | ¿La búsqueda por pliegue es temporalmente válida? | ADR 0012; tests aislamiento; piloto `search_momentum_20260809T085829Z_c28e3b` | **PASSED** | Protocolo limpio para R2–R3 |
| **R2** | ¿Momentum y RS–GA sobreviven sin contaminación? | ADR 0013; `multiseed_momentum_r2_clean_v2` | **PASSED** (resultado negativo) | Momentum **rechazado**; GA no superior |
| **R3** | ¿Alguna familia se promueve? | ADR 0015; `r3_full_budget100_ga21`; [thesis_report](../../reports/r3_gate/r3_full_budget100_ga21/thesis_report.json) | **CLOSED_NEGATIVE** (0/5) | Sin candidato holdout |
| **R4** | ¿Robustez extendida de promovidas? | phase_gates § R4; ADR 0015 | **SKIPPED** | No ejecutado; R3 cierra el arco |

---

## 6.7 Procedencia y limitaciones de reconstrucción

Los cinco estudios R3 registran *worktrees* sucios y
`reproducible_from_commit_alone=false` en dos estados tracked distintos derivados
de `run_identity.json` (cuatro familias comparten un diff; BTC_ETH_confirmation
otro). No se retuvieron bytes de parche en los artefactos persistidos. Esta
limitación afecta a la **reconstrucción exacta del código ejecutado**, no a la
**coherencia numérica** verificada por el reporter R3 entre ejecución, rollup,
`study_robustness` y veredicto (0 discrepancias)
([thesis_report.md § Provenance limitation](../../reports/r3_gate/r3_full_budget100_ga21/thesis_report.md)).

---

## 6.8 Síntesis del capítulo

Bajo un protocolo temporal corregido, un baseline de momentum rechazado y un
presupuesto de búsqueda homogéneo, **ninguna** de las cinco familias evaluadas
cumple los criterios pre-especificados de promoción en ambos activos. Ninguna
cifra de este capítulo procede del holdout: el arco R1–R4 se resolvió entero en
desarrollo, y la apertura posterior de la partición (§6.1) no lo altera. R4 no
añade evidencia porque no hubo promovidas. El resultado
global del arco R1–R4 es **negativo pero auditable**, apto para reportarse como
hallazgo principal del TFM.
