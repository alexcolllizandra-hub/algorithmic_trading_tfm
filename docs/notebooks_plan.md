# Plan de notebooks

Fecha: 2026-08-19. Punto de partida real: **no hay notebooks dispersos que
archivar**. Los cinco existentes son artefactos generados por
`scripts/build_*_notebook.py` (regla: `.cursor/rules/notebook-policy.mdc` — la
lógica vive en `src/perp_lab/`, los notebooks importan y narran). El problema
no es el orden: es el idioma (inglés, con la memoria en español) y el tono
(plantilla «Question → Method → Interpretation (2.1)» repetida ~40 veces).

## Secuencia propuesta

| # | Notebook | Builder | Propósito (una frase) | Inputs | Outputs / figuras (`reports/figures/`) | Alimenta |
|---|---|---|---|---|---|---|
| 01 | `01_datos_y_exploracion` | `build_eda_notebook.py` (reescribir prosa) | Qué aspecto tiene el mercado y si el dato es apto para el estudio | lake validado 5m/1h + funding | `eda/f01-f24, fa2` (25), tablas `eda/s1-s6, t01b-t39b` | Cap 4.1 y anexo EDA |
| 02 | `02_features_causales` | `build_features_notebook.py` (reescribir) | Qué puede saber el modelo y cuándo, y qué cuesta una fuga | frame de desarrollo | `features/g01-g09` | Cap 5.2 |
| 03 | `03_backtest_y_walk_forward` | `build_backtest_notebook.py` (reescribir) | Cómo una señal se convierte en posición pagando lo que se paga, y qué hace out-of-sample a un fold — con una familia de ejemplo de punta a punta | dev + configs | `backtest/h01-h06` | Caps 4.2-4.3, 5.4 |
| 04 | `04_busqueda_y_sobreajuste` | `build_search_notebook.py` (reescribir) | Cuánto de un resultado buscado es estructura y cuánto sesgo de selección | `artifacts/runs/r3_full_budget100_ga21/` | `search/i01-i06` | Caps 5.4-5.6 |
| 05 | `05_cierre_y_contraste_multiple` | `build_results_notebook.py` (reescribir) | Qué encontró el estudio completo y si algo sobrevive a la corrección | `reports/study_closure/*.json` | `closure/j01-j04` | Caps 6-8 |
| 06 | `06_meta_etiquetado_supervisado` | **nuevo** (`build_ml_notebook.py`) | ¿Puede un clasificador (LR, RF, LightGBM — el trío preregistrado) decidir cuándo actuar sobre una primaria, y qué separa mejora económica de capacidad predictiva? | `reports/meta_labeling_real/*.json` + dataset reconstruible | `ml/m01-m05` (nuevas: economía vs AUC por fold, calibración, SHAP, abstención) | Cap 5.8 y cap 6 (RQ3) |
| 07 | `07_monte_carlo_nula` | **nuevo** (Bloque C) | Situar la mejor estrategia rechazada dentro de la distribución del azar | ledgers de `volatility_breakout` en `r3_full_budget100_ga21/` | `montecarlo/k01-k05` (nuevas) | Cap 6/anexo — la figura-resumen del TFM |

Decisiones: se **archiva nada** (no existe legacy); se **reescriben los cinco
builders** (prosa, no lógica) y se **añade el 06**. Los nombres de figura
actuales son estables y ya están citados por tablas y web: no se renombran.

## Guía de estilo (vinculante para los builders)

1. ~~Español~~ **DECISIÓN 2026-08-19: INGLÉS en todo el repositorio** (código,
   notebooks, docs técnicos) — el repo y la plataforma son públicos e
   internacionales. Estado de migración: 07 ✅ EN; 05, 06 y 08 pendientes de
   retraducir; 01-04 ya estaban en EN (solo necesitan patrón+tono). ÚNICA
   excepción abierta: `docs/thesis/` (borradores de la memoria) sigue en
   español hasta que el autor confirme el idioma de entrega. Antes decía:
   Español, el idioma de la memoria. Términos técnicos consagrados se dejan
   en inglés la primera vez con traducción entre paréntesis.
2. Primera persona del plural, prosa continua. La pregunta se plantea como
   pregunta real, no como epígrafe de plantilla; la respuesta admite lo que
   queda sin resolver.
3. Prohibido: encabezados «Interpretation (N.M)», celdas de «Setup», banners,
   emojis, listas de viñetas donde cabe un párrafo.
4. El código de las celdas no cambia de contrato: importa de `perp_lab`, llama
   `save_figure`, no reimplementa lógica (la regla del proyecto ya lo exige).
5. Cada notebook abre con tres frases: qué pregunta responde, con qué datos y
   qué encontrará el lector al final — incluida la parte incómoda.

### Muestra canónica (aprobada 2026-08-18, sustituye al cierre del 05)

> Es fácil leer este resultado como «los mercados son eficientes» o «el trading
> algorítmico no funciona». Ninguna de las dos es lo que hemos demostrado.
>
> Lo que sí hemos demostrado es más estrecho y, creemos, más útil: dentro de un
> espacio bien acotado —trece familias interpretables, dos perpetuos líquidos,
> velas de una hora, seis años, un modelo de costes realista— una búsqueda
> rigurosa no encuentra nada que sobreviva a contar honestamente cuántas veces
> se ha mirado. Y esa acotación importa tanto como el hallazgo: cada límite es
> un sitio donde otro estudio, con otros datos u otra frecuencia, podría llegar
> a una respuesta distinta.
>
> ¿Por qué nos fiamos de este negativo? Por tres razones que se sostienen
> solas: el aparato se validó antes de usarse y detectó al instante una fuga
> plantada a propósito; la búsqueda tuvo presupuesto igual y verificado en cada
> familia; y el negativo lo confirman tres diagnósticos que no tenían por qué
> estar de acuerdo —contraste de hipótesis, Sharpe deflactado y PBO— y lo
> están.

## Orden de ejecución y coste

| Paso | Qué | Cuándo | Coste |
|---|---|---|---|
| 1 | Reescribir `build_results_notebook.py` (05) — el más corto y el patrón de los demás | ya (worktree `../tfm_notebooks`) | 2-3 h + ejecución rápida (lee JSON) |
| 2 | 04, luego 03, luego 02 | tras aprobar el tono del 05 | 2-4 h cada uno |
| 3 | 01 (builder de 4.928 líneas, ejecución más larga) | último de los reescritos | 4-6 h |
| 4 | 06 ML supervisado (builder nuevo) | tras validar patrón (hecho) | 3-4 h |
| 5 | 07 Monte Carlo | **hecho 19-08** (módulo + builder + determinismo 10/10) | — |
| 6 | 08 síntesis | **hecho 19-08** (12 figuras encadenadas, contrato verifica entradas) | — |
| 7 | Regenerar todo + versionar figuras (tras quitar `.gitignore:54`) | al cierre de la ronda CRT | 1 h |

Restricción operativa vigente: los `.ipynb` están trackeados; regenerarlos en el
árbol principal rompe la huella de la ronda en curso. Todo en worktree hasta que
`crt_v1_execution.json` marque `completed`.
