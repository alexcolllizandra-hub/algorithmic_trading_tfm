# Capítulo 5 — Mapeo, valores [VALOR], tablas 5.1–5.3 y hallazgos que corrigen el borrador

**Fuentes:** todo sale de `scripts/build_ch5_figures.py` (semilla 42, solo
partición de desarrollo vía `DataLake`, que lanza `HoldoutLeakageError` ante
cualquier fuga) y de los artefactos ya congelados del notebook 01
(`reports/tables/eda/`). El builder escribe cada número usado aquí en
`reports/figures/thesis_ch5/values_ch5.json`; ninguna cifra de este documento
está escrita a mano. Figuras: `reports/figures/thesis_ch5/fig_5_1 … fig_5_16`
(PNG+PDF).

---

## 🔴 Hallazgos reales que OBLIGAN a reescribir frases del borrador

Regla acordada: el texto se reescribe con el hallazgo, nunca al revés.

**R1 — Ljung–Box SÍ rechaza en los retornos crudos.** El borrador dice
«Ljung–Box fails to reject the no-autocorrelation null on returns». Falso con
n = 52 607: p = 2,9·10⁻²⁵ (BTC) y 7,7·10⁻²³ (ETH) a 24 retardos. La lectura
correcta es la distinción significancia/magnitud: la ACF lag-1 es −0,017 (BTC)
y −0,008 (ETH) — con muestras de este tamaño cualquier desviación microscópica
es «significativa», pero un coeficiente de −0,02 sobre un coste de ida y
vuelta de 10 pb no es estructura explotable. Redacción sugerida:

> With 52,607 hourly observations, Ljung–Box formally rejects the
> no-autocorrelation null even on raw returns (p ≈ 10⁻²⁵); the rejection,
> however, rests on autocorrelations of at most |0.02| — statistically
> detectable, economically negligible against a 10 bps round trip — whereas
> the same test on squared returns rejects with autocorrelations an order of
> magnitude larger and persistent across dozens of lags.

**R2 — El condicional de funding NO es nulo en BTC: el decil más negativo
predice rebote.** El borrador estaba redactado para acomodar un nulo. El dato
(Fig. 5.10, horizonte 8 h tras cada settlement, IC bootstrap por bloques de
24 barras, 500 remuestreos): decil 1 (funding más negativo) BTC
**+25,2 pb [10,8, 37,6]** — el IC excluye cero; el decil 10 (más positivo) da
−5,0 pb [−21,8, 11,4], indistinguible de cero. En ETH nada sale del cero
(decil 1: +10,3 [−7,3, 28,0]). Lectura honesta: el único condicional que
sobrevive al bootstrap es «funding extremadamente negativo → rebote medio en
BTC», episódico (los settlements muy negativos se concentran en los crashes) y
asimétrico. Esto es exactamente la hipótesis de la familia `funding_reversal`
del cap. 7 — que aun así no superó los criterios de promoción — y la lectura
S1 (p crudo 0,060). Conviene contarlo como coherencia descriptivo→confirmatorio.

**R3 — ADF sobre el log-precio de ETH es límite.** p = 0,045: rechaza la raíz
unitaria justo al 5% (BTC: p = 0,387, no rechaza). KPSS rechaza estacionariedad
en ambos precios (p = 0,01) y ambos tests coinciden en que los retornos son
estacionarios. La frase «prices are non-stationary, returns are stationary»
vale, pero cítala vía KPSS + ADF-BTC y anota el borderline de ETH — un tribunal
con la tabla delante lo verá.

**R4 — El Hurst rodante nunca baja de 0,5.** El borrador esperaba oscilación
alrededor de 0,5. Real: global 0,548 (BTC) / 0,545 (ETH); rodante en ventana de
180 días siempre en **[0,516, 0,607]** (BTC) y [0,513, 0,596] (ETH). Es
persistencia leve y estable, no ruido alrededor de 0,5 — pero sin excursiones
sostenidas que anclen una estrategia, y coherente con VR < 1 no significativo
(la persistencia de |r| domina el estimador R/S). Redactar «oscillates in a
narrow band just above 0.5 (0.52–0.61), mild persistence that never
consolidates».

**R5 — Ajuste t vs índice de cola: tensión que hay que contar.** El ajuste ML
de la t de Student da **df ≈ 2,0** (BTC 1h: 1,96; 5m: 1,99; ETH 1h: 2,14),
mientras Hill sobre el 2% superior da **α = 2,88 ± 0,09 (BTC) y 3,06 ± 0,09
(ETH)**. No es contradicción — el ML pondera el centro, Hill solo la cola —
pero el capítulo debe citar cada número para lo suyo: la t(≈2) como la forma
que sigue los cuantiles empíricos (Fig. 5.3), α ≈ 3 como el índice de cola
(Fig. 5.13). Con α ∈ (2, 4): varianza finita, cuarto momento frágil — la
kurtosis es descriptiva, no asintóticamente fiable, tal como dice el texto.

**R6 — Engle–Granger no rechaza en ninguna ventana.** Full sample p = 0,875;
por régimen: 0,872 / 0,746 / 0,651 / 0,307 / 0,572. El borrador dejaba abierto
«[rechaza/no rechaza] … sub-period results are unstable». Real: **no hay
evidencia de cointegración BTC–ETH ni en el total ni en ningún régimen** — los
p-valores se mueven mucho (0,31–0,87) pero nunca cruzan el umbral. Para las
familias cross-asset del cap. 7 el aviso es más fuerte que el redactado: no es
que la relación sea inestable, es que nunca llega a establecerse.

**R7 — IM: «uniformly small» necesita matiz.** Las features de *nivel*
(sma_24/96, atr_14) se excluyen de la medición — su IM aparente con retornos a
horizonte largo refleja no-estacionariedad compartida (precio≈época), no
estructura predictiva. Sobre las 11 features estacionarias la dependencia que
queda es real pero está concentrada en las features de volatilidad y crece con
el horizonte — es predictibilidad de *varianza*, no de dirección — exactamente
la asimetría que el capítulo declara como hecho central. (Números exactos en
la sección 5.7 de abajo.)

---

## Mapeo notebook/módulo existente ↔ capítulo 5

El notebook 01 es capa fina generada (`scripts/build_eda_notebook.py`); la
lógica vive en `src/perp_lab/eda/` (24 submódulos, ya testeados). Lo único
suelto en el builder son helpers de trazado y un `_longest_constant_run`
menor. Lo AÑADIDO en esta entrega está en negrita.

| Sección | Ya existía (módulo / artefacto congelado) | Añadido para el capítulo |
|---|---|---|
| 5.1 inventario/cobertura | `coverage.py`; s1/s2 (cobertura 100%, 0 huecos/duplicados/OHLC), t04–t10 | Fig 5.1 (cobertura mensual + incidentes) |
| 5.2 distribuciones | `returns.return_stats` (con Jarque–Bera), s3, f05 | **`distributions.py`**: ajuste t, kurtosis por agregación, supervivencia, **Hill**; Figs 5.2–5.4, 5.13 |
| 5.3 dependencia/volatilidad | `dependence.autocorrelation`, `stationarity.py` (ADF/KPSS/LB/ARCH-LM), s4, t20, t17 | **`hurst_rs` + rodante, `variance_ratio` Lo–MacKinlay robusto, `leverage_effect`**; **regímenes por FECHA en `regimes.MARKET_REGIMES` + `market_regime_stats`**; Figs 5.5–5.6, 5.14; Tablas 5.2–5.3 |
| 5.4 estacionalidad | `seasonality.py`, t24–t25, fa2 | Figs 5.7–5.8 (perfil intradía, heatmap) |
| 5.5 funding | `funding.py` (dinámica, ACF, relación leak-free t28), t26–t27 | Fig 5.9; **condicional por decil con bootstrap por bloques** (Fig 5.10) |
| 5.6 cross-asset | `correlation.py`, `leadlag.py`, t29–t30 | **`cointegration.py` (Engle–Granger, total y por régimen)**; Fig 5.11 |
| 5.7 features/labels | `perp_lab.features` (motor causal), t02/t06/t07 (2 pares ρ≥0,9) | **`eda/features.py`**: matriz de correlación, **PCA scree, IM por horizonte con suelo por permutación, resumen de labels triple-barrera**; Figs 5.12, 5.16 |

Verificaciones exigidas por la spec, todas en verde:

- **Guard de partición:** ya existía (`datasets.assert_no_holdout` +
  `HoldoutLeakageError`, con test). El builder y `build_feature_frame` lo
  invocan explícitamente.
- **Estimadores contra sintéticos** (`tests/unit/test_eda_ch5.py`, 19 tests):
  ruido blanco → ACF plana, VR≈1, Hurst≈0,5; AR(1) → VR>1 y Hurst>0,5
  significativos; GARCH simulado → ARCH-LM rechaza; paseo aleatorio → ADF
  mantiene raíz unitaria en niveles y rechaza en diferencias; Pareto α=3 →
  Hill recupera α; t(4) simulada → el ajuste recupera df; par cointegrado →
  EG rechaza / paseos independientes → no; IM con dependencia → supera el
  suelo, sin dependencia → se queda en él.
- **Determinismo:** semilla 42 en bootstrap, permutaciones y submuestreo.
- **Cacheo:** labels e IM a parquet por hash de configuración en
  `reports/cache/eda_ch5/`.

---

## Los [VALOR] del capítulo, por sección

### 5.1 Inventario y cobertura

| Hueco | Valor verificado | Fuente |
|---|---|---|
| Barras totales por dataset | 5m: **631.296** · 15m: **210.432** · 1h: **52.608** por símbolo (desarrollo); funding: 6.576 eventos/símbolo | s1/s2; manifiestos |
| Cobertura / huecos / duplicados / OHLC | **100% · 0 · 0 · 0** en los seis datasets | s2 |
| Barras de volumen cero | BTC **66** / ETH **47** (5m) | s2; Fig 5.1 |
| Meses de concentración | 2021-03 (11), 2022-05 (12), 2023-09 (3), **2023-11 (19, solo BTC)**, 2024-10 (16), 2025-01 (2), 2025-08 (3) — idénticos en ambos símbolos salvo 2023-11: eventos a nivel de exchange | values_ch5: zero_vol_months |

### 5.2 Distribuciones y colas

| Hueco | Valor | Fuente |
|---|---|---|
| Exceso de curtosis 1h | BTC **57,1** · ETH **32,5** | Tabla 5.1 |
| Jarque–Bera | rechaza con p < 10⁻¹⁶ en los seis dataset (estadístico BTC 1h 7,2·10⁶) | Tabla 5.2 |
| df del ajuste t | BTC 1h **1,96** (5m 1,99 · 15m 1,99) · ETH 1h 2,14 | Fig 5.3; R5 |
| Curtosis por horizonte (BTC) | 5m 170,7 → 15m 76,4 → 30m 59,5 → 1h 57,1 (monótona); ETH 594,8 → 42,4 → 35,6 → 32,5 | Fig 5.4 |
| Hill α̂ | BTC **2,88 ± 0,09** · ETH **3,06 ± 0,09**, sobre el **2%** superior (k≈1.052) | Fig 5.13 |
| Rango sugerido «[2–4]» | confirmado: α ∈ (2,4) — varianza existe, momentos altos frágiles | R5 |
| Asimetría de colas | skew 1h −1,03 (BTC) / −1,01 (ETH); media de las 10 mayores pérdidas horarias **11,3%** vs 10 mayores ganancias 9,3% (BTC); 13,3% vs 9,4% (ETH); máximos −20,71% vs +15,08% (BTC), −24,46% vs +14,62% (ETH) | values_ch5; t16 |
| Fechas de eventos extremos | **2020-03-12/13** (COVID, ambos activos simultáneos), 2021-01-29, 2021-02-08, **2021-05-19**, 2020-05-10 — top-15 BTC: todos con extremo simultáneo en ETH | t16 |

### 5.3 Dependencia temporal

| Hueco | Valor | Fuente |
|---|---|---|
| Lags significativos en retornos | ACF lag-1 **−0,017** (BTC) / −0,008 (ETH); algún pico aislado fuera de banda (±1,96/√n = ±0,009); LB rechaza (R1) pero magnitudes ≤ |0,03| | Fig 5.5; t20 |
| ACF de \|r\| / r² | lag-1 0,296 / 0,169 (BTC), 0,283 / 0,182 (ETH); \|r\| sigue > 0,11 a 100 retardos | Fig 5.5; t20 |
| ARCH-LM | rechaza, p < 10⁻¹⁶ (estadístico ≈ 4.258 BTC / 4.172 ETH, 12 lags) | s4 |
| ADF/KPSS | ver Tabla 5.2 y R3 | |
| Hurst global | BTC **0,548** · ETH **0,545**; rodante 180d en [0,516, 0,607] / [0,513, 0,596] (R4) | Fig 5.14 |
| VR(q) horizontes | 2–48 barras; BTC VR: 0,983 → 0,920, ETH 0,992 → 0,966; **todos < 1 (reversión leve), ninguno significativo** (peor z robusto −1,59 en q=8) | Fig 5.14 |
| Descripción VR sugerida | «dip mildly below one across all horizons — at most 8% below at q=48 — never beyond the robust bands (all \|z\| < 1.6)» | values_ch5: vr_* |
| Factor de volatilidad entre regímenes | rodante 30d BTC: mín 0,222 → máx 1,885 anualizada = **×8,5** | Fig 5.6 |
| Leverage effect | corr(r_t, RV siguiente 24h): **−0,040** (BTC) / **−0,049** (ETH) — signo equity-like pero magnitud casi nula; coherente con la literatura cripto que lo reporta débil | values_ch5 |
| Volumen–volatilidad | Spearman contemporáneo volumen vs \|r\| 1h: **0,528** (BTC) / **0,462** (ETH); coincide con t23 del notebook (0,528/0,463) | Fig 5.15 |
| Contraste más llamativo Tabla 5.3 | vol anualizada BTC 2022 (contracción) 0,63 vs 2024–25 (institucional) 0,44; y curtosis del crash COVID 94,0 en solo 2.183 barras | Tabla 5.3 |

### 5.4 Estacionalidad

| Hueco | Valor | Fuente |
|---|---|---|
| Horas de concentración | pico **13–15 UTC** (solape EU/US; máx 14:00) | Fig 5.7 |
| Horas más tranquilas | **04–06 UTC** (mín 05:00) | Fig 5.7 |
| Fin de semana | volumen **−40,4%**, \|r\| media **−30,5%** vs laborables (BTC 1h) | Fig 5.8 |
| Otro efecto | nada direccional; solo estructura de actividad (Kruskal–Wallis por hora ya en t25) | t25 |

### 5.5 Funding

| Hueco | Valor | Fuente |
|---|---|---|
| Persistencia ACF | lag-1 **0,796**; sigue fuera de banda los **60** settlements medidos (> 20 días) — «days to weeks» confirmado; rachas de signo medias 7,96 settlements (≈ 2,7 días) | Fig 5.9; t26 |
| Horizonte del condicional | **8 h** (un intervalo de settlement) | Fig 5.10 |
| Patrón condicional | **R2**: decil más negativo BTC +25,2 pb [10,8, 37,6]; resto ≈ 0; ETH nada excluye cero | Fig 5.10 |
| Descripción con IC | «concentrado en el extremo negativo de BTC y en pocos episodios; el resto indistinguible de cero» | R2 |

### 5.6 Cross-asset

| Hueco | Valor | Fuente |
|---|---|---|
| Correlación total 1h | **0,839** (Pearson; Spearman 0,820, t29) | Fig 5.11 |
| Banda rodante 30d | **[0,71, 0,92]** (p5–p95); comprime hacia arriba en alta volatilidad (0,77 low → 0,86 high, t30) | Fig 5.11 |
| Lead-lag | pico exactamente en lag 0 (0,839); máximo fuera de cero **0,018** — sin lead-lag explotable a 1h | Fig 5.11 |
| Engle–Granger | **no rechaza en ninguna ventana** (R6): full 0,875; por régimen 0,872/0,746/0,651/0,307/0,572 | values_ch5 |

### 5.7 Features y labels

| Hueco | Valor | Fuente |
|---|---|---|
| Nº features / pares \|ρ\|≥0,9 | 14 features del set congelado; **2 pares**: sma_24~sma_96 (0,999) y price_dist_sma_48~zscore_48 (0,941) — coincide con t07 del notebook 02 | Fig 5.12 |
| PCA | primeros 3 componentes **56,2%**; se necesitan **8 de 14** para el 90% | Fig 5.12 |
| IM (rango, features estacionarias) | **[0.000, 0.119]** nats (h ∈ {1,4,24}, submuestra determinista 1-de-2, suelo por permutación con semilla 42) | Fig 5.16 |
| IM sobre el suelo en h=1 | **9** de 11 features estacionarias | values_ch5 |
| Curva por horizonte | la IM de la feature de volatilidad (rvol_96) CRECE con el horizonte (72 → 172 millinats de h=1 a h=48): predictibilidad de varianza, no de direccion; las features direccionales (momentum_12, price_dist_sma_48) decaen hacia el suelo sin tocarlo (19-43 millinats). Frase sugerida: «the only curves that rise with horizon belong to volatility features - the dependence the feature set carries is about how much the market will move, not where» | Fig 5.16 |
| Balance de labels | **49,6% +1 / 50,4% −1 / 0,0% neutros** (umbral 0 pb) — sin necesidad de maquinaria de desbalanceo, como dice el texto | values_ch5: labels_btc |
| Tiempo a resolución | mediana **9 barras** (media 10,8) de un máximo de 24 | ídem |
| Barrera vertical | solo **14,6%** expira en la vertical (43,0% superior, 42,3% inferior) — con barreras de 2 ATR la mayoría de eventos resuelve en precio | ídem |
| Definición de los labels | triple barrera del protocolo (2,0/2,0 ATR14/precio, vertical 24 barras, `exit_fill="next_open"`), costes del estudio (4+1 pb/lado + funding realizado), eventos = todas las barras de desarrollo BTC 1h en largo (52.569 eventos) | builder |

---

## Tabla 5.1 — Estadística descriptiva de retornos log (desarrollo)

| Symbol | Timeframe | n | Mean (bps) | Std (bps) | Skew | Exc. kurtosis | Min (%) | Max (%) |
|---|---|---|---|---|---|---|---|---|
| BTCUSDT | 5m | 631,295 | 0.040 | 20.62 | -0.55 | 170.7 | -11.05 | 14.92 |
| BTCUSDT | 15m | 210,431 | 0.119 | 34.59 | 0.24 | 131.8 | -13.45 | 21.26 |
| BTCUSDT | 1h | 52,607 | 0.476 | 67.30 | -1.03 | 57.1 | -20.71 | 15.08 |
| ETHUSDT | 5m | 631,295 | 0.050 | 26.94 | -1.71 | 594.8 | -32.27 | 27.01 |
| ETHUSDT | 15m | 210,431 | 0.149 | 44.57 | -0.07 | 69.2 | -14.04 | 21.04 |
| ETHUSDT | 1h | 52,607 | 0.597 | 86.97 | -1.01 | 32.5 | -24.46 | 14.62 |

## Tabla 5.2 — Batería de tests (1h, por símbolo)

| Test | Series | BTC | ETH | Reading |
|---|---|---|---|---|
| Jarque–Bera | returns | 7.16e+06 (p < 1e-16) | 2.32e+06 (p < 1e-16) | normality rejected |
| Ljung–Box (24) | returns | p = < 1e-16 | p = < 1e-16 | rejects — but the underlying ACF is economically negligible (lag-1 ≈ −0.02) |
| Ljung–Box (24) | squared returns | p < 1e-16 | p < 1e-16 | strong volatility clustering |
| ARCH-LM (12) | returns | p < 1e-16 | p < 1e-16 | conditional heteroskedasticity |
| ADF | log price | p = 0.387 | p = 0.045 | unit root kept (ETH borderline at 5%) |
| ADF | returns | p < 1e-16 | p < 1e-16 | returns stationary |
| KPSS | log price | p = 0.010 | p = 0.010 | stationarity rejected on prices |
| KPSS | returns | p = 0.100 | p = 0.084 | stationarity kept on returns |
| Hurst (R/S) | returns | 0.548 | 0.545 | close to memoryless 0.5 |

## Tabla 5.3 — Estadística condicional por régimen de mercado (ventanas por fecha, congeladas en código)

| Regime | Window | Bars | BTC ann. ret | BTC ann. vol | BTC exc. kurt | ETH ann. vol | BTC–ETH corr |
|---|---|---|---|---|---|---|---|
| covid_crash | 2020-01-01 → 2020-04-01 | 2,183 | -45% | 115% | 94.0 | 131% | 0.903 |
| expansion_2020_21 | 2020-04-01 → 2021-12-01 | 14,616 | +131% | 76% | 15.7 | 98% | 0.820 |
| contraction_2022 | 2021-12-01 → 2023-01-01 | 9,504 | -114% | 64% | 11.1 | 85% | 0.892 |
| recovery_2023 | 2023-01-01 → 2024-01-01 | 8,760 | +94% | 43% | 26.5 | 47% | 0.860 |
| institutional_2024_25 | 2024-01-01 → 2026-01-01 | 17,544 | +36% | 49% | 9.7 | 68% | 0.798 |

Ventanas definidas en `perp_lab.eda.regimes.MARKET_REGIMES` (fin exclusivo):
covid_crash [2020-01-01, 2020-04-01) · expansion_2020_21 [→2021-12-01) ·
contraction_2022 [→2023-01-01) · recovery_2023 [→2024-01-01) ·
institutional_2024_25 [→2026-01-01). El capítulo 7 puede condicionar sobre
exactamente estos cortes importando la constante.

---

## Notas metodológicas (para pies de figura)

- **Fig 5.6 / Tabla 5.3:** regímenes por fecha fijados en código, no ajustados
  a los datos; documentados arriba.
- **Fig 5.10:** deciles por rango (la masa en el baseline de 1 pb colapsa los
  cuantiles); IC bootstrap de bloques móviles (bloque 24 barras, 500
  remuestreos, semilla 42).
- **Fig 5.14:** bandas del VR con el estadístico robusto a heteroscedasticidad
  (Lo–MacKinlay M2); Hurst por R/S, ventana 180 días, paso semanal.
- **Fig 5.16:** IM con kNN (k=3) sobre submuestra determinista 1-de-2
  (≈26.300 barras); suelo = máximo de 5 permutaciones del target con semilla
  fija; features de nivel excluidas (R7).
- **Labels:** una caracterización EDA sobre eventos «todas las barras, lado
  largo»; el estudio de meta-etiquetado del cap. 9 usa los mismos parámetros
  sobre los eventos de la estrategia primaria.
