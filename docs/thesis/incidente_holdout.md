# El incidente del holdout

> Sección de memoria, escrita para ser leída por un tribunal. El registro
> operativo completo, con los nueve requisitos de auditoría y su estado, está
> en `docs/methodology/holdout_audit_status.md`; este texto lo resume sin
> suavizarlo. Fecha: 2026-08-19.

## Qué pasó

El diseño del estudio reservó desde el principio los últimos seis meses del
histórico, `[2026-01-01, 2026-07-01)`, como partición congelada para una única
prueba confirmatoria (ADR 0003). El protocolo preveía que su apertura
requiriera una autorización explícita y un candidato promovido y congelado de
antemano.

El 2026-08-13 a las 11:13:37 UTC la partición fue abierta sin que se cumpliera
ninguna de las dos condiciones. No existía candidato elegible —el estudio había
cerrado tres días antes con cero familias promovidas (ADR 0015)— y no existía
ningún control que exigiera la autorización: la verificación posterior
estableció que la procedencia de la lectura no registra campo de autorización
alguno, y que la única aparición operativa del token previsto es un cerrojo de
publicación (`src/perp_lab/api/settings.py:73`) introducido en el commit
`4673b32`, posterior a la apertura. El control que hoy impide publicar la cifra
no existía cuando se generó, y nunca hubo uno que impidiera generarla.

El candidato evaluado fue `volatility_breakout` sobre BTCUSDT a 1 hora, motor
random_search: la familia con el p-valor bruto más bajo del estudio (0.3455) y,
aun así, rechazada bajo cualquier umbral concebible, corregido o sin corregir.

## Cronología

| Momento (UTC) | Evento | Evidencia |
|---|---|---|
| 2026-08-13 11:00 | `02b79f1` — pre-declaración de la regla de selección y del candidato | git |
| 2026-08-13 11:13 | `31c241f` — máquina de evaluación de la fase final | git |
| 2026-08-13 11:13:37 | **Apertura de la partición** | `final_holdout.json`, `provenance.opened_at` |
| 2026-08-13 18:02 | `0a0bf92` — resultado registrado | git |
| 2026-08-13 18:26 | `0b6f002` — API del estudio con las cifras embebidas | git |
| Posterior | `4673b32` — cerrojo de publicación (`HOLDOUT_LOCKED`) | git |

Una discrepancia menor quedó registrada en lugar de reconciliarse en silencio:
el encargo que motivó la revisión situaba la apertura a las «12:04», hora que
no consta en ningún artefacto; la única marca registrada es 11:13:37Z.

La historia de git no se ha reescrito. Que `02b79f1` sea anterior a la apertura
es exactamente lo que permite comprobar que el candidato estaba declarado antes
de mirar; esa propiedad se destruiría reescribiendo el historial, que es la
razón por la que la cadena de commits se conserva intacta como registro.

## Por qué importa metodológicamente

Un holdout vale exactamente una lectura: su valor probatorio consiste en que
nada de lo que contiene ha influido en ninguna decisión previa. Una vez leído,
esa propiedad no se puede restaurar — ni repitiendo la lectura, ni prometiendo
no usarla. Por eso la respuesta al incidente no fue borrar, sino **retener y
bloquear**: la cifra existe en disco
(`reports/study_closure/final_holdout.json`), no se publica, no se cita como
resultado, y dos cerrojos independientes —el artefacto regenerado sin la
lectura y la capa de servicio, que exige un valor de entorno exacto y no un
booleano cualquiera— impiden que aparezca por accidente.

## Qué invalida y qué no

No invalida la conclusión del estudio. El veredicto negativo —cero familias de
trece supervivientes a la corrección múltiple, PBO 0.486, p mínimo 0.3455— se
construyó íntegramente sobre la partición de desarrollo y se sostiene sin la
lectura del holdout. La apertura fue la prueba confirmatoria de una hipótesis
ya descartada: publicar su cifra cambiaría el énfasis de un párrafo, no la
conclusión.

Sí invalida, y por completo, la posibilidad de una prueba confirmatoria limpia
sobre este conjunto de datos. La partición está consumida. Ninguna familia
posterior puede reclamar validación final sobre este histórico, y la ronda
CRT ejecutada después lo lleva codificado en su registro de ejecución
(`"promotion_possible": false`). Que el estudio cerrara en negativo es lo que
hace tolerable la pérdida: no había nada que confirmar. Con un candidato vivo
habría sido mucho más grave.

## Gestión hacia delante

Tres reglas vinculantes quedaron escritas para todo trabajo posterior
(`holdout_audit_status.md` §5.1): ninguna familia nueva reclama validación
final sobre este histórico; la lectura retenida no se usa para construir,
seleccionar ni desempatar nada; y recuperar una prueba confirmatoria exige
datos nuevos — extender el corte más allá de 2026-07-01 y congelar una
partición nueva, declarada antes de mirarla.

La lección de proceso también quedó implementada, no solo enunciada: los
cerrojos que faltaban existen ahora (con test que verifica que un `true`
casual no desbloquea), y la auditoría de nueve requisitos que decidirá si la
lectura llega a publicarse está definida con su estado actual: el requisito de
autorización, verificado y no cumplido; el crítico —ausencia de modificaciones
entre el commit que congela y el que registra— pendiente de verificación
formal.

Ocultar este episodio habría sido barato y habría destruido lo único que lo
hace recuperable: la procedencia. Se cuenta porque el proyecto sostiene que la
integridad de un resultado no es un estado que se declara, sino una propiedad
que se audita — y eso incluye los fallos del propio autor.
