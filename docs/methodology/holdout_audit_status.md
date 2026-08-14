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
| 1 | Autorización explícita `OPEN_FINAL_HOLDOUT` registrada | **Pendiente de verificar** |
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
