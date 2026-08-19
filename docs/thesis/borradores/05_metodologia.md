# Capítulo 5 — Metodología (borrador)

> Borrador escribible-ya del 2026-08-19. El hilo del capítulo: cada capa del
> sistema existe para cerrar una vía concreta de autoengaño, y cada cierre es
> una propiedad ejecutable, no una promesa. Diagramas en
> `docs/methodology/pipeline_end_to_end.md`.

## 5.1 Arquitectura por capas

El sistema es un monolito modular en Python (`src/perp_lab/`), organizado como
una tubería de capas con contratos explícitos entre ellas: datos → validación →
features → estrategias → backtest → validación temporal → búsqueda → evaluación
→ registro. La regla transversal es que cada capa **falla en cerrado**: ante un
dato ausente, una columna inesperada o una petición fuera de contrato, el
sistema se detiene en lugar de continuar con un supuesto (ejemplos: funding
obligatorio en `backtesting/engine.py`; esquema estricto en
`validation/schemas.py`; `FoldIsolationError` en `search/evaluator.py`).

## 5.2 Ingeniería de características causal

Cada característica se declara —no se programa ad hoc— con sus entradas, su
ventana, su warm-up y el instante en que su valor es conocible
(`features/spec.py`, `features/registry.py`). El motor construye el frame una
sola vez y las características contextuales (funding, activo de referencia) se
incorporan con retardo explícito mediante uniones as-of hacia el pasado.

La causalidad no se argumenta: se ejecuta. La propiedad central es la
invariancia de prefijo —truncar el futuro del fichero no puede cambiar ningún
valor del pasado— y se comprueba por test sobre los datos reales, junto con un
contraejemplo deliberado: una característica con fuga plantada que los tests
deben detectar (figuras `reports/figures/features/g03`, `g04`). Distinguimos
además cuatro instantes por fila —feature_time, signal_time, execution_time,
label_time— para que «cuándo se sabe» y «cuándo se actúa» nunca se confundan
(figura `features/g09`).

## 5.3 Familias de estrategia interpretables

El espacio de hipótesis son reglas que caben en una frase: momentum, ruptura,
reversión a la media, funding, confirmación entre BTC y ETH, y las variantes de
rango/liquidez de la ronda CRT. La elección es metodológica antes que estética:
con reglas interpretables, un resultado negativo es informativo —«esta clase de
estructura no es explotable en estos datos»—, mientras que con una caja negra
no podría distinguirse «no hay señal» de «mi modelo no la encontró».

Cada familia define un espacio de parámetros tipado y finito con reparación de
combinaciones inválidas y hash canónico por candidato
(`search/space.py`), de modo que dos candidatos son «el mismo» si y solo si sus
parámetros activos canónicos coinciden — la base de la contabilidad de
evaluaciones únicas.

## 5.4 Búsqueda con presupuesto emparejado

Dos motores compiten sobre espacios, evaluador, objetivo y presupuesto
idénticos: búsqueda aleatoria y un algoritmo genético generacional con elitismo,
cruce uniforme y mutación local (`search/random_search.py`,
`search/genetic_algorithm.py`; ADR 0009). El presupuesto acota evaluaciones
únicas del objetivo, no iteraciones: los élites reutilizan fitness cacheado y
los duplicados no consumen, de modo que el GA no puede obtener más evaluaciones
que RS por construcción. Los hiperparámetros del GA son convencionales y
deliberadamente no ajustados: ajustarlos sería una segunda búsqueda apilada
sobre la primera, cuyo sesgo de selección no quedaría recogido en el recuento
de pruebas del estudio (`search/config.py`).

La corrección decisiva llegó con ADR 0012: la búsqueda corre de forma
independiente dentro de cada fold externo. Cada fold recibe su propio evaluador,
construido sobre un bundle que contiene únicamente ese fold
(`search/evaluator.py::single_fold_bundle`): el fitness de un candidato es
función de la ventana de validación de su fold y de nada más, y pedirle al
evaluador un fold ajeno lanza excepción. El defecto que esta corrección eliminó
—fitness agregado sobre todos los folds, incluidos los posteriores al que se
puntuaba— invalidó todos los resultados anteriores, que se reejecutaron
(ADR 0012, 0013). Dentro de cada fold el orden es irreversible: buscar sobre
validación, congelar el ganador con huella, puntuarlo una vez sobre test.

## 5.5 Objetivo transparente

El fitness es una combinación lineal explicable: recompensa el Sharpe de
validación y penaliza drawdown, rotación, inestabilidad intra-fold (desviación
de los Sharpe de sub-bloques contiguos de la propia ventana de validación — la
dispersión entre folds sería look-ahead bajo el protocolo por-fold) y
complejidad (parámetros activos más allá de los dos que cualquier regla
necesita). Las restricciones duras convierten al candidato en fallo explícito
con penalización determinista: métricas no finitas, operaciones insuficientes,
drawdown excesivo o funding ausente jamás se convierten en una puntuación
atractiva (`search/objective.py`).

## 5.6 Inferencia: contar cuántas veces se ha mirado

La unidad de inferencia es la celda activo × fold, con diez semillas promediadas
dentro de cada celda (ADR 0011: la variación entre semillas se midió antes de
usarse — un estudio de una sola semilla es irreproducible aquí por medida, no
por suposición). Sobre el estudio cerrado se aplican:

- **Holm-Bonferroni** (FWER) y **Benjamini-Hochberg** (FDR;
  Benjamini & Hochberg 1995) sobre los p bootstrap por familia;
- **Deflated Sharpe Ratio** (Bailey & López de Prado 2014): el Sharpe observado
  de la mejor familia se compara con el máximo esperado bajo la nula dados los
  ensayos realizados;
- **PBO por CSCV** (López de Prado & Zhu 2017) con 70 particiones;
- **Reality Check** (White 2000) y **SPA** (Hansen 2005) sobre bootstrap
  estacionario (Politis & Romano 1994), para la pregunta «¿la mejor de la
  familia bate al benchmark tras el snooping?»;
- una **sensibilidad del denominador**: el veredicto se recalcula bajo cuatro
  definiciones del número de pruebas — 13 familias, 22 familia×activo, 142
  familia×activo×semilla y 496.500 configuraciones examinadas.

Implementación completa con citas en
`src/perp_lab/evaluation/multiple_testing.py`; salida canónica en
`reports/study_closure/study_level_multiple_testing.json`. El marco general de
la crítica al backtest reportado sigue a López de Prado (2018) y
Harvey, Liu & Zhu (2016).

## 5.7 Registro y reproducibilidad

Cada ejecución registra una identidad: hash de configuración, contrato de
datos, hashes de datasets, commit y diff del árbol
(`tracking/identity.py`); los estudios multi-semilla llevan checkpoint por
unidad y reanudación exacta (`experiments/multi_seed.py`), y un auditor
independiente verifica a posteriori paridad de presupuesto por fold, ganadores
con huella y dispersión intra-fold (`scripts/audit_study_isolation.py`; 100/100
runs en la ronda principal). El entorno queda fijado por `uv.lock` y todo
muestreo aleatorio pasa por generadores inyectados con semillas derivadas
deterministamente (`utils/seeds.py`).

## 5.8 Capa de meta-etiquetado (RQ3)

Sobre las señales de una regla primaria se construyen etiquetas de triple
barrera cortadas en retornos netos de costes, con la convención de llenado
`next_open` — la única que el motor puede ejecutar realmente
(`labeling/triple_barrier.py`). Un clasificador (regresión logística, random
forest; LightGBM preregistrado) decide únicamente si actuar, nunca la
dirección; sus probabilidades se calibran y su umbral se elige en bloques
cronológicos disjuntos, y la función de ajuste no acepta datos de test
(`meta_labeling/model.py`). La capa se validó primero sobre dos mercados
sintéticos emparejados —uno con ventaja plantada, otro de ruido puro donde debe
abstenerse— (ADR 0017) y después se ejecutó sobre datos reales bajo contrato
exploratorio; el resultado se presenta en el capítulo 6.
