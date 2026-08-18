# Capítulo 7 — Limitaciones y amenazas a la validez (borrador)

> Borrador escribible-ya del 2026-08-19. La regla del capítulo: cada limitación
> se enuncia con su evidencia y con lo que implicaría para la conclusión si
> resultara determinante. Ninguna se enuncia para inmunizarse de ella.

## 7.1 El incidente del holdout

La limitación más seria del estudio es de procedimiento y está registrada en
detalle en `incidente_holdout.md` y
`docs/methodology/holdout_audit_status.md`: la partición reservada
`[2026-01-01, 2026-07-01)` se abrió el 2026-08-13 sin que existiera el token de
autorización que el protocolo preveía —verificado de dos formas independientes:
la procedencia de la lectura no registra campo de autorización alguno, y el
único control operativo con ese nombre es un cerrojo de *publicación*
introducido después de la apertura
(`src/perp_lab/api/settings.py:73`, commit `4673b32`). La lectura queda
retenida y la partición, consumida.

Qué invalida y qué no: el candidato evaluado (`volatility_breakout`, BTCUSDT)
ya estaba rechazado por la corrección múltiple antes de abrir —su p bruto,
0.3455, falla incluso el umbral sin corregir—, de modo que la conclusión del
estudio no depende de esa lectura. Lo que sí se pierde, íntegro, es la
posibilidad de una prueba confirmatoria limpia sobre este histórico: ninguna
familia posterior (las CRT incluidas) puede reclamar validación final sin datos
nuevos más allá de 2026-07-01. El registro de la ronda CRT lo codifica
explícitamente (`artifacts/runs/crt_v1_budget100/crt_v1_execution.json`:
`"promotion_possible": false`).

## 7.2 Potencia estadística y exposición

El estudio no distingue «no hay efecto» de «no hay potencia para detectar un
efecto pequeño», y hay razones medidas para tomarse lo segundo en serio: las
familias de eventos operan con exposiciones bajísimas (mediana 3-13% del tiempo
en mercado; 4,2% en el caso analizado en detalle), de modo que 32.385 barras
out-of-sample se reducen a unos cientos de operaciones efectivas por unidad. Un
intervalo bootstrap del Sharpe con esa muestra es ancho por construcción. La
cuantificación formal del tamaño de efecto detectable queda pendiente
(`PENDIENTE DE EJECUTAR`: análisis de potencia sobre los ledgers de
`artifacts/runs/r3_full_budget100_ga21/`) y debe citarse en la discusión: si el
edge buscado es menor que el detectable, el negativo es en parte un problema de
potencia, y decirlo es parte de la honestidad del resultado.

## 7.3 Granularidad temporal frente al mecanismo hipotetizado

Las familias CRT hipotetizan barridos de liquidez que son sucesos *intrabar* a
1 hora. Decidir con velas horarias sobre un mecanismo sub-horario significa que
la señal solo ve los barridos que sobreviven al cierre de la vela; la
exposición observada (≈4-7%) sugiere que la mayoría de los eventos que la
propia hipótesis predice quedan fuera del alcance del detector. Es una
limitación falsable con los datos de 5 minutos ya presentes en el lake, y por
eso se traslada a trabajo futuro en lugar de usarse como excusa.

## 7.4 Concentración del resultado en pocas operaciones

En la mejor configuración observada, cinco operaciones de 153 concentran el 93%
del retorno (retorno +27,8% → +1,8% al retirarlas;
`artifacts/runs/crt_v1_budget100/pdl_reclaim_long/study_robustness.json`,
`trade_concentration`), con curtosis en exceso de ~587. La media de una
distribución así no es un resumen honesto, y el criterio de promoción
drop-top-5 existe precisamente para esto. La amenaza correspondiente —que
cualquier positivo futuro sea un accidente de cola— está mitigada por diseño,
pero la lección se enuncia: en este dominio, contar operaciones ganadoras es
menos informativo que preguntar cuánto queda al quitar las mejores.

## 7.5 Inestabilidad de la selección

Dos medidas independientes apuntan a lo mismo. A nivel de estudio, la
probabilidad de sobreajuste del backtest es 0.486 sobre 70 particiones — elegir
al mejor en muestra no predice quién será mejor fuera de ella. A nivel de
familia, los 15 folds de la ronda CRT eligieron 14 parametrizaciones ganadoras
distintas, y en la familia analizada la varianza atribuible a la semilla iguala
a la atribuible al periodo (ratio 0.94-1.00,
`crt_htf_range_reversal/headline_summary.txt`). La selección, en este espacio,
opera esencialmente sobre ruido.

## 7.6 Supuestos de coste y ejecución

Los costes (taker 4 bps + 1 bp de slippage por lado) son provisionales por
declaración (ADR 0005) y el slippage es optimista para tamaños no triviales.
Mitigación medida: stress a costes doblados en cada candidato y barrido de
erosión por bps (`reports/tables/backtest/t02`); el punto de anulación de la
mejor curva cae dentro del rango de costes reales de un exchange. El modelo
next-bar-open tampoco captura microestructura alguna (colas, impacto, fills
parciales): los resultados son cotas superiores del neto alcanzable, lo cual
reforzaría —no debilitaría— el veredicto negativo.

## 7.7 Alcance del universo

Dos activos, un exchange, seis años que contienen exactamente un ciclo completo
alcista-bajista-alcista. La generalización a otros activos, exchanges o
regímenes macro no está soportada por el diseño; la evaluación condicionada por
régimen (`reports/study_closure/regime_conditioned.json`) matiza pero no
sustituye esa limitación.

## 7.8 El denominador de pruebas es una cota inferior

El recuento congelado del cierre (13 familias; 436.092 evaluaciones válidas de
496.500 examinadas) no incluye la ronda CRT posterior ni exploraciones
manuales previas al registro. Un denominador mayor solo endurecería la
corrección: la dirección del sesgo es conocida y juega contra cualquier
positivo, no contra el negativo obtenido. La sensibilidad publicada
(13 → 496.500, sin cambio de veredicto;
`reports/study_closure/study_level_multiple_testing.json`) acota el argumento.

## 7.9 Preguntas con respuesta parcial

RQ3 (meta-etiquetado) se respondió sobre datos reales en contrato exploratorio
con 4 folds útiles de 6 —dos se descartaron por tener menos de 30 eventos— y
bloques de test de 22-48 eventos; LightGBM, preregistrado, no llegó a
ejecutarse por ausencia del backend (registrado como no disponible, no
sustituido en silencio). La respuesta obtenida (mejora económica en 4/4 folds
con ROC-AUC 0.486: toda la mejora proviene de abstenerse, no de predecir) es
consistente con el resto del estudio, pero su tamaño muestral la deja como
evidencia de dirección, no de magnitud.

## 7.10 Reproducibilidad operativa

La huella de identidad de ejecución cubre el diff del árbol completo en lugar
de restringirse a los directorios relevantes
(`src/perp_lab/tracking/identity.py:111`), lo que en la práctica costó tres
interrupciones de ronda y ~23 unidades de cómputo descartadas
(`artifacts/runs/crt_v1_budget100/_DESCARTADO_huella_arbol_sucio/POR_QUE.md`).
Es un defecto operativo —invalida administrativamente, no científicamente—,
está documentado y su corrección tiene test previsto. Se menciona porque un
lector que reproduzca el estudio tropezará con él antes que con ninguna otra
cosa de esta lista.
