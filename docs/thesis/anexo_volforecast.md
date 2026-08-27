# Anexo DL — Predicción de volatilidad: HAR vs LSTM (veredicto)

**Veredicto según la regla congelada: el LSTM NO añade valor sobre HAR.**
La regla (`docs/methodology/volforecast_spec.md`, fijada antes de entrenar
nada) exigía dos condiciones: (1) batir a HAR en QLIKE sobre el OOS
concatenado en **ambos** símbolos — se cumple — y (2) rechazo del test de
Diebold–Mariano al 5% a favor del LSTM en al menos uno — **no se cumple**
(BTC p = 0,091 con estadístico *a favor de HAR* en pérdida cuadrática;
ETH p = 0,647). Conclusión declarada por la regla: «no material improvement
over the classical benchmark».

**Diseño ejecutado sin desviaciones:** los 15 pliegues walk-forward del
estudio, partición de desarrollo vía DataLake, objetivo log RV(t+1…t+24),
HAR-RV (componentes 24/168/720h, OLS por pliegue en train+val), LSTM de una
capa (hidden 32, ventana 96, early stopping en validación, semillas
{42, 43, 44}), 32.400 barras OOS por símbolo. Artefactos:
`artifacts/volforecast/results.json` + parquets de predicciones OOS.
Figuras V1–V3 en `reports/figures/thesis_volforecast/` (espejo en
`figures/eda/`); veredicto calculado mecánicamente por
`scripts/build_volforecast_figures.py` → `values_volforecast.json`.

## Números (OOS concatenado, 15 pliegues)

| | naive | HAR | LSTM (media de semillas) |
|---|---|---|---|
| QLIKE BTC | 0,921 | 0,507 | **0,489** |
| QLIKE ETH | 0,738 | 0,469 | **0,428** |
| R² OOS vs naive, BTC | 0 | **0,307** | 0,290 |
| R² OOS vs naive, ETH | 0 | 0,293 | **0,298** |
| DM (HAR vs LSTM) | — | — | BTC: −1,69 (p 0,091) · ETH: +0,46 (p 0,647) |

Por semilla (QLIKE): BTC 0,507 / 0,511 / 0,475 · ETH 0,448 / 0,432 / 0,425 —
dispersión pequeña; la mejora del LSTM es consistente pero minúscula.

## Lectura honesta (tres frases para la memoria)

1. **La varianza es predecible — por cualquiera.** Ambos modelos recortan
   ~45% del QLIKE del naive y logran R² OOS ≈ 0,29–0,31 contra persistencia:
   confirmación directa del hallazgo de información mutua del cap. 5 (la
   dependencia medible vive en la volatilidad).
2. **El modelo profundo no separa del benchmark de 4 parámetros.** La ventaja
   en QLIKE (3–9%) no sobrevive al DM; en BTC la pérdida cuadrática incluso
   apunta al lado de HAR. Con 52k barras y esta señal, la jerarquía HAR ya
   captura casi toda la estructura explotable del RV horario.
3. **Y nada de esto es dirección.** El experimento pronostica *cuánto* se
   moverá el mercado, no *hacia dónde*; su éxito relativo, contrastado con el
   fracaso de las 14 familias direccionales (13 + S3), es la asimetría central
   de la tesis medida por tercera vía independiente.

Redacción sugerida (inglés) para el capítulo de trabajo futuro:

> A pre-registered deep-learning annex confirms the asymmetry from the other
> direction: next-24h realized volatility is forecastable by anything — a
> three-component HAR regression removes 45% of the naive QLIKE — but a
> sequence model adds no statistically separable margin over that classical
> benchmark (Diebold–Mariano p = 0.09 and 0.65), while every directional
> hypothesis, including the calendar-gated Gate S3 family, fails its frozen
> promotion criteria. Predictability in this market lives in the variance,
> is saturated by simple models, and does not extend to the sign.
