# `CRT_INTRADAY_V2` — preregistración

> **ESTADO: BORRADOR. NO EJECUTABLE.**
>
> No existe ninguna configuración, ningún run y ningún resultado de esta ronda.
> **V2 no se ejecuta hasta que `CRT_INTRADAY_V1` esté cerrada y su denominador
> recalculado** según [crt_intraday.md §6bis.2](crt_intraday.md). Ejecutarla
> antes convertiría V1 y V2 en una única búsqueda mal contada.
>
> **Fecha de redacción: 2026-08-16.** Escrita antes de que exista un solo
> resultado de V1. Esa es toda su razón de ser: si estas hipótesis se
> escribieran después, serían filtros post-hoc sobre V1 con otro nombre.

Relacionado: [crt_intraday.md](crt_intraday.md) ·
[study_level_multiple_testing.md](study_level_multiple_testing.md) ·
[holdout_audit_status.md](holdout_audit_status.md)

---

## 0. Lo que V2 no puede ser

Hereda sin excepción la restricción de V1: **la partición final está consumida**,
así que ninguna familia de V2 puede promocionarse a estrategia operativa. V2
produce evidencia sobre un mecanismo, no candidatos. El resultado esperado y
declarado sigue siendo `REJECTED`.

Y hereda una segunda, propia de V2: **no es una segunda oportunidad para las
familias de V1.** Si V1 cierra en negativo, V2 no es «volver a intentarlo con
más parámetros». Es una pregunta distinta —¿el mecanismo dependía de cuándo se
opera?— cuyo resultado más probable es que tampoco.

---

## 1. Qué distingue esto de un filtro post-hoc

Es la objeción central y merece contestarse antes que nada.

Un filtro post-hoc es mirar los resultados de V1, observar que las entradas de
madrugada pierden, y publicar «CRT funciona filtrando por sesión». Eso no es una
hipótesis: es describir el ruido de una muestra y presentarlo como estructura.

Tres condiciones separan V2 de eso, y las tres son verificables:

1. **Anterioridad demostrable.** Este documento se commitea **antes** de ejecutar
   V1. La cadena de commits es la prueba, igual que `02b79f1` lo fue para el
   candidato del holdout. Si esta preregistración apareciera después del primer
   resultado de V1, no valdría nada, y eso se puede comprobar con `git log`.
2. **Búsqueda nueva, no reetiquetado.** V2 ejecuta una búsqueda completa sobre el
   espacio ampliado, con su propio presupuesto, sus propios folds y sus propias
   semillas. **No se obtiene troceando los ledgers de V1.** Un filtro aplicado a
   posteriori sobre operaciones ya generadas no es una estrategia distinta; es la
   misma estrategia con una máscara elegida a la vista del resultado.
3. **V1 no se reescribe.** Su resultado se publica tal cual salga, con o sin V2.
   V2 no puede «rescatar» a V1, y una V1 negativa seguida de una V2 positiva se
   reporta como lo que sería: dos tests de un mecanismo, contados juntos.

La condición 1 es la que hace falsable a este documento. Las otras dos son
disciplina de ejecución.

---

## 2. Hipótesis admitidas

Cada una necesita un mecanismo económico. Sin mecanismo, no entra: «este
parámetro mejora el Sharpe» no es una hipótesis, es un resultado buscando
justificación.

### H1 — Ventana de ejecución por sesión

**Mecanismo.** Los perps cotizan 24/7, pero la participación no es uniforme. La
profundidad del libro, el spread y el flujo agresor siguen el horario de las
mesas centralizadas: Asia (00–08 UTC), Londres (07–16), Nueva York (13–21).

Esto importa **específicamente para el mecanismo CRT**, no de forma genérica. El
patrón exige que exista liquidez en reposo que barrer y que alguien absorba la
recuperación del nivel. En horas delgadas, un barrido del mismo tamaño nominal
tiene más probabilidad de ser ruido de un libro fino, y la «recuperación» más
probabilidad de ser un artefacto del spread. La hipótesis no es «hay horas
rentables»; es **«el mecanismo necesita un mínimo de participación, y la
participación es función de la sesión»**.

Es falsable en la dirección incómoda: si CRT funciona igual de mal en Londres
que a las 3 de la mañana, la explicación por liquidez queda descartada.

**Aviso — solapamiento parcial con V1.** Tres familias de V1
(`session_liquidity_sweep`, `session_range_rotation`,
`opening_range_breakout_retest`) **ya tienen** un parámetro `session` o
`session_pair`. **No es lo mismo y no debe fusionarse:** el de V1 elige *de qué
sesión se construye el nivel*; H1 filtra *cuándo se permite ejecutar*. Un setup
puede leer el rango de Asia y ejecutarse en Londres. Son ejes ortogonales y en
V2 coexisten. **Este parámetro no se añade a V1**, según lo acordado.

### H2 — Fin de semana

**Mecanismo.** El perp no cierra, pero una clase grande de participantes sí. El
fin de semana el volumen cae, el spread se ensancha y el flujo se sesga a
minorista. Además, y esto es lo específico del mecanismo, **los niveles de
referencia que usan `pdl_reclaim_long` y `pdh_reclaim_short` son «el máximo y el
mínimo del día anterior»** — y un día anterior que fue sábado no representa lo
mismo que un jueves. El nivel existe igual; lo que cambia es cuánta gente lo
estaba mirando cuando se formó.

De ahí que el parámetro tenga dos formas, y ambas se prueban:

- excluir **entradas** en sábado/domingo UTC;
- excluir setups cuyo **nivel de referencia** se construyó en fin de semana.

**Decisión deliberada: H2 y H3 son un solo eje, no dos.** «Excluir fin de semana»
y «filtrar por día de la semana» son casi colineales. Declararlas como dos
parámetros libres duplicaría la cardinalidad para probar una idea, y con el
presupuesto fijo eso solo diluye la búsqueda. Se prueban como niveles de un
único parámetro.

### H3 — Día de la semana, como eje libre — **RECHAZADA**

Se considera y **no entra**. No hay mecanismo: el perp no tiene calendario de
liquidación, y no existe razón estructural por la que un martes deba
comportarse distinto de un miércoles. Lo único defendible del día de la semana
es el efecto fin de semana, que ya cubre H2.

Un parámetro `weekday ∈ {lun…dom}` multiplicaría el espacio por siete a cambio
de siete oportunidades más de encontrar un ganador por azar. Es exactamente la
clase de grado de libertad que esta tesis existe para desaconsejar, y se deja
registrado que se descartó **antes** de ver un resultado, no después.

---

## 3. Espacio de parámetros

Se añaden **dos** parámetros categóricos a las nueve familias de V1. Todo lo
demás —`sweep_bps`, `stop_kind`, `target_plan`, `time_stop_bars`,
`min_net_reward_risk`, `direction` y los propios de cada familia— **queda
exactamente como en V1** y no se retoca.

| Parámetro | Niveles | Card. |
|---|---|---:|
| `execution_session` | `any`, `london`, `new_york`, `london_or_new_york` | 4 |
| `weekend_policy` | `any`, `exclude_weekend_entries` | 2 |

Multiplicador: **×8** sobre el espacio de cada familia.

| Familia | Rejilla V1 | Rejilla V2 |
|---|---:|---:|
| `pdl_reclaim_long` | 192 | 1.536 |
| `pdh_reclaim_short` | 192 | 1.536 |
| `crt_htf_range_reversal` | 864 | 6.912 |
| `session_liquidity_sweep` | 864 | 6.912 |
| `session_range_rotation` | 864 | 6.912 |
| `crt_three_candle_model` | 864 | 6.912 |
| `opening_range_breakout_retest` | 576 | 4.608 |
| `failed_breakout_reversal` | 576 | 4.608 |
| `double_sweep_reversal` | 576 | 4.608 |
| **Total** | **5.568** | **44.544** |

`execution_session` se declara con cuatro niveles y no con dos porque la
hipótesis es sobre *participación*, y distinguir Londres de Nueva York es la
única forma de que H1 pueda fallar de manera informativa: si solo una de las dos
sesiones «funciona», eso es evidencia contra el mecanismo de liquidez, no a
favor. Los rangos se congelan aquí y no se tocan después.

---

## 4. Impacto sobre el denominador global

**El presupuesto no cambia: 100 evaluaciones por fold y motor.** Por tanto el
número de configuraciones evaluadas **no escala con el tamaño de la rejilla** —
escala con unidades × folds × presupuesto. Una rejilla ocho veces mayor con el
mismo presupuesto significa que Random Search cubre una fracción ocho veces
menor del espacio, lo cual es conservador, no permisivo.

Suelo garantizado por contrato, con el mismo protocolo que V1
(9 familias × 2 activos × 10 semillas × 15 folds × 2 motores × 100):

| Concepto | Tras V1 | Tras V2 |
|---|---:|---:|
| Familias | 22 | **22** |
| Familia × activo | 40 | **40** |
| Configuraciones (suelo) | ≥ 1.036.500 | **≥ 1.576.500** |

El recuento que entra en el Deflated Sharpe es siempre el **medido** con
`evaluations_examined`, nunca el suelo del contrato. Véase la rectificación de
[crt_intraday.md §6bis.2](crt_intraday.md).

### El problema que V2 introduce y Holm no ve

**El conteo de familias no sube, y ahí está la trampa.** V2 no añade hipótesis
nuevas: vuelve a probar **las mismas nueve familias** con más libertad. Una
corrección de Holm sobre 22 familias trataría eso como si cada familia se
hubiera probado una vez, cuando se habrá probado dos, con espacios distintos.

Esto se declara ahora para que no se resuelva a conveniencia después. Al cerrar
V2, el estudio debe reportar, como mínimo:

1. La corrección sobre las 22 familias, tal como está definida, **y**
2. Una corrección alternativa que trate **`familia × ronda`** como unidad de
   test, llevando el conteo a 22 + 9 = **31**, porque una familia probada en V1 y
   en V2 tuvo dos oportunidades.
3. El **Deflated Sharpe sobre el recuento medido de todo el estudio**, que ya
   absorbe ambas rondas sin depender de cómo se agrupen las familias, y es por
   eso la cifra más robusta de las tres.

Si las tres coinciden en negativo, la conclusión no depende del agrupamiento —
que es la forma más fuerte que puede tomar este resultado, y la misma propiedad
que hizo sólido el cierre de las 13 familias.

---

## 5. Protocolo

Idéntico a V1, sin excepciones: BTC+ETH, 10 semillas desde la 42, 15 folds
cronológicos, búsqueda independiente por fold, purga y embargo, costes reales
más estrés de costes duplicados, batería de robustez, sensibilidad de
parámetros, drop-top-trades y evaluación por regímenes.

**Random Search es la búsqueda primaria y la única evidencia confirmatoria.** El
algoritmo genético corre a presupuesto idéntico como cross-check de robustez y
nunca como motor de descubrimiento.

---

## 6. Qué falta antes de poder ejecutar

1. Cerrar V1 y recalcular su denominador.
2. Implementar los dos parámetros en `crt/` y `search/registry.py` bajo un
   `SPACE_VERSION` nuevo, sin tocar el espacio de V1.
3. Tests: que el filtro de sesión sea causal y respete DST e IANA como el resto
   del módulo; que `weekend_policy` distinga entrada de nivel de referencia; y
   que una familia con `execution_session="any"` y `weekend_policy="any"`
   reproduzca **exactamente** su comportamiento de V1 — sin ese test, V2 no es
   una ampliación sino un cambio silencioso de V1.
4. Generar las configs con un `make_crt_v2_configs.py` análogo.
5. Registrar la ronda en `ROUND_TAGS` como `CRT_INTRADAY_V2`.

Ninguno de esos pasos se inicia mientras este documento siga en BORRADOR.
