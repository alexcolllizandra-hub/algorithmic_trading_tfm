# Capítulo 8 — Conclusiones

Este capítulo cierra el arco experimental del TFM a partir de los capítulos 6–7,
los ADRs de gates R1–R3 y el extracto R3 fusionado. No reabre experimentos ni
el holdout.

**Marco de preguntas.** Las preguntas de investigación (RQ1–RQ5) y las hipótesis
(H1–H5) están definidas en
[experimental_design.md](../methodology/experimental_design.md) y trazadas en
[hypothesis_matrix.md](../methodology/hypothesis_matrix.md).

---

## 8.1 Respuesta al objetivo general

El objetivo operativo del Capítulo 5 metodológico es **descubrir y validar
estrategias interpretables** en futuros perpetuos BTCUSDT y ETHUSDT USDT-M bajo
un contrato temporal estricto, costes explícitos y trazabilidad reproducible
([experimental_design.md](../methodology/experimental_design.md)).

**Conclusión.** Bajo el contrato ejecutado — protocolo corregido (R1), baseline
re-estimado (R2), evaluación de cinco familias (R3), R4 no aplicado por ausencia
de promovidas, holdout cerrado — **no se identificó ninguna estrategia
interpretable promocionable** en la partición de desarrollo analizada. El TFM sí
entrega una **contribución metodológica, empírica y de ingeniería reproducible**:
detección y corrección de contaminación temporal, criterios de promoción
documentados, evidencia negativa auditable y un pipeline versionado.

El resultado negativo **no demuestra** que sea imposible obtener alpha en estos
mercados; **delimita** lo que no quedó respaldado bajo este diseño, periodo,
activos, frecuencia y batería de criterios.

---

## 8.2 Respuesta a objetivos específicos y preguntas de investigación

### Tabla 8.1 — Trazabilidad objetivos / preguntas → evidencia → conclusión

| Objetivo o pregunta | Evidencia | Conclusión |
|---|---|---|
| **Objetivo general** — validar estrategias interpretables neto de costes en desarrollo | R1–R3; [cap. 6](capitulo_06_resultados.md); ADR 0012, 0013, 0015; [thesis_report](../../reports/r3_gate/r3_full_budget100_ga21/thesis_report.json) | **No promocionable** bajo el contrato; contribución metodológica positiva |
| **RQ1** — ¿Rentabilidad OOS neto de costes de familias interpretables? | ADR 0013 (momentum 0/40); R3 0/5 familias; tabla 6.1 | **No** en momentum ni en las cinco familias evaluadas |
| **RQ2** — ¿GA supera a RS a igual presupuesto? | ADR 0013: GA−RS = −0,061, IC [−0,399 ; +0,277]; R3: GA no decide promoción | **Sin evidencia de superioridad sistemática del GA** |
| **RQ3** — ¿Meta-labeling mejora señales base? | Sin implementación M1/M2; [scientific_questions.md](../roadmap/scientific_questions.md) H3 «Not started» | **No evaluada** en este TFM |
| **RQ4** — ¿Dependencia del rendimiento respecto al régimen de volatilidad? | R4 SKIPPED; modelos de régimen existen pero gate confirmatorio no ejecutado | **No respondida** como gate; fuera del arco cerrado |
| **RQ5** — ¿Robustez ante perturbaciones de costes y parámetros? | Batería parcial en R3 (C2–C5: bootstrap, costes 2×, drop-top-5); R4 SKIPPED | **Parcialmente abordada** en R3; **no** confirma H5 (requiere estrategia promovida) |
| **H1** — Al menos una familia con Sharpe OOS neto > 0 (mayoría de pliegues) | ADR 0013; ADR 0015; 0/5 promociones | **Rechazada** en el alcance ejecutado |
| **H2** — GA con mayor fitness OOS mediano que RS | ADR 0013 (protocolo limpio) | **Sin evidencia** de ventaja GA |
| **H3** — Meta-labeling mejora señales base | Gates M1/M2 no iniciados; sin experimento RQ3 | **No evaluada** |
| **H4** — Rendimiento difiere por régimen de volatilidad | EDA de regímenes descriptivo (Cap. 3); R4 SKIPPED | **No contrastada confirmatoriamente** |
| **H5** — Estrategias promovidas sobreviven batería extendida | 0 promociones R3; R4 SKIPPED | **No evaluable** (ninguna estrategia promovida) |
| **Gate R1** — validez temporal por pliegue | ADR 0012; [phase_gates § R1](../roadmap/phase_gates.md) | **Cumplido** — contaminación corregida |
| **Gate R2** — momentum y RS–GA bajo protocolo limpio | ADR 0013 | **Momentum rechazado**; RS–GA inconcluso a favor de GA |
| **Gate R3** — promoción familiar | ADR 0015; thesis_report | **CLOSED_NEGATIVE**, **0/5** |
| **volatility_breakout / BTC** | thesis_report; ADR 0015 | **Señal parcial no robusta** (6/10 C1); **no** estrategia aprobada |
| **Gate R4** | ADR 0015; phase_gates § R4 | **SKIPPED** — conforme al protocolo |
| **Holdout** | ADR 0003; thesis_report `reporter_holdout_accessed: false` | **Permanece cerrado** — sin candidato congelado |

---

## 8.3 Contribuciones principales

### Metodológica

- Identificación y corrección documentada de **contaminación por pliegue externo**
  en la búsqueda de candidatos ([ADR 0012](../decisions/0012-outer-fold-contamination-in-candidate-search.md)).
- Contrato de promoción R3 con **seis criterios** más **veto separado** de trades
  mínimos; motor confirmatorio RS y GA como diagnóstico.
- Gates R1–R4 con criterios de avance/rechazo explícitos
  ([phase_gates.md](../roadmap/phase_gates.md)).

### Empírica

- Re-baseline de momentum bajo protocolo limpio: **0/40** combinaciones positivas
  (ADR 0013).
- Evaluación homogénea de **cinco familias**, **100/100** unidades, veredicto
  **0/5** promociones (ADR 0015).
- Registro honesto de **volatility_breakout/BTC** como señal parcial no robusta,
  no como promoción.

### Ingeniería y reproducibilidad

- Pipeline versionado (datos, features causales, backtester, búsqueda, tracking)
  con tests offline y reporter R3 de solo lectura sobre artefactos persistidos.
- Identidades de run, manifiestos y extracto
  [thesis_report](../../reports/r3_gate/r3_full_budget100_ga21/thesis_report.md)
  con trazabilidad reporter_verified vs documentary.

---

## 8.4 Limitaciones

- **Activos:** solo BTCUSDT y ETHUSDT; perpetuos USDT-M; no generalizable a otros
  subyacentes o venues sin nuevo diseño.
- **Frecuencia y periodo:** barras **1h**; desarrollo hasta 2025-12-31; OOS de
  estudios hasta 2025-12-09; holdout `[2026-01-01, 2026-07-01)` **no utilizado**
  por ausencia de candidato promovido ([ADR 0003](../decisions/0003-cutoff-and-holdout-window.md)).
- **Costes:** supuestos provisionales documentados ([ADR 0005](../decisions/0005-provisional-transaction-costs.md));
  estrés 2× incluido en criterios, no agota microestructura real.
- **Sobreajuste en desarrollo:** quince pliegues × diez semillas × cinco familias
  implican múltiples comparaciones; los criterios mitigan pero no sustituyen
  holdout final.
- **Procedencia R3:** *worktrees* dirty y
  `reproducible_from_commit_alone=false` limitan reconstrucción exacta del código;
  **no invalida** la coherencia numérica verificada entre JSON persistidos
  (cap. 6.7).
- **Alcance incompleto:** RQ3, R4 como gate confirmatorio y **RQ5 extendida**
  (perturbación de parámetros sobre promovidas) quedan fuera del cierre ejecutado.
  La robustez parcial aplicada en R3 (criterios C2–C5) **no sustituye** la
  confirmación de H5.

---

## 8.5 Líneas futuras

- **Gate S1:** nuevas hipótesis y familias solo como fase **independiente y
  preespecificada**, con motivación escrita antes del código; **sin** rescatar
  retrospectivamente familias rechazadas en R3
  ([phase_gates § S1](../roadmap/phase_gates.md)).
- **M1/M2:** meta-labeling y filtros ML únicamente bajo contrato explícito, no como
  sustituto de la fase interpretable cerrada.
- **Ampliación:** otros activos, periodos o frecuencias requieren nuevo contrato
  de datos y gates.
- **Holdout:** apertura **única** y **solo** con estrategia congelada antes del
  acceso; condición no satisfecha en este TFM.

---

## 8.6 Conclusión final

Este trabajo demuestra que un pipeline exigente de descubrimiento y validación
puede **cerrarse con un resultado negativo riguroso** en lugar de una conclusión
positiva frágil. R1 restauró la validez temporal; R2 rechazó momentum; R3 evaluó
cinco familias con **cero promociones**; R4 quedó **SKIPPED**; el holdout sigue
cerrado. No se demostró superioridad sistemática del GA frente a Random Search.
**volatility_breakout/BTC** mostró una señal parcial no robusta, **no** una
estrategia aprobada.

La aportación del TFM es, por tanto, **metodológica, empírica y de
reproducibilidad**: un marco auditable para preguntas sobre alpha interpretable en
perpetuos cripto, con evidencia registrada de lo que **no** superó el umbral de
promoción bajo el contrato acordado — un resultado científico válido en un Máster
en Ciencia de Datos.
