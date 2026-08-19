# Capítulo 4 — Diseño experimental (borrador)

> Borrador escribible-ya del 2026-08-19. Cifras verificadas contra los
> artefactos citados; huecos marcados. Figuras referidas por su ruta.

## 4.1 Datos y activos

El estudio trabaja sobre los futuros perpetuos USDⓈ-M de Binance para BTCUSDT y
ETHUSDT. La serie base son velas de 5 minutos descargadas del repositorio
público del exchange con verificación de checksum; las temporalidades de 15
minutos y 1 hora no se descargan, sino que se construyen por resampleo
determinista de la base, de modo que no pueda existir inconsistencia entre
temporalidades (contrato en `configs/data_contract.yaml`). Cada dataset queda
descrito por un manifiesto con origen, periodo, número de filas y hash SHA-256
(`data/manifests/`), y ese hash es el que las capas posteriores verifican antes
de computar.

La partición de desarrollo cubre de 2020-01-01 a 2025-12-31 (52.608 barras
horarias por activo, sin nulos OHLC); el corte superior del histórico es
2026-07-01, exclusivo. Los últimos seis meses, `[2026-01-01, 2026-07-01)`,
se congelaron desde el inicio como partición reservada para una única prueba
confirmatoria (ADR 0003). El destino de esa partición se trata en el capítulo
de limitaciones y en el registro del incidente (`incidente_holdout.md`): fue
abierta una vez, el 2026-08-13, y está consumida.

La calidad del dato se valida en dos niveles: esquemas estructurales estrictos
—columnas, tipos, rangos; una columna inesperada es un fallo, no un aviso
(`src/perp_lab/validation/schemas.py`)— y un informe de calidad que cuenta
huecos, duplicados, violaciones OHLC y retornos extremos. Los extremos se
marcan y nunca se eliminan: decidir si un movimiento de 10 desviaciones es un
error de feed o un evento real es una decisión de análisis, y queda documentada
en el EDA en lugar de tomarse en silencio (`validation/quality.py`).

*(Figuras: cobertura mensual `reports/figures/eda/f02`, estructura de huecos
`eda/f01`.)*

## 4.2 Unidad experimental y particionado temporal

La unidad de análisis es la terna (configuración de estrategia, activo,
temporalidad), evaluada sobre los folds out-of-sample de un esquema walk-forward
expandido y anclado: 730 días iniciales de entrenamiento, 90 de validación, 90
de test, avanzando 90 días por fold (`configs/experiment.yaml:133-139`). Sobre
el histórico de desarrollo esto produce 15 folds cuyas ventanas de test son
contiguas y disjuntas: concatenadas, tilan el periodo 2022-03-31 a 2025-12-09
sin huecos ni solapes, lo que permite tratar la serie out-of-sample como una
serie contigua.

Entre entrenamiento y evaluación se interponen dos guardas derivadas —no
elegidas a ojo— del horizonte de etiquetado y del periodo máximo de
mantenimiento: la purga se descuenta del final de la ventana de validación y el
embargo, que la subsume, del final de la de entrenamiento
(`src/perp_lab/validation/walk_forward.py`). Ningún fold puede tocar la
partición reservada: la comprobación lanza excepción, no un aviso.

*(Figura: geometría `reports/figures/backtest/h05_walk_forward_geometry.png`;
tabla de disjunción `reports/tables/backtest/t06`.)*

## 4.3 Modelo de ejecución y costes

Toda señal se decide con la vela cerrada y se ejecuta en la apertura de la
siguiente (semántica next-bar; retorno open-to-open). Los costes son taker
4 bps más deslizamiento 1 bp por lado —declarados provisionales en ADR 0005— y
el funding se paga o cobra de forma realizada, alineado como dato del pasado.
Un giro de largo a corto mueve dos unidades de nocional y se cobra como dos.
Si un experimento exige funding y la serie no está disponible, el motor falla
en lugar de suponer cero (`src/perp_lab/backtesting/engine.py`).

La sensibilidad del resultado a estos supuestos no se delega a la discusión:
está medida. El barrido de coste por vuelta y la cuña bruto/neto por rotación
son artefactos del estudio (`reports/tables/backtest/t02`, `t03`; figuras
`backtest/h02`, `h03`), y la batería de robustez re-precia cada candidato a
2× comisión y 2× deslizamiento.

## 4.4 Presupuesto de búsqueda y su contabilidad

Cada motor de búsqueda dispone del mismo presupuesto de evaluaciones únicas del
objetivo —100 por fold y motor en las rondas cerradas—, donde «única» excluye
propuestas inválidas, duplicados y aciertos de caché, que se contabilizan por
separado (`src/perp_lab/search/outcome.py::Counters`). El presupuesto se declara
en configuración y nunca se infiere del consumo (`search/config.py`); cuando la
cardinalidad finita de un espacio es menor que el presupuesto declarado, el
faltante se reporta en lugar de disimularse (ADR 0014,
`search/space.py::finite_cardinality`).

Esta contabilidad es la que después alimenta la corrección por contraste
múltiple: el estudio cerrado registra 436.092 evaluaciones válidas de 496.500
examinadas (`docs/methodology/crt_intraday.md`, recuento medido y congelado), y
el veredicto se re-verifica bajo cuatro definiciones del número de pruebas.

## 4.5 Criterios de decisión pre-registrados

La promoción de una familia exige superar simultáneamente seis criterios en los
dos activos, cada uno con mayoría de 6 sobre 10 semillas: retorno total
positivo; intervalo bootstrap del Sharpe que excluya el cero sobre el ledger
out-of-sample concatenado; supervivencia a costes doblados; superar a comprar y
mantener sobre la misma cobertura; sobrevivir a la eliminación de las cinco
mejores operaciones; y no estar confinada a un único fold. Cualquier criterio
de rechazo la elimina por sí solo. El contrato completo está congelado en
`docs/roadmap/phase_gates.md` y su aplicación en
`src/perp_lab/evaluation/study_robustness.py`; el veredicto de la ronda
principal, en ADR 0015.

Dos reglas de gobernanza completan el diseño: una familia rechazada no se
reajusta para que pase, y un resultado negativo riguroso es un desenlace válido
del estudio — ambas anteriores a conocer resultado alguno
(`docs/roadmap/README.md`, «Ground rules»).
