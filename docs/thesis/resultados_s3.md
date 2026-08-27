# Gate S3 — resultados (macro_event_brake)

**Veredicto: NO PROMOCIÓN. Hipótesis falsificada.** Ejecutado contra la
especificación congelada (`docs/methodology/strategy_catalogue_s3.md`,
ADR 0019) sin desviaciones: 2 activos × 10 semillas × 15 pliegues, presupuesto
efectivo 100 por pliegue y motor, RS confirmatorio, costes 4+1 pb + funding
realizado. Evidencia de desarrollo; el holdout no se ha cargado.

**Artefactos:** estudio `artifacts/runs/multiseed_20260826T165028Z_0d3a92/`
(`multi_seed_analysis.json`, `study_robustness.json`, `run_identity.json`);
20 runs `search_macro_event_brake_*` con sus paquetes de evidencia completos.
Piloto previo: `s3_pilot_macro_event_brake_DEV_ONLY` (screen técnico).

## Criterios de promoción (motor confirmatorio: random search)

| Criterio | BTC (semillas que pasan / 6 requeridas) | ETH |
|---|---|---|
| C1 retorno total positivo | **0** | **0** |
| C2 IC bootstrap del Sharpe excluye 0 | **0** | **0** |
| C3 sobrevive doble coste | **0** | **0** |
| C4 bate a buy & hold | **0** | **0** |
| C5 no depende de pocas operaciones | 0 | 0 |
| C6 no confinado a un pliegue | (pasa, como en R3) | (pasa) |

0/10 semillas con Sharpe OOS positivo en las cuatro celdas activo×motor
(única excepción anecdótica: 1/10 del GA en BTC con retorno agregado +5,7%,
que el protocolo no lee — el GA es diagnóstico).

## La comparación que la spec exigía: ¿desplaza el freno la distribución del carrier?

Sharpe OOS medio entre semillas (min…max), random search:

| Celda | S3 `macro_event_brake` | R2 momentum (línea base sin freno) | Desplazamiento |
|---|---|---|---|
| BTC | **−0,99** (−1,21…−0,77), sd 0,13 | −0,71 (−1,05…−0,42), sd 0,22 | **−0,28 (peor)** |
| ETH | **−0,68** (−1,04…−0,42), sd 0,19 | −0,49 (−0,99…−0,23), sd 0,20 | **−0,19 (peor)** |

El freno de calendario no solo no mejora el carrier: la distribución completa
de semillas se desplaza **hacia abajo** en ambos activos, en más de una
desviación típica de semillas en BTC. La predicción falsable nº 2 de la spec
(«el prior honesto es no-promoción») se cumple; la lectura informativa es aún
más fuerte: **evitar las ventanas de eventos macro empeora el momentum neto**.

### Por qué es un resultado interesante y no un fracaso del anexo

El anexo descriptivo midió correctamente que las horas de CPI/FOMC concentran
2,5–3,2× la volatilidad — y también que **no tienen deriva direccional**. El
gate S3 prueba la implicación operativa y la respuesta es que esa volatilidad
de evento no era, en media, *adversa* para el carrier: quitarla recorta las
horas de mayor rango — algunas de las cuales el momentum capturaba — y añade
rotación (cada ventana obliga a cerrar y reabrir, pagando 10 pb por vuelta
completa extra cuando la señal persiste). Predictibilidad de varianza sin
predictibilidad de dirección **tampoco se monetiza en negativo** (evitándola):
exactamente la tesis del estudio, ahora con su enésima confirmación
preregistrada.

### Advertencia de comparabilidad (obligatoria al citar la tabla)

La comparación S3 vs R2 no es emparejada: el espacio S3 usa una rejilla de
carrier reducida (fast {12,24}, slow {96,168}, sin trend-filter) frente a la
rejilla completa de R2, y gasta parte del presupuesto en los parámetros del
gate. Es la comparación que la spec congeló, con esta advertencia escrita en
ella; el desplazamiento negativo es consistente en ambos activos y motores.

## Contabilidad de multiplicidad

El estudio pasa a contar **una familia más** (N := N+1) en cualquier
corrección a nivel de estudio que incluya S3. El cierre del estudio original
(0/13) no cambia; S3 se reporta como gate propio: **0/1 promocionada, sin
señal parcial** (0/10 semillas positivas no alcanza la semántica de señal
parcial de S1).
