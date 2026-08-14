# CRT intradía: de la lectura discrecional a una hipótesis falsable

**Estado: motor y nueve familias implementados y testeados. Ninguna estrategia
ejecutada sobre datos reales. Ningún resultado de rendimiento existe todavía.**

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
