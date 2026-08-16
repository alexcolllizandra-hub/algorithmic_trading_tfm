# Capítulo 7 — Discusión

## 7.1 Lectura global del resultado negativo

El arco experimental R1–R4 responde, con protocolo explícito y artefactos
persistidos, a la pregunta de si familias interpretables derivadas del EDA
Capítulo 4 muestran ventaja neta de costes en OOS de desarrollo bajo validación
walk-forward y múltiples semillas. La respuesta consolidada es **no**: cinco
familias rechazadas, momentum previamente rechazado en R2, cero promociones y
holdout sin abrir ([ADR 0015](../decisions/0015-r3-family-evaluation-negative.md)).

Un resultado negativo obtenido **después** de corregir contaminación temporal (R1),
re-baselinear el baseline (R2) y aplicar una batería de seis criterios más veto
de liquidez operativa (R3) no equivale a «no hay efecto en absoluto», sino a
**no hay evidencia suficiente bajo el contrato experimental acordado** para
congelar una estrategia. En un TFM de Ciencia de Datos, demostrar que un pipeline
exigente no produce ventaja espuria tras corregir un fallo metodológico grave es
un **resultado científico válido** y preferible a una conclusión positiva basada
en leakage o en un único split favorable.

---

## 7.2 Validez interna

**Fortalezas.**

- Particiones estrictamente cronológicas; holdout aislado por diseño ([ADR
  0003](../decisions/0003-cutoff-and-holdout-window.md)).
- Corrección documentada de la ranking pool contaminada ([ADR
  0012](../decisions/0012-outer-fold-contamination-in-candidate-search.md)).
- Paridad de presupuesto por pliegue; auditorías de aislamiento en R2 (20/20) y
  R3 (100/100) según cierre documental.
- Promoción atribuida solo a Random Search; GA reportado como diagnóstico.
- Determinismo y trazabilidad de runs (identidades, hashes, semillas derivadas).

**Amenazas residuales.**

- **Sobreajuste dentro de OOS de desarrollo:** quince pliegues × diez semillas ×
  cinco familias implican un espacio de comparación amplio. Los criterios de
  promoción mitigan parte del riesgo (costes dobles, drop-top-5, localidad por
  pliegue), pero no sustituyen un holdout final — que aquí no procede al no haber
  promovidas.
- **Variabilidad entre pliegues y semillas:** las medianas OOS negativas en la
  mayoría de celdas, junto con C2 = 0/10 en todas las familias, indican que la
  señal, cuando aparece (p. ej. volatility_breakout BTC), no es estable en el
  tiempo ni en el muestreo bootstrap semanal.
- **Costes provisionales:** las comisiones y el slippage son supuestos
  configurables ([ADR 0005](../decisions/0005-provisional-transaction-costs.md)).
  Los criterios C3 refuerzan la conclusión bajo estrés de costes, pero no agotan
  todos los escenarios de microestructura.

La **integridad numérica** entre artefactos R3 fue verificada por el reporter
(0 discrepancias; [thesis_report.json](../../reports/r3_gate/r3_full_budget100_ga21/thesis_report.json)).
Esto es independiente de la **procedencia dirty**: dos estados tracked de diff en
`run_identity.json` impiden reconstruir el código exacto solo desde el commit, no
invalidan las tablas derivadas de los JSON de estudio ya persistidos.

---

## 7.3 Validez externa y de constructo

**Externa.** Los resultados se refieren a BTCUSDT y ETHUSDT perpetuos USDT-M en
1h, ventana de desarrollo 2020–2025 y geometría walk-forward fijada. No se
generalizan a otros venues, timeframes ni regímenes no cubiertos por el EDA
inicial.

**Constructo.** Cada familia operationaliza una hipótesis del mapa EDA → familia
([scientific_questions.md](../roadmap/scientific_questions.md)). El rechazo
indica que esas operationalizaciones concretas — no necesariamente la intuición
económica subyacente en abstracto — no generan retornos netos estables bajo la
implementación y el espacio de parámetros buscados. volatility_breakout en BTC
muestra retorno mediano OOS positivo (+6,5 %) pero **falla** criterios de
inferencia (C2), costes y comparación con B&H en la mayoría de semillas; debe
interpretarse como **señal parcial no robusta**, nunca como estrategia aprobada.

---

## 7.4 Random Search frente al algoritmo genético

En R2, con inferencia sobre quince pliegues calendario, GA − RS = −0,061 e IC 95 %
[−0,399 ; +0,277] ([ADR 0013](../decisions/0013-clean-momentum-rebaseline.md)):
**no hay evidencia de superioridad del GA**.

En R3, las comparaciones pareadas por familia son diagnósticas. Solo
mean_reversion presenta un intervalo que excluye cero a favor del GA (+0,179;
[0,012 ; 0,346]), pero el GA **no decide promoción** y la familia queda
rechazada en ambos activos con retornos medianos profundamente negativos
([thesis_report.md](../../reports/r3_gate/r3_full_budget100_ga21/thesis_report.md)).
Concluir superioridad del GA a partir de esa fila sería un error de inferencia:
el criterio de promoción no se cumple y el intervalo no fue pre-registrado como
endpoint confirmatorio principal.

Globalmente, **no hay base suficiente** para afirmar que el GA aporta ventaja
sistemática frente a RS en este contrato experimental.

---

## 7.5 Diferencias entre BTC y ETH

En R3, las medianas buy-and-hold de referencia difieren marcadamente (+52,3 %
BTC vs −21,9 % ETH en la ventana OOS agregada; fuente: thesis_report). Las
estrategias evaluadas muestran pérdidas en ambos activos en casi todas las
familias; ETH concentra los retornos OOS más negativos (p. ej. mean_reversion
−79,9 %). *Hipótesis interpretativa (no demostrada de forma aislada aquí):* la
mayor deriva alcista observada en BTC frente a ETH en la ventana OOS agregada
podría penalizar con más frecuencia estrategias direccionales con sesgo long o
poca adaptación al signo del subyacente; esta explicación no fue sometida a un
contraste causal específico en el diseño experimental.

Ninguna familia satisface el requisito de **ambos** activos simultáneamente, lo
que refuerza que los efectos observados en un solo activo (volatility_breakout BTC)
no bastan para promoción.

---

## 7.6 Costes, número de operaciones y robustez operativa

Los criterios C3 y C5 fueron diseñados para detectar estrategias frágiles a costes
y a concentración en pocas operaciones. El veto `min_oos_trades_met` (mínimo cinco
operaciones OOS) descarta configuraciones con muestras operativas demasiado
pequeñas **sin** mezclarse en la mayoría de seis criterios. En los datos
persistidos, el veto no fue el motor principal del rechazo masivo (10/10 en la
mayoría de filas); lo fueron C1, C2, C4 y retornos medianos negativos.

---

## 7.7 Por qué no ejecutar R4

R4 es un gate **confirmatorio** sobre familias ya promovidas: perturbación de
parámetros, desglose por régimen y bootstrap de trayectoria. Sin promovidas, ejecutar
R4 como continuación del arco R3 sería **re-interpretar familias rechazadas** y
arriesgar un «rescate» retrospectivo prohibido por el protocolo ([phase_gates.md §
R4](../roadmap/phase_gates.md)). Por ello R4 queda **SKIPPED** con `r4_required:
false` en el veredicto de cierre ([ADR 0015](../decisions/0015-r3-family-evaluation-negative.md)).

La armonización documental posterior del alcance «solo promovidas» no convierte
R4 en ejecutado; es una aclaración **documental** posterior al cierre.

---

## 7.8 Trabajo futuro: fase S1

Cualquier nueva hipótesis o familia debe abrirse como **Gate S1 — expansión
controlada de estrategias**: motivación escrita antes del código, grados de
libertad cuantificados, regla de promoción fijada de antemano y paso obligatorio
por los criterios de R3 ([phase_gates.md § S1](../roadmap/phase_gates.md)). **No**
debe plantearse como continuación retrospectiva de las familias ya rechazadas en
R3 ni como re-búsqueda hasta obtener un p-valor favorable.

Líneas plausibles (no ejecutadas en este TFM):

- Mecanismos con motivación EDA independiente y presupuesto de validación
  explícito.
- Meta-labeling o filtros ML solo tras contrato M1/M2, no como sustituto de la
  fase interpretable actual.
- Apertura única del holdout **solo** si existiera un candidato congelado antes
  del acceso — condición no satisfecha.

---

## 7.9 Conclusión de la discusión

Este TFM entrega un pipeline reproducible y un arco R1–R4 cerrado con evidencia
negativa coherente: corrección temporal, baseline descartado, cinco familias
rechazadas, R4 no ejecutado y ninguna cifra procedente del holdout. La
contribución metodológica —
detectar y corregir contaminación por pliegue, fijar criterios de promoción
estrictos y reportar el fracaso con trazabilidad — tiene valor independiente del
signo del alpha. La memoria puede afirmar, con respaldo en artefactos, que **bajo
el contrato experimental descrito no se identificó una estrategia interpretable
promotable** en BTC/ETH perpetuos en la fase de desarrollo analizada.
