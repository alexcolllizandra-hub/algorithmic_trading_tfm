# Tabla 2.1 — Trabajo relacionado (esqueleto verificado)

Regla de construcción: **solo figuran obras citadas de forma verificable en el
código del repositorio** (docstrings de `evaluation/multiple_testing.py`,
`evaluation/montecarlo.py` y `meta_labeling/`). Las filas de estudios
empíricos sobre criptomercados están marcadas `[PENDIENTE]`: no se añade
ninguna referencia sin verificarla antes (regla del proyecto: no inventar
citas).

## Metodología (citada en el repo)

| Obra | Aportación | Uso en este TFM | Especificación replicable |
|---|---|---|---|
| Holm (1979) | Control step-down del error familiar (FWER) para comparaciones múltiples | Corrección principal del cierre: 0/13 familias sobreviven | Sí — algoritmo cerrado, sin parámetros libres |
| Politis & Romano (1994) | Bootstrap estacionario para series dependientes | IC del Sharpe por remuestreo en bloques (cuaderno 07 y laboratorio web) | Sí — longitud media de bloque como único parámetro |
| Benjamini & Hochberg (1995) | Control de la tasa de descubrimientos falsos (FDR) | Corrección secundaria del cierre (más permisiva; tampoco sobrevive nada) | Sí |
| White (2000) | Reality Check: contraste del mejor modelo contra un universo de pruebas | Contraste a nivel de estudio en la batería de robustez | Sí — bootstrap especificado |
| Hansen (2005) | Test SPA: mejora del Reality Check menos sensible a modelos malos | Complemento del anterior en el cierre | Sí |
| Bailey & López de Prado (2014) | Deflated Sharpe Ratio: Sharpe corregido por número de intentos y no-normalidad | DSR del cierre (P(espurio)=0,861) y contador de intentos del laboratorio | Sí — fórmula cerrada |
| Bailey, Borwein, López de Prado & Zhu (2017) | PBO/CSCV: probabilidad de sobreajuste del backtest | PBO=0,486 sobre 70 particiones en el cierre | Sí — protocolo CSCV especificado |
| López de Prado (2018), *Advances in Financial Machine Learning* | Triple barrera, meta-labeling, purga y embargo | Etiquetado del estudio de meta-labeling (cuaderno 06) y geometría walk-forward | Parcial — libro; las elecciones concretas se documentan en este TFM |

## Estudios empíricos en criptomercados `[PENDIENTE]`

| Obra | Mercado | Horizonte | Hallazgo principal | ¿Especificación replicable? |
|---|---|---|---|---|
| [PENDIENTE — verificar antes de citar] | — | — | — | — |

Candidatos a verificar manualmente (NO citados aún en el repo; comprobar
autor/año/venue/contenido antes de incluir): estudios sobre momentum e
ineficiencias en Bitcoin, primas de funding en perpetuos, y anomalías
intradía en cripto. Criterio de la columna final: ¿publica el paper reglas,
costes y ventanas suficientes para reproducir el backtest? (La experiencia
del propio estudio sugiere que la respuesta habitual es «no», y ese es un
punto del capítulo.)
