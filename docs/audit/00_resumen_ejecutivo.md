# Auditoría del repositorio — resumen ejecutivo

Fecha: 2026-08-19. Revisor: auditoría automatizada con verificación fichero a fichero.
`SUPUESTO:` entrega del TFM ~15 de septiembre de 2026, ~25 h/semana disponibles
(los dos huecos del encargo venían sin sustituir).

Alcance de este documento: los diez hallazgos que condicionan la defensa, ordenados
por impacto. El detalle y la evidencia completa están en `01_inventario_repo.md` y
`02_auditoria_calidad.md`.

## Los diez hallazgos

**1. La memoria no existe en un 80%.** `docs/thesis/` contiene 4.114 palabras
(capítulos 6–8) de las ~22.000 que necesita una memoria completa. Los capítulos 1–5
no existen en ninguna rama en español; el 5 existe solo en inglés en la rama
`feat/final-manuscript-integration`. Es el único riesgo capaz de suspender el TFM
por sí solo. Todo lo demás de esta lista es secundario frente a esto.

**2. La evidencia visual no está versionada.** `.gitignore:54` (`reports/figures/*`)
excluye las 51 figuras PNG+PDF que sostienen los capítulos de resultados. Existen
solo en un disco local. Un fallo de disco obliga a reejecutar cinco notebooks para
recuperarlas. Coste de arreglo: 1 línea de `.gitignore` + `git add` (~10 min).

**3. La huella de identidad hashea el árbol entero.**
`src/perp_lab/tracking/identity.py:111` calcula `git diff HEAD` sin restringir a
`RELEVANT_DIRS` (que sí se aplica a los untracked, línea contigua). Consecuencia
medida: tres muertes de la ronda CRT_INTRADAY_V1 el 17-08 por ediciones en
`apps/web` y docs, ~23 unidades de cómputo descartadas
(`artifacts/runs/crt_v1_budget100/_DESCARTADO_huella_arbol_sucio/POR_QUE.md`).
Arreglo pendiente con ADR propio; no aplicar hasta que cierre la ronda en curso.

**4. El trabajo clave vive fuera de `main`.** `main` está quieto desde el 11-08;
`feat/study-closure` va +29 commits. Diez ramas con trabajo sin fusionar, entre
ellas: ADR 0017 y toda la maquinaria de meta-labeling (rama
`feat/m1m2-synthetic-validation`), la respuesta a RQ3 sobre datos reales (rama
`feat/meta-labeling-real-data`, commit `7d00e9a`, 18-08) y la pasada de estilo de
comentarios (`style/comment-pass`). Un tribunal que clone `main` no ve nada de esto.

**5. Quedan afirmaciones obsoletas de «holdout intacto» en docs vivos.** El hecho
(holdout consumido el 13-08) está bien documentado en
`docs/methodology/holdout_audit_status.md`, pero lo contradicen documentos no
históricos: `docs/roadmap/future_architecture.md:278` («provably untouched»),
`docs/roadmap/gate_s1b_outcome.md:4`, `docs/roadmap/gate_s1_batch_01.md:93`,
`docs/roadmap.md:44`. Los ADR 0003/0006/0015 también lo dicen, pero son registros
históricos fechados: ahí lo correcto es la nota de estado (0006 y 0015 ya la
llevan), no la reescritura.

**6. El encargo de auditoría contiene tres premisas falsas — y eso es un hallazgo.**
(a) «notebooks antiguos de LightGBM, LSTM, Transformer, stacking, Optuna, DEAP»:
no existen; los únicos matches del grep son base64 de imágenes embebidas. Los cinco
notebooks de `notebooks/` son artefactos generados por `scripts/build_*_notebook.py`,
con secuencia 01–05 coherente. Estado: `DECLARADO PERO INEXISTENTE`.
(b) «API FastAPI todavía stub en apps/api»: `apps/api/` contiene 0 ficheros Python
(solo Dockerfile y README); la API real son 2.104 líneas en `src/perp_lab/api/`.
(c) «notebooks dispersos, de distintas épocas, sin hilo»: falso, ver (a).

**7. La web no consume la API.** `apps/web/src/lib/site-data.ts:147-159` lee JSON
estático de `/data/*.json` vía SWR; `apps/web/src/lib/evidence.ts` igual. La API de
`src/perp_lab/api` (montable con `perp-lab api`) no tiene ningún consumidor en la
web pública. Decisión pendiente: o la web declara su naturaleza estática (correcto
para publicar) o se cablea la API (solo tiene sentido para el panel interactivo).

**8. El denominador N=13 está declarado y el negativo es robusto a él.** Verificado
contra `reports/study_closure/study_level_multiple_testing.json`: p bruto mínimo
0.3455 (volatility_breakout), PBO 0.486 (70 particiones), Holm 0/13, BH 0/13, y la
sensibilidad del recuento (13 → 22 → 142 → 496.500) no cambia el veredicto. Las
familias CRT fuera del cierre están acotadas en
`docs/methodology/crt_intraday.md` §6bis. Ningún artefacto contradice los hechos
1–4 del encargo.

**9. RQ3 dejó de estar sin responder el 18-08.** El estudio de meta-labeling sobre
datos reales (`reports/meta_labeling_real/meta_labeling_real.{json,md}` en la rama
`feat/meta-labeling-real-data`) da: mejora del retorno neto en 4/4 folds
(−31,97% → +0,88%) con ROC-AUC 0.486 y PR-AUC lift 1.012 — es decir, sin capacidad
predictiva alguna: toda la mejora viene de abstenerse (tasa 0.75). Es evidencia
negativa adicional lista para la memoria, y cierra la pregunta de investigación
que quedaba abierta.

**10. Riesgo operativo de hardware sin diagnosticar.** El 18-08 a las 23:25 hubo
un reinicio sucio (Kernel-Power id 41: «se bloqueó o se interrumpió el suministro
eléctrico»), además del patrón previo de Modern Standby matando procesos en
segundo plano. Mitigado con checkpoint/resume (solo se perdió 1 unidad de ~18) y
un heartbeat de entrada sintética, pero la causa física (alimentación, temperatura)
solo puede comprobarla el autor. Mientras la ronda CRT corre, el árbol principal
no puede tocarse: toda esta auditoría se escribió en el worktree `../tfm-audit`.

## Lectura de conjunto

El aparato metodológico es la parte fuerte del proyecto y está por encima del
estándar de un TFM: corrección por contraste múltiple exhaustiva, aislamiento por
fold verificado por auditoría (100/100 runs), contratos de datos con hash, y un
resultado negativo que se sostiene sin corregir (p mínimo 0.345). Los riesgos
reales no son metodológicos: son de **documento** (hallazgo 1), de **custodia de
evidencia** (hallazgos 2 y 4) y de **coherencia editorial** (hallazgos 5–7).
La prioridad racional hasta la entrega es: memoria > consolidar ramas y versionar
figuras > correcciones editoriales > todo lo demás.
