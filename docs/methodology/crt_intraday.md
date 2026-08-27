# CRT intradía: de la lectura discrecional a una hipótesis falsable

**Estado: motor y nueve familias implementados y testeados. Ninguna estrategia
ejecutada sobre datos reales. Ningún resultado de rendimiento existe todavía.**

**Ninguna familia de esta ronda puede promocionarse: la partición final está
consumida. Esta ronda produce evidencia, no candidatos operativos.** La
declaración completa, fechada y escrita antes de ejecutar, está en el
[apartado 6bis](#6bis-declaración-previa-a-la-ejecución).

Este documento describe el módulo `src/perp_lab/crt/` y registra la ronda
experimental `CRT_INTRADAY_V1`. No contiene métricas porque los experimentos no
se han corrido. Cuando se corran, sus resultados se añadirán aquí y se contarán
en el diagnóstico de comparaciones múltiples del estudio, no aparte.

---

## 1. El problema con CRT como se enseña normalmente

Candle Range Theory se explica en términos de secuencia: se congela el rango de
una vela, el precio barre uno de sus extremos, el barrido es rechazado, el nivel
se recupera, y el precio rota hacia el punto medio.

Contado así no es falsable, por dos razones distintas.

**Cada término es un juicio.** ¿Cuánto tiene que penetrar el precio para que sea
un "barrido" y no un simple roce? ¿Cuánta mecha hace falta para que sea un
"rechazo"? Sin un número, la respuesta se decide mirando lo que pasó después, y
entonces el patrón siempre funciona.

**El orden se pierde al programarlo.** La traducción ingenua a código son
columnas booleanas independientes: `hubo_barrido`, `cerró_dentro`,
`mecha_grande`. Pero un cierre dentro del rango no significa nada por sí solo;
significa algo únicamente si el precio había salido antes y lo bastante. Un
modelo construido sobre booleanos sin orden dispara en barras donde la secuencia
nunca ocurrió.

El módulo ataca las dos cosas: cada término tiene una definición aritmética con
umbral configurable, y cada patrón es una máquina de estados ordenada.

---

## 2. La garantía de causalidad: `available_from`

Es el punto más importante del módulo y el error que más fácilmente se comete.

"El máximo de ayer" es un solo número para todo el día de hoy. La implementación
natural es agrupar por día, calcular el máximo y difundirlo a las barras. Hecho
sin desplazar, **cada barra del día conoce el máximo del día en el que está**,
incluidas las barras anteriores al momento en que ese máximo se marcó. Una
estrategia construida sobre eso parece excelente y no vale nada.

La misma trampa aplica a:

- el máximo de una sesión mientras la sesión todavía se está formando,
- los extremos de una vela H4 o diaria que aún no ha cerrado,
- un rango de N días que incluya el día en curso.

Por eso cada rango que produce `ranges.py` lleva una columna `available_from`, y
esa columna es el contrato:

> Un nivel solo puede leerse en instantes `>= available_from`, que es el cierre
> del periodo que lo construyó. No existe configuración que lo desactive.

El acceso se hace por `active_ranges_at(ranges, momento)` y `latest_range(...)`.
Filtrar la tabla a mano está desaconsejado precisamente porque es como se olvida
el desplazamiento.

El test `test_no_bar_of_a_day_can_see_that_days_own_extremes` fija esto sobre
datos donde la respuesta se conoce por construcción, y
`test_every_built_range_is_available_no_earlier_than_its_period_ends` lo
comprueba de golpe sobre todos los tipos de rango.

La única excepción deliberada es el **opening range**, que sí queda disponible
dentro de su propia sesión — pero solo desde que su ventana de apertura termina,
y caduca al cerrar la sesión.

---

## 3. Sesiones: por qué no vale un desplazamiento fijo

Cripto no cierra, así que una "sesión" aquí no es un calendario de mercado sino
una ventana del día en la que un tipo de participante está activo. Es una
decisión de modelado, y por tanto tiene que ser explícita.

Dos cosas lo complican más de lo que parece.

**El horario de verano.** Londres y Nueva York no cambian la hora la misma
semana. Una sesión anclada a las 08:00 de Europe/London cae a las 08:00 UTC en
invierno y a las 07:00 UTC en verano, y durante unos quince días de marzo la
distancia entre Londres y Nueva York es una hora menor de lo habitual. Codificar
un desplazamiento fijo desplaza silenciosamente todos los niveles dos veces al
año, y el artefacto resultante se parece a estacionalidad. Todo se resuelve con
zonas IANA, día natural a día natural.

**La medianoche.** La sesión asiática empieza por la tarde en su propia zona y
acaba a la mañana siguiente. Las ventanas se guardan como *inicio + duración* en
vez de inicio y fin, de modo que una ventana que cruza medianoche es el caso
ordinario y no uno que haya que recordar.

Las sesiones que se solapan reclaman sus barras a la vez. El solape
Londres–Nueva York está dentro de sus dos padres por construcción, y obligar a
una barra a elegir destruiría justo lo que se quiere medir.

| Sesión | Zona | Inicio | Duración |
|---|---|---|---|
| `asia` | Asia/Tokyo | 09:00 | 9 h |
| `london` | Europe/London | 08:00 | 8 h 30 |
| `new_york` | America/New_York | 09:30 | 6 h 30 |
| `london_new_york_overlap` | America/New_York | 09:30 | 3 h |
| `crypto_day` | UTC | 00:00 | 24 h |

---

## 4. Definiciones mecánicas

Todos los umbrales llevan unidad explícita. Las profundidades se expresan en
puntos básicos del nivel y, opcionalmente, como fracción de ATR; un barrido debe
superar el más exigente de los dos criterios configurados, lo que mantiene la
definición comparable entre regímenes de volatilidad sin fijar una escala de
precio.

Para un rango de referencia con máximo `H_R`, mínimo `L_R` y medio
`M_R = (H_R + L_R)/2`:

| Concepto | Definición mecánica |
|---|---|
| Aproximación | El extremo de la barra queda a `<= approach_bps` del nivel sin alcanzarlo. |
| Toque | El extremo alcanza el nivel. La igualdad cuenta: un mínimo exactamente igual a `L_R` es un toque. |
| Penetración | La excursión más allá del nivel supera `pierce_bps`. |
| Barrido | La penetración alcanza `max(sweep_bps, sweep_atr_fraction · ATR)`. |
| Rechazo | Tras penetrar, el cierre vuelve al lado original del nivel. |
| Recuperación | Tras un **barrido**, `reclaim_confirmation_closes` cierres dentro del rango, dentro de `reclaim_within_bars` barras, superando `reclaim_buffer_bps` y los filtros de forma. |
| Retest | Tras recuperar, el precio vuelve a `<= retest_tolerance_bps` del nivel. |
| Recuperación fallida | Tras recuperar, un cierre vuelve a perder el nivel. |
| Aceptación fuera | `acceptance_closes` cierres consecutivos a más de `acceptance_bps` del nivel. |

La distinción entre **rechazo** y **recuperación** es deliberada y operativa: un
rechazo sin barrido previo no es un setup. El precio se asomó y volvió, pero
nunca salió lo suficiente como para que hubiera algo que recuperar, así que no
se registra barrido y nada aguas abajo puede dispararse.

### Absorción

Con solo OHLCV **no se puede afirmar que exista absorción real de órdenes**. Lo
que se puede medir es un conjunto de síntomas compatibles con ella: varios
intentos de ruptura sin continuación, mechas repetidas en el mismo nivel,
penetraciones progresivamente menores, cierres que no consiguen alejarse,
volumen alto sin desplazamiento proporcional.

Eso se etiqueta como `OHLCV_ABSORPTION_PROXY` y **nunca** como absorción
observada. Si en algún momento hay datos de taker flow, delta, CVD o libro de
órdenes, se podrá construir `ORDER_FLOW_CONFIRMED_ABSORPTION` como concepto
separado. Los dos no se mezclan ni se presentan como equivalentes.

---

## 5. La máquina de estados

Cada nivel se sigue con una máquina explícita en vez de con condiciones sueltas.
Los estados son `AVAILABLE`, `APPROACHING`, `TOUCHED`, `PIERCED`, `SWEPT`,
`REJECTED`, `RECLAIMED`, `RETESTED`, `ACCEPTED_OUTSIDE`, `FAILED_RECLAIM`,
`TARGET_REACHED`, `INVALIDATED` y `EXPIRED`.

Cada transición se guarda con la barra que la causó, el precio, el nivel
afectado y la magnitud medida que la disparó. Eso es lo que permite explicar una
señal después, en vez de solo reproducirla.

Largo y corto comparten una única implementación mediante un `Side` con signo,
de forma que las dos variantes no pueden divergir. El test
`test_the_short_side_mirrors_the_long_side_exactly` refleja los precios a través
del nivel y exige el mismo estado y la misma profundidad.

### Tres defectos que encontraron los tests

Merece la pena registrarlos porque los tres eran silenciosos:

1. Un mínimo **exactamente igual** al nivel se clasificaba como "aproximación" en
   vez de "toque". El test limpio que aguanta al tick es justo el caso que más
   importa, y una desigualdad estricta lo archivaba como "no llegó".
2. La confirmación de recuperación con **varios cierres** no podía completarse
   nunca: las barras confirmatorias dejaban de examinarse en cuanto el precio se
   alejaba del nivel, que es exactamente lo que hace una recuperación.
3. Un roce superficial que cerraba dentro registraba un barrido que no se había
   ganado.

---

## 6. Ronda experimental `CRT_INTRADAY_V1`

Registrada como ronda **nueva y separada**. No se añade retrospectivamente a R2
ni a R3, y sus resultados no se mezclan con familias ya cerradas.

Cuando se ejecute, el protocolo será el mismo que rechazó a las trece familias
anteriores, sin rebajas:

- BTCUSDT y ETHUSDT.
- Ejecución en 5m y 15m donde el dato lo permita; referencias 1h, 4h y diaria.
- Sesiones Asia, Londres y Nueva York.
- Variantes largas y cortas.
- Costes reales y costes duplicados como prueba de estrés.
- Diez semillas.
- Walk-forward con purga y embargo.
- Resultados fuera de muestra, robustez por fold y por régimen.
- Sensibilidad de parámetros y eliminación de las mejores operaciones.
- Corrección por comparaciones múltiples **contando todas las configuraciones
  evaluadas, no solo la ganadora**, e incorporándolas al Deflated Sharpe.

Los rangos de parámetros se mantienen cortos y bien separados a propósito. Una
rejilla de cientos de valores casi idénticos no explora más hipótesis: solo
infla el número de pruebas y degrada la corrección múltiple sin aportar
información.

### Lo que este documento **no** dice

No dice que estos patrones funcionen. La expectativa previa, dada la EDA del
estudio y trece familias rechazadas sobre el mismo activo, es que también sean
rechazados. Se implementan porque son hipótesis concretas y comprobables, y
porque un mapa de dónde *no* está el edge vale más cuanto más territorio cubre.

El holdout congelado no se usa para construir, seleccionar ni ajustar nada de
esto.

---

## 6bis. Declaración previa a la ejecución

**Fecha: 2026-08-16. Escrito antes de ejecutar una sola unidad de esta ronda y
antes de observar ningún resultado.** Este apartado existe para que las dos
consecuencias de abajo no puedan decidirse después, a la vista de lo que salga.

### 6bis.1 Ninguna familia CRT puede promocionarse

La partición final `[2026-01-01, 2026-07-01)` **está consumida**: se abrió una
vez el 2026-08-13 sobre `volatility_breakout` y no queda ninguna prueba
confirmatoria limpia sobre este histórico. Véase
[holdout_audit_status.md](holdout_audit_status.md) §5.1.

De ahí se sigue, sin margen de interpretación:

> **Ninguna familia de la ronda `CRT_INTRADAY_V1` puede promocionarse a
> estrategia operativa, gane lo que gane.** Esta ronda produce **evidencia, no
> candidatos.** No existe el estado `PROMOTED` para ninguna de las nueve.

El mejor resultado posible de esta ronda es una familia con señal parcial en
desarrollo, y una señal parcial en desarrollo **no es un resultado positivo**:
es una hipótesis que se queda sin forma de confirmarse. El destino esperado y
declarado de las nueve familias es `REJECTED`, y eso es un resultado válido —
el mapa de dónde *no* está el edge vale más cuanto más territorio cubre.

Recuperar la capacidad de promocionar exige datos nuevos más allá de
`2026-07-01` y una partición congelada declarada antes de mirarla. Eso es
trabajo futuro y no puede sustituirse reinterpretando lo ya existente.

### 6bis.2 Qué le pasa al denominador de comparaciones múltiples

El cierre vigente
([study_level_multiple_testing.md](study_level_multiple_testing.md), commit
`232bc372`) está fijado en **N = 13 familias** y **496.500 configuraciones
evaluadas**. Esa cuenta **no incluye** esta ronda.

Contabilidad declarada de antemano:

| Concepto | Cierre vigente | Tras `CRT_INTRADAY_V1` |
|---|---:|---:|
| Familias | 13 | **22** |
| Familia × activo | 22 | **40** |
| Pruebas (ver 2ª rectificación) | 436.092 | **≈ 878.000, techo 976.092** |

> ### Rectificación — 2026-08-16
>
> **La primera redacción de esta tabla, escrita el mismo día, daba
> «1.036.500» como cifra cerrada y afirmaba que las 540.000 añadidas eran
> exactas porque «la paridad de presupuesto garantiza esa cifra». Las dos
> afirmaciones eran incorrectas y se corrigen aquí en lugar de reescribirse.**
>
> El error fue **sumar dos bases de conteo distintas**. Verificado en
> `reporting/study_closure.py::evaluations_examined`, el 496.500 del cierre no
> es un producto del contrato: es el **recuento de filas reales** de los
> ficheros `{engine}_candidates.parquet`, es decir, cada candidato que la
> búsqueda llegó a puntuar. El producto del contrato para ese mismo estudio es
> 284 unidades × 15 folds × 100 = **426.000**. La diferencia, **+16,5 %**, son
> propuestas inválidas, duplicadas y aciertos de caché: se registran como filas
> pero **no consumen presupuesto**, que es precisamente lo que hace no
> explotable el elitismo del GA.
>
> Por tanto las 540.000 de CRT son un **suelo garantizado**, no un total. Bajo
> el mismo ratio empírico el recuento real rondaría las 629.000, pero ese ratio
> depende de la familia —de cuántas propuestas rechaza su `validate`— y **no
> puede declararse por adelantado**. Declararlo sería justo el tipo de cifra
> inventada que esta tesis documenta.
>
> Redacción correcta: tras la ronda, el denominador se **mide** con
> `evaluations_examined` sobre la unión de los directorios de run, y será
> **≥ 1.036.500**. La cifra que entra en el Deflated Sharpe es la medida, nunca
> la del contrato.
>
> Los recuentos de **familias (13 → 22) y de familia × activo (22 → 40) sí son
> correctos** y se mantienen: 6 R3 + 4 S1 + 3 S2 + 9 CRT = 22, y
> 6×2 + 4×1 + 3×2 + 9×2 = 40. No dependen de la base de conteo.

> ### Segunda rectificación — 2026-08-16
>
> **La primera rectificación también estaba mal, y en la dirección contraria.**
> Dijo que 540.000 era un *suelo garantizado* y que el recuento real quedaría por
> encima. Es al revés: **540.000 es un techo que la búsqueda puede no alcanzar.**
> Se deja la primera nota tal cual y se corrige aquí.
>
> El error de fondo era razonar sobre supuestos en vez de medir. Ahora está
> medido sobre el estudio ya cerrado, reproduciendo su propio inventario
> (`build_inventory` → 284 unidades, 142 directorios de run, 4.260 grupos
> fold × motor × unidad, `evaluations_examined` = 496.500, idéntico al artefacto).
>
> **Qué son en realidad las 496.500 filas.** No hay más que dos estados, y
> ninguno es el que ambas notas anteriores supusieron:
>
> | Estado | Filas | % | Qué es |
> |---|---:|---:|---|
> | `evaluated` | 436.092 | 87,8 % | Configuración distinta, backtesteada, con objetivo válido |
> | `failed` | 60.408 | 12,2 % | Configuración distinta, **backtesteada**, rechazada por `min_trades_total 4` |
>
> **Duplicados: 0. Aciertos de caché: 0.** Verificado en los 4.260 grupos:
> `n_unique(params_json) == n_filas` en todos, sin una sola excepción. El
> parquet solo registra candidatos genuinamente nuevos, así que la premisa de la
> primera nota —que el exceso eran duplicados y caché— era falsa. Y los `failed`
> **sí tocaron el dato**: corrieron su backtest y produjeron un número de
> operaciones; lo que no produjeron es un objetivo admisible.
>
> **El 426.000 no existía.** Salía de suponer presupuesto 100 y 15 folds para
> todo el estudio. Medido, el presupuesto fue heterogéneo por diseño:
>
> | Puerta | Grupos | `evaluated` | `failed` | Media por grupo |
> |---|---:|---:|---:|---:|
> | R2 | 600 | 178.321 | 1.679 | 297,2 |
> | R3 | 3.000 | 245.589 | 54.411 | **81,9** |
> | S1 | 120 | 2.266 | 734 | 18,9 |
> | S2 | 540 | 9.916 | 3.584 | 18,4 |
>
> La fila de R3 es la importante: con presupuesto declarado de 100, la media
> realizada es **81,9**. Un presupuesto es un **tope**, no una cuota. Cuando el
> espacio es pequeño o rechaza muchas propuestas, la búsqueda termina por debajo,
> y hay grupos con cero candidatos admisibles. De ahí que un producto de contrato
> sea siempre un techo.
>
> ---
>
> #### Definición operativa de «prueba», congelada aquí
>
> > **Una prueba es una configuración de parámetros distinta que, dentro de su
> > fold y motor, consumió presupuesto y produjo un objetivo válido.**
>
> Es la definición propuesta con **una corrección**, que conviene explicar porque
> cambia el resultado en dos órdenes de magnitud. La propuesta decía «y produjo un
> Sharpe out-of-sample». En este pipeline los candidatos se puntúan sobre la
> ventana de **validación** (`mean_val_sharpe`); el único que llega a tocar test
> es el ganador de cada fold. Tomada al pie de la letra, esa definición daría
> N ≈ 4.260 —los ganadores— cuando la selección operó de hecho sobre cientos de
> miles de candidatos. Sería un DSR mucho más permisivo de lo debido.
>
> Lo que el Deflated Sharpe necesita es *sobre cuántas oportunidades se tomó el
> máximo*, y esas son las evaluaciones de validación. Por eso la tercera cláusula
> queda como **«produjo un objetivo válido»**, y el out-of-sample no entra.
>
> **Caché y duplicados: excluidos**, y la exclusión no cuesta nada porque no
> existen — no se registra ninguno. Si algún día se registraran, quedan excluidos
> por definición: una caché devuelve el resultado de una configuración ya contada
> y volver a sumarla contaría dos veces la misma oportunidad.
>
> **`failed`: excluidos.** Una configuración rechazada por no alcanzar el mínimo
> de operaciones nunca pudo ganar la selección, así que no fue una oportunidad de
> producir un falso positivo. El criterio `min_trades_total` está preregistrado en
> el objetivo y se aplica igual a todas las familias, de modo que excluirlas no es
> una elección hecha a la vista de los resultados. Se registra que son 60.408 y
> que se conocen, para que la exclusión sea auditable en lugar de silenciosa.
>
> #### N bajo esta definición
>
> | | N |
> |---|---:|
> | **Estudio cerrado (13 familias), medido** | **436.092** |
> | V1 proyectado, techo del contrato (5.400 grupos × 100) | ≤ 540.000 |
> | V1 proyectado, si se realiza como R3 (81,9 %) | ≈ 442.000 |
> | **Estudio + V1, a medir tras la ronda** | **≈ 878.000, techo 976.092** |
>
> La proyección de V1 es una **proyección**, no una declaración: depende de
> cuántas propuestas rechaza el `validate` de cada familia, y las rejillas CRT
> son pequeñas (192 para `pdl`/`pdh`), lo que empuja a la baja. El número que
> entra en el DSR será el **medido** con `evaluations_examined` restringido a
> `status == 'evaluated'`, nunca una proyección ni un producto de contrato.
>
> **Esta definición queda fijada antes de que exista un solo resultado de V1.**
> Ese es su propósito: si se eligiera después, se elegiría la que mejor le
> sentara al resultado.

El techo de 540.000 sale del contrato congelado: 9 familias × 2 activos × 10
semillas × 15 folds × 2 motores × 100 evaluaciones por fold y motor. El
presupuesto es un tope por grupo, no una cuota: la cifra que cuenta es la
realizada, y se mide al cerrar la ronda.

**Qué se recalcula, con qué regla de conteo, antes de reportar nada:**

1. **Holm–Bonferroni** (FWER) y **Benjamini–Hochberg** (FDR), ambos a α = 0.05,
   sobre las **22 familias** — no sobre las 9 nuevas por separado. Corregir la
   ronda dentro de sí misma repetiría exactamente el fallo que el cierre vino a
   arreglar: cada puerta corrigiendo internamente y nadie corrigiendo entre
   puertas.
2. **Deflated Sharpe Ratio** de la mejor familia del estudio completo, contando
   la selección sobre el **número de pruebas medido** —configuraciones distintas
   con objetivo válido, según la definición congelada en la 2ª rectificación—
   de todo el estudio, no sobre el techo del contrato ni sobre 22.
3. **PBO por CSCV** sobre las 22 series familiares alineadas, con el mismo
   número de particiones que usó el cierre.
4. **Sensibilidad del conteo** bajo las cuatro reglas ya establecidas —familias,
   familia × activo, familia × activo × semilla, y todas las configuraciones—
   recalculadas con los nuevos totales, para que la conclusión no dependa de qué
   denominador se elija.

La regla primaria de conteo sigue siendo **la familia**, con las semillas
promediadas dentro de cada familia como réplicas de una misma hipótesis, tal y
como está definido en el cierre. Esta ronda no introduce una regla nueva.

#### 6bis.2.1 Qué afirmación usa qué N

Un N no es global: corrige *una* afirmación concreta, y aplicarle a una
afirmación el N de otra la distorsiona en una dirección u otra. Esta tabla fija
la correspondencia antes de que exista un resultado de V1.

| Afirmación | N aplicable | Justificación |
|---|---|---|
| «Ninguna de las 13 familias del cierre sobrevive» | **13 familias / 436.092 pruebas** | Es el estudio tal como se cerró. Su denominador se fija en el momento del cierre y **no se reabre** por trabajo posterior. |
| «`volatility_breakout` era el mejor del cierre y aun así es espurio» | **436.092** | El candidato se seleccionó sobre ese conjunto y sobre ningún otro. |
| «Ninguna de las 22 familias del estudio ampliado sobrevive» | **22 familias / ≈ 878.000 pruebas** | Afirmación nueva sobre un universo nuevo; exige el denominador del universo entero. |
| «Ninguna familia CRT sobrevive» | **22 familias / ≈ 878.000** | No 9 ni 540.000: corregir la ronda dentro de sí misma repetiría el fallo que el cierre vino a arreglar. |
| «El estudio no encuentra ventaja, en ningún momento de su historia» | **≈ 878.000** | Es la afirmación acumulada y le corresponde el denominador acumulado. |

**El punto que no puede quedar ambiguo.** El candidato del cierre se seleccionó
**antes de que V1 existiera**. Añadir retroactivamente a su denominador unos
ensayos que aún no se habían realizado **no es correcto**: el sesgo de selección
que el Deflated Sharpe corrige es el de la búsqueda que produjo *ese* máximo, y
esa búsqueda tuvo 436.092 oportunidades, no 878.000. Por eso las dos primeras
filas conservan su N original de forma permanente.

Lo que sí cambia es que **aparece una afirmación nueva** —sobre 22 familias— que
no existía antes y que sí necesita el denominador ampliado. Las dos conviven: la
del cierre se cita con su N, la ampliada con el suyo, y ninguna hereda el del
otro.

Tres matices, para que la decisión sea auditable y no una preferencia:

1. **La dirección del error es conservadora.** Inflar retroactivamente un
   denominador solo hace más difícil rechazar el nulo, así que hacerlo nunca
   crearía un falso positivo. Es defendible —y algunos autores lo prefieren— pero
   es una elección, no la única lectura, y aquí se decide explícitamente por la
   otra.
2. **En este estudio la cuestión es discutible sin consecuencia**, porque nada
   promociona bajo ninguno de los dos denominadores: el p-valor crudo más bajo es
   0,345 y falla incluso con N = 1. La distinción se fija igualmente, porque una
   regla que solo se define cuando importa se define a conveniencia.
3. **Si alguna vez importara**, la regla ya está escrita y fechada aquí, antes de
   existir el resultado que podría tentar a elegir la otra.

#### Por qué las tres familias S2 no están en `search/registry.py`

`registry.FAMILIES` tiene 19 entradas (6 R3 + 4 S1 + 9 CRT), pero el cierre
cuenta 13 familias, tres de las cuales —`taker_flow_extreme`,
`illiquidity_reversion`, `flow_price_divergence`— no aparecen en este registry.
No es una omisión:

- Se definieron en el commit `de857bd` («Freeze Gate S2 Batch 01 pre-specification
  and S2-A implementation»), que añadió `strategies/{taker_flow_extreme,
  illiquidity_reversion,flow_price_divergence,orderflow}.py`, 176 líneas a
  `search/registry.py`, tres entradas a `search/config.py` y sus tests.
- Se ejecutaron en `de07164` («run the S2-B development pilots and record a
  negative outcome»).
- **Ninguno de los dos es ancestro de `feat/study-closure`.** Viven en la rama
  `feat/s2-evidence-and-strategy-lab`, sin fusionar aquí.

La divergencia es coherente y no hay que arreglarla: el registry describe **qué
puede buscar esta rama**, mientras que el inventario del cierre se reconstruye
**desde los informes de puerta**, no listando el código. Un estudio puede haber
probado una familia cuyo código vive en otra rama; el conteo de hipótesis no
depende de qué esté fusionado.

**Lo que sí hay que vigilar al fusionar.** Desde que `SearchRunConfig.family` se
valida contra `registry.FAMILIES` en lugar de contra una lista propia, una
fusión que traiga las S2 debe dejarlas también en `FAMILIES` y asignarlas a un
grupo de ronda, o sus configs dejarán de validar.
`tests/unit/test_search_config_families.py::test_the_round_groups_partition_the_registry`
falla si se añaden sin declarar su ronda — que es el fallo que se quiere, porque
una familia buscable y sin ronda sería una hipótesis fuera del denominador.

**Condición de bloqueo.** Ninguna cifra de esta ronda —ni en la memoria, ni en
el panel, ni en la landing— puede citarse antes de re-ejecutar
`scripts/run_study_closure.py` y regenerar la evidencia web. Reportar un
resultado CRT contra la corrección de 13 familias sería subestimar el número de
oportunidades que tuvo la búsqueda de producir un ganador, que es precisamente
el error que esta tesis existe para documentar.

### 6bis.2.2 Reanudación: qué se pierde si el proceso muere

Verificado sobre la ejecución en curso, no sobre la documentación.

- **Granularidad: la unidad `(activo, semilla)`.** Las claves del checkpoint son
  literalmente `BTCUSDT|seed=891022`. Cada familia son 20 unidades (2 activos ×
  10 semillas), 180 en la ronda.
- **Persistencia tras cada unidad.** `Checkpoint.mark_done()` escribe y hace
  `_flush()` inmediatamente, vía `atomic_write_json` → escritura a temporal y
  reemplazo. No hay escrituras a medias: o la unidad está entera en el
  `checkpoint.json` o no está.
- **Lo que se pierde es, como mucho, la unidad en curso**: sus 15 folds × 2
  motores, unos 4 minutos. **El trabajo intra-unidad no se checkpointea**: morir
  en el fold 14 de 15 pierde los 15.
- **Reanudar es seguro y casi gratis.** `run_crt_v1.py` no salta familias, pero
  `multi-seed` sí salta unidades ya persistidas (`is_done`), así que una familia
  completa se re-recorre en segundos. La robustez y la auditoría se rehacen (~9 s
  y ~4 s por familia, medidos).
- **`assert_compatible()` protege el pooling**: un checkpoint escrito bajo otra
  config, contrato o huella de código se niega a reanudarse en lugar de mezclar
  resultados incomparables.

El comando de recuperación es el mismo que el de arranque:
`uv run python scripts/run_crt_v1.py`.

### 6bis.3 Motor de búsqueda

**Random Search es la búsqueda primaria y la única evidencia confirmatoria.** El
algoritmo genético se ejecuta a presupuesto idéntico como *cross-check* de
robustez —¿coinciden dos mecanismos de búsqueda distintos en que no hay nada?—
y **nunca como motor de descubrimiento**. Ningún resultado de esta ronda puede
apoyarse en el GA si RS no lo sostiene. Esto es consistente con CR-2 del estudio,
donde el GA no mostró ventaja sobre RS.

### 6bis.4 Compromiso de medición: exposición desigual a la selección

**Declarado antes de tener resultados; a completar al cerrar la ronda.**

R3 realizó **81,9** evaluaciones válidas por grupo contra un presupuesto
declarado de 100. Los primeros folds de V1 realizan **100 de 100**. Si eso se
sostiene, la lectura es que el `validate()` de las familias CRT rechaza muchas
menos propuestas que el de R3, de modo que **por la misma cuota nominal las CRT
recorren un espacio efectivo mayor**.

Eso importa para una corrección conjunta. Holm y Benjamini-Hochberg sobre 22
familias tratan a cada familia como una prueba, pero **no todas habrán tenido la
misma exposición a la selección múltiple**: una familia que examinó 100
candidatos por fold tuvo más oportunidades de producir un máximo afortunado que
una que examinó 82. La corrección por familias no ve esa asimetría; el Deflated
Sharpe, que cuenta ensayos y no familias, sí.

Al cerrar la ronda se medirá y se publicará aquí, para las 22 familias:

1. **Tasa de rechazo de `validate()` por familia** — `failed / (evaluated + failed)`.
2. **Presupuesto realizado / declarado por familia**, con la dispersión por fold.
3. Si la asimetría se confirma, **qué implica para comparar familias bajo una
   corrección conjunta**, y si procede reportar el DSR por familia con su propio
   número de ensayos junto al DSR global.

**No se cambia nada del pipeline por esto.** Es una propiedad medida del estudio
que se documenta; ajustar presupuestos a posteriori para igualar exposición sería
cambiar el experimento después de ver cómo salió.

---

## 7. Ficheros

| Fichero | Contenido |
|---|---|
| `src/perp_lab/crt/sessions.py` | Sesiones con zonas IANA, DST y cruce de medianoche. |
| `src/perp_lab/crt/ranges.py` | Rangos de referencia y niveles, con `available_from`. |
| `src/perp_lab/crt/states.py` | Máquina de estados de liquidez y definiciones mecánicas. |
| `src/perp_lab/crt/signals.py` | Pipeline de eventos y señales, sin duplicados. |
| `src/perp_lab/crt/entries.py` | Reglas de entrada comparables, pivotes causales. |
| `src/perp_lab/crt/exits.py` | Stops, objetivos, parciales, ambigüedad intrabar. |
| `src/perp_lab/crt/risk.py` | Dimensionado y límites, separado de la señal. |
| `src/perp_lab/crt/strategies.py` | Nueve familias, largo y corto por `Side`. |
| `tests/unit/test_crt_*.py` | Causalidad, simetría, ambigüedad, límites de riesgo. |
