# Lista de correcciones para los capítulos 4 y 6 (y colindantes)

Resultado del barrido completo del repo (2026-08-28) buscando (a) los nombres
CRT inventados y (b) cualquier atribución de los resultados a controles de
riesgo no ejecutados (position sizing, límites de apalancamiento/exposición,
límites de trades diarios, lockouts, stops del motor). Cada punto dice qué se
encontró, dónde, y si ya está corregido en el repo o es una instrucción para
el texto redactado de la memoria (que vive fuera del repo).

## Capítulo 4 (arquitectura / MLOps)

1. **`docs/architecture.md` línea 64 — CORREGIDO en este commit.** Decía que
   el módulo `backtesting/` incluye "position sizing, leverage/exposure
   limits". Falso respecto al código; ahora dice explícitamente que el motor
   toma la posición emitida por la estrategia (fracción fija 1.0) y que los
   bloques `risk:`/`position_sizing` del config son provisionales y no
   consumidos.
2. **Figuras y tablas del cap. 4 — LIMPIAS, sin cambio.** Ni
   `scripts/build_ch4_figures.py` (mapa de módulos, ERD, ciclo de config,
   árbol de semillas) ni `docs/thesis/tablas_cap4.md` contienen ninguna
   mención a sizing, risk engine, lockouts o límites diarios. Verificado por
   grep sobre los términos: position sizing/position_sizing/risk engine/
   lockout/max_trades_per/max_daily/volatility_target/max_leverage/stop_loss.
3. **Instrucción para el TEXTO del cap. 4** (redactado fuera del repo): si
   alguna frase o diagrama del borrador describe el backtester con sizing,
   límites o stops de motor, reescribirla con la distinción de tres niveles:
   *arquitectura disponible* (el modelo de config y `crt/risk.py` existen y
   están testeados) / *controles realmente ejecutados* (next-bar-open, 4+1
   pb/lado, funding as-of-past, gates de señal que solo aplanan; CRT además
   su gestión de trade interna) / *pendiente de integración* (sizing por
   volatilidad, límites de riesgo, risk engine CRT — nunca conectados al
   motor en ninguna ronda). Fuentes: `NOTA_ACLARACIONES.md` §4.
4. **`configs/experiment.yaml:243-247` (bloque `risk:`) — DOCUMENTADO, no
   tocado.** Su comentario "Risk limits applied inside the backtester" es
   incorrecto respecto al código. No se edita antes de la entrega porque el
   YAML resuelto entra en el `config_sha256` de la identidad de cualquier
   run futuro; queda apuntado como corrección post-entrega. La memoria no
   debe citar ese comentario.
5. **`docs/methodology/strategy_specification.md` (v0.1) — NOTA AÑADIDA.**
   La spec pre-implementación prometía sizing por volatilidad y salidas ATR
   compartidas que las rondas ejecutadas no usan. El texto v0.1 se conserva
   intacto (es un documento histórico) y se le añade una nota "as-executed"
   fechada que impide citarlo como protocolo ejecutado.

## Capítulo 6 (validación estadística)

6. **Exportes del cap. 6 — LIMPIOS de atribuciones de riesgo.** Grep sobre
   `reports/thesis/chapter_06/` y los builders de los notebooks 04/05: sin
   menciones. Nada que corregir por este frente.
7. **Nombres CRT inventados — ELIMINADOS de todo el repo.** Tras la
   corrección del inventario, la única aparición restante de
   `crt_turtle_soup`/`crt_po3_expansion`/`crt_asia_range_fade`/
   `crt_ny_open_continuation`/`crt_liquidity_sweep_reversal` está en
   `reports/thesis/chapter_07/MANIFEST.md`, citados expresamente como
   nombres erróneos corregidos (registro de la reconciliación). Las tablas y
   figuras CRT (t10, j05, fig_7_4) se generan desde los artefactos y siempre
   usaron los nombres canónicos. **Instrucción para el texto**: si algún
   borrador de capítulo copió la lista antigua del inventario, sustituirla
   por el `frozen_order` de `crt_v1_execution.json`.
8. **`i06_convergence` — NO USAR con su rótulo actual.** Causa diagnosticada
   y paridad verificada al nivel de parquet (320 runs, 640 tablas, 9.600
   celdas pliegue×motor, cero violaciones) — ver `NOTA_ACLARACIONES.md` §5.
   Corrección post-entrega apuntada: re-rotular el eje del GA en
   `build_search_notebook.py` (o truncar la traza del GA a evaluaciones
   únicas) y regenerar el notebook 04. Si el cap. 6 cita la figura o su
   caption, retirar la cita hasta entonces; la afirmación "paridad de
   presupuesto verificada" debe citar la verificación por parquets, no i06.
9. **Alcance de las correcciones estadísticas — YA ACOTADO, mantener.** Las
   frases del cap. 6 sobre Holm/BH/DSR/PBO deben seguir refiriéndose SOLO al
   cierre de 13 familias; el resumen de 16 familias del cap. 7 (fig_7_6) no
   hereda esas correcciones (no calculadas para CRT/S3). Los scope notes ya
   están en ambos MANIFEST y en la sección 8 del notebook 05.

## Capítulo 3 (sin cambio, para constancia)

10. `docs/thesis/tablas_cap3.md:73-76` enmarca `max_leverage: 3.0`
    correctamente como restricción de fitness provisional durante la
    búsqueda, "no criterio de promoción" — y el notebook 07 declara
    explícitamente que no toca overlays de gestión de riesgo. Ambos están
    bien como están.

## Sobre repetir experimentos

Ninguna ronda ejecutada declaraba en su prerregistro los controles del risk
engine como parte del protocolo (los preregs congelados definen espacios sin
sizing ni límites; la spec v0.1 que sí los mencionaba es anterior a la
implementación y quedó superada por los espacios congelados — ver la nota de
procedencia en `ch7_hypotheses_rules.md`). Por tanto la exposición fija es
una **decisión de diseño documentada**, no una desviación de protocolo, y no
obliga a repetir comparaciones. Lo que sí obliga: que la memoria lo cuente
exactamente así.
