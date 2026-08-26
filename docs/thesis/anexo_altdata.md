# Anexo de datos alternativos — Fear & Greed y eventos macro US

**Estado:** anexo DESCRIPTIVO. Nada de esto entra en el estudio canónico ni
altera el cierre (0/13). Cualquier estrategia sugerida por estas figuras sería
una hipótesis nueva que se preregistra y paga su coste de multiplicidad
(N := N+1), como los batches S1/S2. Solo partición de desarrollo, con el mismo
guard (`HoldoutLeakageError`) que los datos de mercado.

**Artefactos:** figuras A1–A4 en `reports/figures/thesis_altdata/` (PNG+PDF) +
`values_altdata.json`. Builder: `scripts/build_altdata_annex.py` (semilla 42).
Ingesta: `scripts/ingest_altdata.py` → `data/external/*.parquet` con
manifiestos SHA-256 en `data/manifests/`. Módulo: `src/perp_lab/eda/altdata.py`
con 7 tests de validación sintética (`tests/unit/test_eda_altdata.py`).

---

## Datos

| Dataset | Fuente | Cobertura usada | Filas |
|---|---|---|---|
| Crypto Fear & Greed (diario) | alternative.me (API pública) | 2020-01-01 → 2025-12-31 (desarrollo) | 2.191 días |
| Calendario macro US curado | BLS (schedules anuales 2020–2025) + Federal Reserve (calendarios FOMC) | 2020–2025 | **120 eventos: 71 CPI + 49 FOMC** |

El calendario vive como CSV committeado (`configs/altdata/us_macro_events.csv`)
con la URL de origen fila a fila: reproducible sin red. Horas convertidas de ET
a UTC con `America/New_York` (DST verificado por test: 08:30 ET = 13:30Z en
enero, 12:30Z en julio). Particularidades codificadas: los dos recortes de
emergencia de marzo 2020 llevan su hora real de anuncio (3-mar 10:00 ET,
domingo 15-mar 17:00 ET); el CPI de referencia octubre-2025 no se publicó
(shutdown federal) y el de septiembre salió el 24-oct.

**Advertencia punto-en-tiempo (para el pie del anexo):** el índice F&G lo sirve
una API viva; el proveedor no versiona cambios históricos de metodología. Por
eso el análisis (a) es solo descriptivo y (b) aplica un retardo de
disponibilidad de un día completo (el valor del día *d* condiciona la ventana
que empieza en el primer bar del día *d+1*).

---

## Resultados (todos en `values_altdata.json`)

### A2 — Condicional Fear & Greed: **sin gradiente direccional explotable**

Retorno medio de las 24h siguientes por quintil de F&G, IC bootstrap de
bloques móviles (bloque 7 días, 500 remuestreos):

- **BTC**: Q1 (miedo extremo, 5–25) +13,9 pb [-18,6, +42,1] … Q5 (codicia, 71–95) +26,9 pb [+3,0, +55,3]. Sin monotonía; casi todos los IC cubren cero.
- **ETH**: todos los quintiles positivos (deriva alcista del activo en la
  ventana), tampoco monótono.

Lectura honesta: el nivel de F&G **no ordena** los retornos siguientes a 24h.
Coherente con el hallazgo central del cap. 5: la dirección no se deja
condicionar; el «sentimiento» diario agregado tampoco lo consigue.

### A3/A4 — Eventos macro: **el cripto opera el calendario macro de EEUU**

Event-study horario (offset 0 = barra que contiene el evento) y control
emparejado por estacionalidad (misma hora UTC en días sin evento — clave,
porque el CPI cae a las 13:30/12:30 UTC, dentro del pico intradía del cap. 5):

| Evento | Activo | \|r\| barra del evento | Control emparejado | Ratio | p (permutación) |
|---|---|---|---|---|---|
| CPI (71) | BTC | **111,3 pb** | 43,4 pb | **×2,57** | < 0,001 |
| CPI (71) | ETH | 141,8 pb | 57,1 pb | ×2,48 | < 0,001 |
| FOMC (49) | BTC | **138,2 pb** | 43,0 pb | **×3,21** | < 0,001 |
| FOMC (49) | ETH | 154,1 pb | 56,7 pb | ×2,72 | < 0,001 |

Estructura temporal (Fig. A3, BTC): la volatilidad elevada **persiste 2–3
horas** tras el evento (barra del evento 111 pb y hora siguiente 77 pb en el CPI; 138 y 107 pb en el FOMC, sobre una media incondicional de 40 pb) y las horas previas al CPI quedan ligeramente *por debajo* de esa media
— compresión de anticipación. Es la manifestación a
nivel de evento del hecho estilizado del cap. 5: **cuándo** se moverá el
mercado es predecible; **hacia dónde**, no (el event-study de retorno con
signo no muestra deriva direccional aprovechable).

### Implicación (redacción sugerida para el capítulo de trabajo futuro)

> Scheduled US macro releases are among the most predictable volatility events
> in the development window: the CPI and FOMC hours carry 2.5-3.2 times the
> absolute return of seasonality-matched non-event hours (permutation
> p < 0.001), with elevated volatility persisting two to three hours. This
> supports calendar-aware conditioning layers — volatility sizing, spread
> assumptions, or trading pauses around releases — as pre-registrable
> hypotheses. It says nothing about direction: neither the event windows nor
> the daily Fear & Greed level order subsequent signed returns.

---

## Qué se añadió al repo

| Pieza | Ubicación |
|---|---|
| CSV curado de eventos (fuente committeada) | `configs/altdata/us_macro_events.csv` |
| Ingesta con manifiestos SHA-256 | `scripts/ingest_altdata.py` → `data/external/` |
| Análisis (puros, testeados) | `src/perp_lab/eda/altdata.py`: `load_fear_greed`, `load_macro_events`, `fear_greed_conditional`, `event_study`, `event_hour_vs_matched_control` |
| Tests sintéticos (7) | `tests/unit/test_eda_altdata.py`: spike plantado recuperado en offset 0; nulo → ratio≈1 y p>0,05; dependencia F&G plantada recuperada / nulo cubre cero; guard de partición; contrato del CSV (recuentos y DST) |
| Figuras + valores | `scripts/build_altdata_annex.py` → `reports/figures/thesis_altdata/` |
