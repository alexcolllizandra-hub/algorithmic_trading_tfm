# Estado de la auditoría del holdout

**Estado actual: `HOLDOUT_LOCKED`. La partición fue abierta. Su lectura existe
en disco. No está publicada y no debe citarse como resultado hasta completar la
auditoría descrita más abajo.**

Este documento existe porque hay una discrepancia entre lo que se pidió
conservar y lo que el repositorio contiene, y ocultarla sería peor que
registrarla.

---

## 1. Qué pasó

La partición congelada `[2026-01-01, 2026-07-01)` **fue abierta** el
`2026-08-13T11:13:37Z`, ejecutando la Pieza 3 del encargo anterior, que pedía
explícitamente abrirla una sola vez sobre un candidato pre-declarado.

### 1.1 Qué candidato se evaluó

Leído de `reports/study_closure/final_holdout.json`, campo `provenance.candidate`:

| Campo | Valor |
|---|---|
| Familia | `volatility_breakout` |
| Activo | `BTCUSDT` |
| Temporalidad | `1h` |
| Motor de búsqueda | `random_search` |
| Ventana leída | `2026-01-01 00:00Z` … `2026-06-30 22:00Z` |

**Ese candidato ya estaba rechazado antes de abrir la partición.** `volatility_breakout`
es la familia con el p-valor crudo más bajo del estudio (0.345), y ese p-valor
falla el umbral más generoso concebible —N = 1, sin corrección alguna— por un
factor de siete. La corrección a nivel de estudio la rechaza bajo Holm y bajo
Benjamini-Hochberg, y su Sharpe se invierte de signo al pasar de BTC a ETH.
Véase [ADR 0015](../decisions/0015-r3-family-evaluation-negative.md) y
[study_level_multiple_testing.md](study_level_multiple_testing.md).

La apertura no era, por tanto, una prueba capaz de promover nada: era la prueba
confirmatoria de una hipótesis ya descartada.

### 1.2 Cronología

Horas en UTC; entre paréntesis la hora local (CEST, UTC+2) que muestra `git log`.

| Momento | Evento | Evidencia |
|---|---|---|
| `2026-08-13T11:00Z` (13:00) | Commit `02b79f1`: pre-declaración de la regla de selección y del candidato | git |
| `2026-08-13T11:13Z` (13:13) | Commit `31c241f`: máquina de evaluación de la Fase H | git |
| `2026-08-13T11:13:37Z` (13:13:37) | **Apertura de la partición** | `provenance.opened_at` |
| `2026-08-13T18:02Z` (20:02) | Commit `0a0bf92`: resultado registrado | git |
| `2026-08-13T18:26Z` (20:26) | Commit `0b6f002`: API del estudio, artefacto con las cifras embebidas | git |
| Posterior | Instrucción de conservar la Pieza 3 sin commitear — ya estaba commiteada | encargo |
| Posterior | Commit `4673b32`: bloqueo de publicación | git |

> **Discrepancia registrada.** El encargo que motiva esta revisión sitúa la
> apertura a las «12:04». Ningún artefacto ni commit del repositorio lleva esa
> marca: la única hora de apertura registrada es `11:13:37Z` (13:13 local). Se
> conserva aquí la hora que consta en la evidencia, no la del encargo, y se deja
> anotada la diferencia en lugar de reconciliarla en silencio.

Posteriormente se indicó conservar la Pieza 3 como cambio local sin commitear.
Para entonces ya estaba commiteada. No se ha reescrito el historial para
revertirlo: hacerlo destruiría la evidencia de procedencia, que es precisamente
lo que hace auditable una apertura. La cadena de commits **es** el registro.

| Commit | Contenido | Momento relativo a la apertura |
|---|---|---|
| `02b79f1` | Pre-declaración de la regla de selección y del candidato | **Antes** |
| `31c241f` | Máquina de evaluación de la Fase H | **Antes** |
| `0a0bf92` | Resultado registrado y conclusión del arco | Después |
| `0b6f002` | API del estudio, con el artefacto que embebía las cifras | Después |
| `4673b32` | **Bloqueo de publicación** | Después |

Que `02b79f1` sea anterior a la apertura es lo que permite comprobar que el
candidato estaba congelado antes de mirar. Esa propiedad se pierde si se
reescribe la historia.

---

## 2. Qué se ha hecho al detectarlo

La acción tomada es conservadora y reversible: **se bloquea la publicación, no
se destruye la evidencia.**

1. `scripts/build_study_dashboard.py` ya no embebe la lectura del holdout salvo
   que se pida con `--include-holdout`. El artefacto que consume la API se
   regeneró sin ella; se verificó que el hash del dataset, el retorno y la
   dispersión por semilla han desaparecido del fichero.
2. `/api/v1/study/holdout` devuelve `HOLDOUT_LOCKED` con `result`, `provenance` y
   `buy_and_hold` a `null`, más el periodo reservado, el motivo del aislamiento y
   los nueve requisitos de apertura.
3. La publicación exige que `PERP_LAB_HOLDOUT_PUBLICATION` valga exactamente
   `AUDITED_OPEN_FINAL_HOLDOUT`. Un valor "verdadero" cualquiera —`1`, `true`,
   `yes`— **no** desbloquea, porque esos valores se ponen sin pensar mientras se
   depura otra cosa. Hay un test que lo comprueba.
4. El panel del dashboard no renderiza ninguna métrica del holdout aunque el
   payload llegue poblado.
5. Los ficheros originales (`reports/study_closure/final_holdout.json` y `.md`,
   `docs/methodology/final_holdout_evaluation.md`) quedan intactos como
   evidencia científica.

Son dos cerrojos independientes —el artefacto y la capa de servicio— para que ni
una regeneración del fichero ni un flag olvidado publiquen por su cuenta.

---

## 3. Requisitos de la auditoría

Ninguno se da por cumplido en este documento. Cada uno debe verificarse
manualmente contra el repositorio y marcarse aquí con su evidencia.

| # | Requisito | Estado |
|---|---|---|
| 1 | Autorización explícita `OPEN_FINAL_HOLDOUT` registrada | **NO SE CUMPLE — verificado** |
| 2 | Commit anterior a la apertura con la regla de selección y el candidato | Aparente (`02b79f1`), sin verificar |
| 3 | Candidato congelado con sus parámetros exactos y su huella de selección | **Pendiente** |
| 4 | Configuración resuelta del experimento (costes, ejecución, anualización) | **Pendiente** |
| 5 | SHA-256 del dataset de holdout coincidente con el registrado antes de abrir | **Pendiente** |
| 6 | Comando ejecutado y logs de la ejecución | **Pendiente** |
| 7 | Artefactos generados por la lectura | Existen, sin verificar |
| 8 | Commit posterior que registre el resultado | Aparente (`0a0bf92`), sin verificar |
| 9 | Ausencia de modificaciones retrospectivas entre ambos commits | **Pendiente** |

El requisito 9 es el que de verdad importa. Todo lo demás puede fabricarse a
posteriori; lo que no se puede fabricar sin dejar rastro es que la
especificación no cambiara entre el commit que la congela y el que registra el
resultado.

### 3.1 Requisito 1: verificado y no cumplido

**No existía ninguna autorización cuando se abrió la partición.** Comprobado de
dos formas independientes:

1. `reports/study_closure/final_holdout.json` registra en `provenance` los campos
   `annualization_days`, `candidate`, `costs`, `dataset_hashes`, `git`,
   `is_research_result`, `opened_at`, `partition_evaluated` y `regime`. **No hay
   ningún campo de autorización ni de token.** La apertura no dejó constancia de
   haber sido autorizada porque no había nada que se la pidiera.
2. La única aparición operativa de `OPEN_FINAL_HOLDOUT` en el código es
   `src/perp_lab/api/settings.py:73`, y compara
   `PERP_LAB_HOLDOUT_PUBLICATION == "AUDITED_OPEN_FINAL_HOLDOUT"`. Es un cerrojo
   de **publicación**, no de apertura, y se introdujo en `4673b32`, es decir
   **después** de que la partición ya se hubiera abierto.

Dicho de otro modo: el control que hoy impide publicar la cifra no existía en el
momento en que se generó, y nunca hubo un control que impidiera generarla. La
protección se construyó a posteriori sobre un hecho ya consumado, y eso es
exactamente lo que este documento registra en lugar de disimular.

---

## 4. Qué muestra el dashboard mientras tanto

- Estado `HOLDOUT_LOCKED`.
- El periodo reservado, `[2026-01-01, 2026-07-01)`.
- El motivo del aislamiento: la partición se congeló antes de cualquier EDA,
  selección de familias o ajuste de parámetros, y publicar una cifra antes de
  comprobar que el candidato estaba congelado convertiría la prueba
  confirmatoria en una prueba más del estudio.
- La lista de requisitos de apertura.
- Una afirmación explícita de que **la ausencia de métricas es deliberada**, no
  un fallo de carga.

---

## 5. Consecuencia para la tesis

La conclusión del estudio **no depende** de esta lectura. El resultado es el
mapa de trece familias rechazadas bajo corrección a nivel de estudio, con PBO
cercano a 0.5 y ninguna superviviente, y ese resultado se sostiene entero sin
abrir la partición.

El holdout era la prueba confirmatoria de un candidato que ya había sido
rechazado por la corrección múltiple. Publicarlo o no cambia el énfasis de un
párrafo, no la conclusión.

### 5.1 La partición está consumida

Esta es la consecuencia que sí es cara, y conviene decirla sin rodeos.

Un holdout vale exactamente una lectura. La de `[2026-01-01, 2026-07-01)` ya se
gastó. **No queda ninguna partición final limpia en este conjunto de datos**, ni
para `volatility_breakout` ni para nada que se construya después.

Consecuencias operativas, vinculantes para todo trabajo posterior:

1. **Ninguna familia nueva puede reclamar una validación final** sobre este
   histórico. Las familias CRT y cualquier hipótesis futura se evalúan en
   desarrollo con walk-forward, y su resultado es y seguirá siendo un resultado
   de desarrollo.
2. **La lectura del holdout no puede usarse para construir, seleccionar ni
   ajustar nada.** Ni como criterio, ni como sanity check, ni como desempate. Ya
   no es una prueba independiente de nada.
3. **Recuperar una prueba confirmatoria limpia exige datos nuevos**: extender el
   corte más allá de `2026-07-01` y congelar una partición nueva, declarada antes
   de mirarla. Eso es trabajo futuro, no una casilla que se pueda marcar
   reinterpretando lo que ya hay.

Que el estudio cierre en negativo es lo que hace tolerable esta pérdida: no había
nada que confirmar. Habría sido mucho más grave con un candidato vivo.

---

## 6. Cómo se verificaron los commits de esta tanda

Nota de procedencia sobre los ocho commits temáticos del 2026-08-16
(`bddaf4c` … `c3f27bc`), añadida para que nadie deduzca una garantía que no se
dio.

**La puerta de calidad se ejecutó una vez, sobre el árbol completo**, no una vez
por commit: `ruff check`, `ruff format --check`, `pyright`, `pytest -m "not
network"` (1.329 pasan), `tsc --noEmit`, `next lint` y `next build`.

Los ocho commits son **subconjuntos disjuntos de ese mismo árbol de trabajo**. El
árbol no cambió entre ellos, así que re-ejecutar la puerta antes de cada uno
habría dado el mismo resultado; lo que **no** se hizo, y por tanto no se afirma,
es verificar que cada commit compila **de forma aislada**, con `git checkout` en
él y la puerta encima.

Lo que sí se comprobó es el **orden de dependencias**: los commits se
construyeron de modo que ningún fichero importe algo que llegue en un commit
posterior — en concreto, las páginas legales y `lib/legal.ts` preceden al stack
de autenticación, que importa `PRIVACY_POLICY_READY`.

Quien necesite la garantía por commit debe ejecutar `git checkout <sha>` y la
puerta en cada uno. No se ha hecho aquí.
