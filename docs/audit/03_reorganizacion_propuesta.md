# Reorganización propuesta

Fecha: 2026-08-19. Criterio: legibilidad para un tribunal al mínimo coste de
churn. Se descarta la reorganización general de `src/` — el paquete ya sigue una
arquitectura por capas coherente (datos → validación → features → estrategias →
backtest → búsqueda → evaluación → tracking) y moverlo invalidaría huellas de
identidad futuras y el `git blame` de la fase experimental.

**Precondición dura para TODO lo de abajo: que la ronda CRT_INTRADAY_V1 haya
terminado.** Cualquier movimiento en el árbol principal antes de eso mata la
reanudación (evidencia: `_DESCARTADO_huella_arbol_sucio/POR_QUE.md`).

## 1. Movimientos propuestos (tabla de → a)

| De | A | Motivo | Comando |
|---|---|---|---|
| `docs/roadmap.md` | (borrar; historia queda en git) | Se autodeclara superseded en su primera línea; `docs/roadmap/README.md` ya lo lista como tal | `git rm docs/roadmap.md` |
| `ingest.log`, `ingest2.log`, `perp_lab_repo.zip` (raíz) | (borrar) | No trackeados, ya ignorados (`.gitignore:40,85`); 3,9 MB de ruido en la primera pantalla del repo | `rm ingest.log ingest2.log perp_lab_repo.zip` |
| `.gitignore:54` (`reports/figures/*`) | (quitar la línea) | Las 51 figuras son evidencia de la memoria y deben versionarse (~15 MB) | editar `.gitignore` + `git add reports/figures` |
| `apps/api/` | `deploy/api/` o borrar | Contiene solo Dockerfile+README; el código real está en `src/perp_lab/api`. Como está, promete un servicio que no contiene | `git mv apps/api deploy/api` (si se conserva el Dockerfile) |
| `src/perp_lab/dashboard/` | sin mover ahora; post-defensa a `legacy/` | Streamlit v0 superseded por `apps/web`, pero borrar en caliente rompe el CLI `perp-lab dashboard` citado en `docs/research_dashboard.md` | post-TFM: `git mv src/perp_lab/dashboard legacy/dashboard_streamlit` + retirar el comando del CLI |
| `docs/thesis/` | reconstruir índice 01–10 en español | Hoy solo caps 6–8 con numeración antigua; el andamiaje completo es entregable del Bloque B | (Bloque B, no un mv) |

## 2. Lo que NO se mueve, y por qué

- `src/perp_lab/*`: la arquitectura por capas ya es el diagrama del capítulo 5.
  El coste (huellas, blame, imports, riesgo de romper 101 ficheros de test) supera
  cualquier ganancia estética.
- `artifacts/runs/search_*` (~300 dirs): son la evidencia primaria de los
  agregados. Un tribunal no los lee, pero su existencia es el argumento de
  reproducibilidad. Si el volumen molesta, la opción correcta es un índice
  (`artifacts/runs/INDEX.md` generado), no mover datos.
- Raíces fallidas (`r3_full/`, `r3_full_budget100/`, `crt_v1_ABORTED_*`,
  `_DESCARTADO_*`): retenidas deliberadamente por ADR 0015 §5 como procedencia de
  fallos de proceso. Moverlas destruiría justo lo que demuestran.
- Los 4 commits del incidente de holdout (`02b79f1→31c241f→0a0bf92→0b6f002`):
  intocables, regla inviolable del proyecto.

## 3. Consolidación de ramas (el problema real de estructura)

La dispersión que confundiría a un tribunal no está en las carpetas: está en que
`main` (11-08) no contiene el cierre del estudio. Orden de fusión propuesto, tras
el fin de la ronda CRT:

1. `feat/study-closure` → `main` (+29 commits: cierre, CRT V1, legal, landing).
2. `feat/m1m2-synthetic-validation` → `main` (ADR 0017, meta-labeling, stochastic).
3. `feat/meta-labeling-real-data` → `main` (RQ3 real; ya contiene el merge de 2).
4. `style/comment-pass` → `main` (comentarios validation/search, AST-safe).
5. `feat/s2-evidence-and-strategy-lab` → `main` (aprobado en sesión el 16-08).
6. Ramas a +0 de main (10): borrar. `chore/remove-thesis-manuscript-docs`: borrar
   sin fusionar (su decisión quedó revertida por el plan actual de memoria).
7. Worktrees `../tfm-dashboard-redesign` y `../tfm-outer-fold-leakage`: revisar
   commits únicos (+2 y +3), fusionar o etiquetar, y `git worktree remove`.

## 4. Orden de ejecución recomendado

1. (bloqueado por ronda) — fin de CRT V1.
2. Fusiones del §3 en ese orden; resolver `uv.lock` regenerando, como en el merge
   del 18-08.
3. Quitar `reports/figures/*` del `.gitignore` y versionar figuras.
4. `git rm docs/roadmap.md`; `rm` de los tres ficheros de la raíz.
5. Decisión `apps/api` (mover Dockerfile a `deploy/` o borrar).
6. Nota de obsolescencia en los 4 docs vivos con «holdout untouched»
   (`docs/roadmap/{future_architecture,gate_s1b_outcome,gate_s1_batch_01}.md` —
   `docs/roadmap.md` desaparece en el paso 4).
7. Fix de `identity.py` (diff restringido a `RELEVANT_DIRS`) con su ADR y su test,
   como primer commit de la fase post-ronda.

Coste total estimado de los pasos 2–7: una tarde. Nada de esto toca lógica de
investigación; todo es custodia y coherencia editorial.
