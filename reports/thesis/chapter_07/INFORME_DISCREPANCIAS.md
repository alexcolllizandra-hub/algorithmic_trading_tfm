# Informe de discrepancias del paquete del capítulo 7 (2026-08-28)

Cada entrada: causa verificada → corrección → comprobación que la vigila.

## 1. Benchmark de las curvas ≠ benchmark de las tablas (fig_7_1 / 7_3 / 7_4)

**Síntoma.** `ch7_results_units.csv` implica capital final B&H ≈ 1,5227 (BTC)
y 0,7810 (ETH); las curvas terminaban en ≈ 2,0 y ≈ 1,0.

**Causa (verificada en código y numéricamente).** Dos definiciones distintas:
el B&H tabulado es el baseline **siempre-largo del perpetuo con costes y
funding** del estudio (`evaluation/baselines.py::_evaluate`, invocado por
`study_robustness.analyse_run`: `net = market − funding_por_barra` y una
entrada a 5 pb; el comentario del código lo declara: "charged the run's own
cost rate and funding so it is not given an artificially cheap execution").
Las curvas dibujaban `cumprod(1+oo_return)` = solo precio, sin funding ni
coste. La brecha es el coste de funding de un largo perpetuo en 3,7 años
(BTC: +100,66% solo-precio vs +52,27% fundado; ETH: +0,93% vs −21,90%).
Ninguna serie estaba «mal»: eran convenciones distintas, y la congelada por
el estudio (la que deciden los tests `beats_buy_and_hold`) es la fundada.

**Corrección.** Las curvas de benchmark de fig_7_1/7_3/7_4 (y las del
explorador web, que compartían el defecto) se derivan ahora de la receta
exacta del baseline fundado sobre el mismo ledger concatenado. Reproducción
verificada byte a byte antes del cambio: receta vs tabla, diff 0,00e+00 en
BTC y ETH (script efímero `verify_bh.py`, 2026-08-28). Leyendas y captions
dicen "buy & hold, funded perp"; el valor solo-precio queda documentado en
`ch7_figure_captions.md` como cantidad distinta que no se dibuja.

**Comprobación automática.** El builder ejecuta en cada regeneración 44
aserciones curva-vs-tabla (cada curva de semilla contra `total_return_net` y
cada benchmark contra `bh_total_return`) con **tolerancia explícita 1e-6
sobre el capital final**; una violación aborta la construcción. El exporter
web lleva la misma aserción por celda familia×activo.

## 2. El p = 0,06 de S1-B no existe en los artefactos

**Búsqueda.** Grep de `0.06/0,060` sobre reports/ y docs/: no aparece ningún
p=0,06 asociado a funding_reversal. Valores documentados: bootstrap unilateral
OOS del piloto (H0: media de retorno OOS ≤ 0, serie concatenada RS) =
**0,7455** (RS, motor primario) y 0,402 (GA, diagnóstico) en
`reports/gate_s1b/s1b_pilot_report.json`; BH sobre las 4 familias → 0
rechazos; p de familia del **cierre** (bootstrap estacionario recentrado,
otra prueba sobre otra agregación) = 0,738. Son análisis distintos y así se
distinguen en el brief.

**Origen probable.** Deriva de resumen conversacional de una sesión anterior,
propagada a `ch7_rounds_summary.md` y al inventario del cap. 6. Sin respaldo.

**Corrección.** Retirado de `ch7_rounds_summary` (builder), de
`INVENTARIO_MAESTRO.md/.csv` y de cualquier texto derivado, con nota de
retirada explícita para que no se reintroduzca desde borradores antiguos.

## 3. Interpretaciones de ronda afinadas (punto 3 del encargo)

- **R2**: "rejected under the pre-registered C1-C6 majority rules" → ahora
  "rechazada sobre los CUATRO criterios que su artefacto evalúa; drop-top y
  fold-locality NO EVALUADOS (posteriores a R2), ausentes, no fallidos".
  Respaldo: claves del JSON de R2 y `criteria: null` en el dashboard.
- **S3**: la frase "shifts below the carrier" queda acotada al **Sharpe medio
  por pliegue** exclusivamente, con la advertencia doble de no-emparejamiento
  y no-aislamiento causal. No se afirma nada de otras métricas.
- **Veto de actividad**: separado de los criterios en
  `ch7_activity_veto.csv` (30 celdas; el veto solo descalifica, nunca cuenta
  como séptimo criterio). Verificado: **0/30 celdas** lo dispararon (mínimo 5
  operaciones OOS cumplido en todas); los rechazos vienen de los criterios,
  no del veto.
- **Controles**: la distinción activo-vs-implementado-desactivado ya estaba en
  `ch7_hypotheses_rules.md` y se repite en el brief de redacción.

## 4. Estado de la partición final (punto 4)

Documentado en el brief con los registros existentes: abierta **una vez** el
2026-08-13 sobre un candidato ya rechazado, lectura en disco SIN AUDITAR,
publicación retenida (`HOLDOUT_LOCKED`), auditoría de nueve requisitos
pendiente (`docs/methodology/holdout_audit_status.md`). No se describe como
intacta; la apertura es una desviación del protocolo registrada, no una
confirmación válida, y la partición queda consumida.

## 5. Comprobaciones ejecutadas en este cierre

- Reproducción exacta del B&H fundado (diff 0) antes de tocar las curvas.
- Regeneración completa del paquete con las 44 aserciones activas.
- Doble ejecución del builder → artefactos byte-idénticos (ver MANIFEST).
- `ruff` limpio sobre los scripts tocados; suite pytest ejecutada.

## Pendiente (nada bloquea la redacción, se listan por honestidad)

- El `exit_reason` del ledger del motor no conserva los motivos internos CRT
  (stop/target/time): la fig. 7.7 anota la salida solo como registrada.
  Persistirlos requeriría re-ejecutar runs — fuera de alcance.
- `i06_convergence` sigue excluida hasta re-rotular el eje del GA
  (`CORRECCIONES_CAP4_CAP6.md` §8); la paridad de presupuesto está verificada
  por parquets, no por esa figura.
