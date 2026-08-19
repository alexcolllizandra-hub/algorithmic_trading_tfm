"""Deterministically (re)build the Monte Carlo notebook (07).

Run with: ``uv run python scripts/build_montecarlo_notebook.py``

The notebook narrates DESCRIPTIVE resampling of the study's best -- and
rejected -- strategy. Figure and table names live under the ``montecarlo/``
group (k01-k05, t01-t05) and are frozen once the thesis map cites them.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import nbformat as nbf

CELLS: list = []


def md(text: str) -> None:
    CELLS.append(nbf.v4.new_markdown_cell(text.strip("\n")))


def code(src: str) -> None:
    CELLS.append(nbf.v4.new_code_cell(src.strip("\n")))


# --------------------------------------------------------------------------- #
# Apertura
# --------------------------------------------------------------------------- #
md(
    r"""
# Monte Carlo: la mejor estrategia dentro de la distribución del azar

> **EVIDENCIA NEGATIVA ADICIONAL — todo el cuaderno es `DESCRIPTIVO`.** La
> estrategia analizada, `volatility_breakout` en BTCUSDT (random_search), está
> **RECHAZADA**: p bruto 0,345, PBO del estudio 0,486, cero supervivientes bajo
> Holm y Benjamini-Hochberg — y fue además la que consumió el holdout. Este
> análisis existe por dos razones legítimas: demostrar que la maquinaria de
> riesgo funciona, y cuantificar cuán poco distinguible del azar es la mejor
> candidata. Nada de lo que sigue es una prueba de hipótesis nueva ni un caso
> de uso operativo, y ningún resultado puede promover nada: la partición
> reservada está consumida.

**¿Qué pregunta responde este cuaderno?** Cuánto de lo que la mejor estrategia
del estudio muestra en backtest cabe esperar del puro azar — en retorno, en
secuencia y en supervivencia a reglas de cuenta fondeada. **¿Con qué datos?**
Los ledgers out-of-sample reales de las diez semillas BTCUSDT/random_search del
estudio R3 cerrado. **¿Qué va a encontrar el lector?** La figura que resume la
tesis: las diez ejecuciones reales cayendo dentro de la distribución de mil
versiones de sí mismas a las que se les ha quitado lo único que las hacía
"estrategia" — saber dónde estaban los retornos.

**Qué recibe del anterior.** El 06 mostró una mejora económica sin capacidad
predictiva; este cuaderno generaliza la sospecha: ¿cuánto resultado positivo
produce el azar sin ayuda de nadie? **Qué entrega al siguiente.** Al 08, la
pieza central del argumento visual completo.

Los métodos de remuestreo se explican donde se usan: qué asume cada uno, qué
puede detectar y qué no. La honestidad del capítulo depende de esas letras
pequeñas.

### La pregunta local

- **P1.** ¿En qué percentil de su propia nula cae la estrategia real, y
  sobrevive algo de ella a costes crecientes o a reglas de cuenta fondeada?
  (Alimenta **RQ5** — robustez — y cierra el argumento de **RQ1**.)
"""
)

# --------------------------------------------------------------------------- #
# Setup + contrato
# --------------------------------------------------------------------------- #
code(
    r"""
import os
import sys
from pathlib import Path

_root = Path.cwd()
while not (_root / "pyproject.toml").exists() and _root != _root.parent:
    _root = _root.parent
os.chdir(_root)
if str(_root / "src") not in sys.path:
    sys.path.insert(0, str(_root / "src"))
print(f"Repository root: {_root}")
"""
)

code(
    r"""
# Contrato del cuaderno: entradas y salidas declaradas y verificadas antes de
# computar nada. La cadena 01->08 se valida encadenando estos bloques.
import hashlib
import subprocess

NB_CONTRACT = {
    "notebook": "07_monte_carlo_nula",
    "inputs": [
        "artifacts/runs/r3_full_budget100_ga21/volatility_breakout/study_robustness.json",
    ],
    "outputs": {
        "figures": ["k01_bootstrap_distribuciones", "k02_permutacion_secuencia",
                     "k03_nula_con_la_estrategia_dentro", "k04_barrido_costes",
                     "k05_cuenta_fondeada"],
        "tables": ["t01_semillas_reales", "t02_bloque_acf", "t03_percentiles_nula",
                    "t04_barrido_costes", "t05_cuenta_fondeada"],
        "dirs": ["reports/figures/montecarlo", "reports/tables/montecarlo"],
    },
    # Una unica semilla gobierna todo el remuestreo del cuaderno.
    "seed": 42,
}

missing = [f for f in NB_CONTRACT["inputs"] if not Path(f).exists()]
if missing:
    raise FileNotFoundError(f"El cuaderno anterior ya no produce: {missing}")

INPUT_HASHES = {
    f: hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in NB_CONTRACT["inputs"]
}
REPO_COMMIT = subprocess.run(
    ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False
).stdout.strip() or None

for k, v in INPUT_HASHES.items():
    print(f"input  {v[:16]}  {k}")
print(f"commit {REPO_COMMIT}")
"""
)

code(
    r"""
import json

import matplotlib.pyplot as plt
import numpy as np
import polars as pl
from IPython.display import display

from perp_lab.config import Paths, load_data_contract
from perp_lab.evaluation.montecarlo import (
    PropFirmRules,
    bar_net_returns,
    breakeven_multiplier,
    cost_multiplier_sweep,
    iid_trade_bootstrap,
    null_circular_shifts,
    path_metrics,
    permutation_paths,
    prop_firm_pass_probability,
    stationary_bar_bootstrap,
    suggest_block_length,
)
from perp_lab.evaluation.study_robustness import load_oos_ledger, load_oos_trades
from perp_lab.reporting import ArtifactContext, apply_house_style, save_figure, save_table

apply_house_style()
PATHS = Paths()
FIG_DPI = 300
SEED = NB_CONTRACT["seed"]

ROB = json.loads(Path(NB_CONTRACT["inputs"][0]).read_text(encoding="utf-8"))
UNITS = {k: v for k, v in ROB["per_run"].items() if "BTCUSDT" in k and "random_search" in k}
print(f"unidades BTCUSDT/random_search: {len(UNITS)}")

_contract = load_data_contract("configs/data_contract.yaml")
ctx = ArtifactContext(
    notebook=NB_CONTRACT["notebook"],
    figures_dir=PATHS.reports_root / "figures" / "montecarlo",
    tables_dir=PATHS.reports_root / "tables" / "montecarlo",
    metadata_dir=PATHS.reports_root / "metadata" / "montecarlo",
    datasets=INPUT_HASHES,
    config={
        "seed": SEED,
        "code_commit_resolved": REPO_COMMIT,
        "data_contract_cutoff": str(_contract.cutoff_date),
        "family": "volatility_breakout (REJECTED)",
        "symbol": "BTCUSDT",
        "engine": "random_search",
        "n_units": len(UNITS),
    },
    period="development walk-forward out-of-sample; holdout never loaded",
    repo_root=".",
)


def show(fig, name, caption=""):
    save_figure(fig, name, ctx, caption=caption, dpi=FIG_DPI)
    display(fig)
    plt.close(fig)
"""
)

# --------------------------------------------------------------------------- #
# 1. Las diez ejecuciones reales
# --------------------------------------------------------------------------- #
md(
    r"""
## 1. Las diez ejecuciones reales, y cuál narra el detalle — `DESCRIPTIVO`

Cargamos el ledger out-of-sample concatenado de cada semilla (los quince folds
de test, contiguos y sin solape). Para las secciones que analizan una sola
serie elegimos **la semilla cuyo retorno total es la mediana de las diez** —
una regla fijada antes de mirar distribución alguna, precisamente para no
elegir ni la mejor (maquillaje) ni la peor (dramatismo). La figura central de
la sección 3 muestra las diez.
"""
)

code(
    r"""
ledgers = {}
trades = {}
rows = []
for key, entry in sorted(UNITS.items()):
    run_dir = entry["run_dir"]
    led = load_oos_ledger(run_dir, "random_search")
    ledgers[key] = led
    tr = load_oos_trades(run_dir, "random_search")
    trades[key] = tr["net_return"].to_numpy().astype(float)
    m = path_metrics(bar_net_returns(led))
    rows.append({
        "seed": int(key.split("seed=")[1].split("|")[0]),
        "n_bars": led.height, "n_trades": tr.height,
        "exposure": float((led["position"].to_numpy() != 0).mean()),
        **m,
    })

T01 = pl.DataFrame(rows).sort("total_return")
save_table(T01, "t01_semillas_reales", ctx,
           caption="Las diez semillas reales de volatility_breakout BTCUSDT/random_search sobre "
                   "su ledger out-of-sample concatenado.")
display(T01)

median_row = T01.row(T01.height // 2, named=True)
MEDIAN_KEY = next(k for k in UNITS if f"seed={median_row['seed']}|" in k)
LED = ledgers[MEDIAN_KEY]
TRADES = trades[MEDIAN_KEY]
BAR_R = bar_net_returns(LED)
REAL = path_metrics(BAR_R)
print(f"\nsemilla mediana: {median_row['seed']} | retorno {REAL['total_return']:+.4f} | "
      f"trades {TRADES.size} | barras {BAR_R.size}")
"""
)

# --------------------------------------------------------------------------- #
# 2. Bootstrap
# --------------------------------------------------------------------------- #
md(
    r"""
## 2. Dos bootstraps, y por qué hacen falta los dos — `DESCRIPTIVO`

El **bootstrap IID de operaciones** remuestrea con reemplazo la bolsa de
operaciones cerradas. Asume que las operaciones son intercambiables e
independientes; con eso puede responder «¿qué caminos podía haber producido
esta colección de resultados?», y no puede ver nada que dependa del orden real
ni de la dependencia temporal entre barras.

El **bootstrap estacionario por bloques** (Politis-Romano) remuestrea barras en
bloques de longitud geométrica, preservando la autocorrelación local. Su
parámetro es la longitud media de bloque, y no la elegimos a ojo: la derivamos
del último retardo cuya autocorrelación sobresale de la banda de ruido
2/√n, acotada a [6, 168] barras, y publicamos la ACF para que la elección sea
inspeccionable.
"""
)

code(
    r"""
block_info = suggest_block_length(BAR_R)
BLOCK = block_info["block_length"]
T02 = pl.DataFrame({
    "block_length": [BLOCK],
    "last_significant_lag": [block_info["last_significant_lag"]],
    "noise_band": [block_info["noise_band"]],
    "n_bars": [BAR_R.size],
})
save_table(T02, "t02_bloque_acf", ctx,
           caption="Longitud de bloque del bootstrap estacionario, derivada de la ACF de los "
                   "retornos netos por barra de la semilla mediana.")
display(T02)

boot_iid = iid_trade_bootstrap(TRADES, n_resamples=1000, seed=SEED)
boot_bar = stationary_bar_bootstrap(BAR_R, block_length=BLOCK, n_resamples=1000, seed=SEED)
print(f"bloque medio: {BLOCK} barras | IID sobre {TRADES.size} trades | "
      f"estacionario sobre {BAR_R.size} barras")
"""
)

code(
    r"""
# --- K01: distribuciones bootstrap con la realidad marcada ---------------------
fig, axes = plt.subplots(1, 3, figsize=(13.6, 4.6))
panels = [
    ("total_return", "retorno total compuesto", REAL["total_return"]),
    ("sharpe", "Sharpe por observación", REAL["sharpe"]),
    ("max_drawdown", "drawdown máximo", REAL["max_drawdown"]),
]
for ax, (key, label, real_v) in zip(axes, panels, strict=True):
    ax.hist(boot_iid[key], bins=40, density=True, histtype="step", lw=1.8,
            color="#0072B2", label="IID de operaciones")
    ax.hist(boot_bar[key], bins=40, density=True, histtype="step", lw=1.8,
            ls="--", color="#D55E00", label="estacionario por bloques")
    ax.axvline(real_v, color="black", lw=2.2, label="real")
    ax.set_xlabel(label)
    ax.set_yticks([])
axes[0].legend(fontsize=8.5, loc="upper left")
fig.suptitle(
    f"Mil remuestreos de la propia estrategia (semilla mediana, bloque {BLOCK} barras)",
    fontsize=12,
)
fig.tight_layout()
show(fig, "k01_bootstrap_distribuciones",
     caption="Distribuciones bootstrap del retorno, el Sharpe y el drawdown de la semilla "
             "mediana bajo remuestreo IID de operaciones y estacionario por bloques, con el "
             "valor real marcado.")
"""
)

md(
    r"""
La lectura importante no es dónde cae la línea negra — es **lo anchas que son
las distribuciones**. La misma bolsa de operaciones, recompuesta mil veces,
produce desde pérdidas severas hasta ganancias que cualquier vendedor de
señales enmarcaría. Cuando el intervalo que la propia estrategia genera sobre
sí misma es así de ancho, un backtest puntual es una anécdota, no una medida.
"""
)

# --------------------------------------------------------------------------- #
# 3. Permutacion y nula
# --------------------------------------------------------------------------- #
md(
    r"""
## 3. Separar la suerte de secuencia, y después quitar la señal entera — `DESCRIPTIVO`

La **permutación del orden** baraja las mismas operaciones sin reemplazo. El
retorno total compuesto es invariante por construcción — reordenar factores no
cambia el producto — así que toda la dispersión que aparezca en drawdown y en
tiempo bajo el agua es **suerte de secuencia** pura: el mismo conjunto de
aciertos y fallos, en otro orden, habría dolido más o menos.

La **nula por rotación circular** va más lejos: desplaza la serie de posiciones
un offset aleatorio contra las mismas barras, y re-cobra costes y funding
idénticamente. La rotación conserva exactamente la exposición, el número de
operaciones y la rotación de cartera; lo único que destruye es la alineación
entre la señal y los retornos que tenía delante. Si la estrategia real no se
distingue de sus mil versiones rotadas, lo que el backtest midió era la
distribución del mercado, no una habilidad de la regla.
"""
)

code(
    r"""
perm = permutation_paths(TRADES, n_resamples=1000, seed=SEED)

fig, (axA, axB) = plt.subplots(1, 2, figsize=(11.8, 4.6))
axA.hist(perm["max_drawdown"], bins=40, color="#0072B2", edgecolor="white", lw=0.4)
axA.axvline(REAL["max_drawdown"], color="black", lw=2.2, label="orden real")
axA.set_xlabel("drawdown máximo")
axA.set_ylabel("permutaciones")
axA.set_title("(a) El mismo resultado, otros órdenes")
axA.legend(fontsize=9)

axB.hist(perm["time_under_water"], bins=40, color="#D55E00", hatch="///",
         edgecolor="white", lw=0.4)
axB.axvline(REAL["time_under_water"], color="black", lw=2.2, label="orden real")
axB.set_xlabel("fracción del tiempo bajo el máximo previo")
axB.set_title("(b) Tiempo bajo el agua")
axB.legend(fontsize=9)

fig.suptitle("Permutación de operaciones: el retorno total es idéntico en las mil; "
             "solo cambia el sufrimiento", fontsize=11.5)
fig.tight_layout()
show(fig, "k02_permutacion_secuencia",
     caption="Drawdown máximo y tiempo bajo el agua bajo mil permutaciones del orden de las "
             "operaciones de la semilla mediana. El retorno total es invariante por "
             "construcción.")
"""
)

code(
    r"""
# --- K03: LA figura -- las diez reales dentro de su nula -----------------------
nulls = {}
for key, led in ledgers.items():
    nulls[key] = null_circular_shifts(led, n_shifts=1000, seed=SEED)

pooled_null = np.concatenate([n["null"]["total_return"] for n in nulls.values()])
reals = {k: n["real"]["total_return"] for k, n in nulls.items()}
pcts = {k: n["real_percentile"]["total_return"] for k, n in nulls.items()}

T03 = pl.DataFrame([
    {"seed": int(k.split("seed=")[1].split("|")[0]),
     "real_total_return": reals[k],
     "null_percentile": pcts[k],
     "exposure": nulls[k]["exposure_share"]}
    for k in sorted(nulls)
]).sort("null_percentile")
save_table(T03, "t03_percentiles_nula", ctx,
           caption="Percentil de cada semilla real dentro de su propia distribución nula por "
                   "rotación circular (1.000 rotaciones por semilla).")
display(T03)

fig, ax = plt.subplots(figsize=(11.6, 5.6))
ax.hist(pooled_null, bins=80, density=True, color="#BBBBBB", edgecolor="white", lw=0.3,
        label="nula: 10 semillas x 1.000 rotaciones de posiciones")
for i, (_k, v) in enumerate(sorted(reals.items(), key=lambda kv: kv[1])):
    ax.axvline(v, color="#0072B2", lw=1.8,
               label="estrategia real (10 semillas)" if i == 0 else None)
lo, hi = np.percentile(pooled_null, [2.5, 97.5])
ax.axvspan(lo, hi, color="#999999", alpha=0.18,
           label="95% central de la nula")
ax.set_xlabel("retorno total neto del periodo out-of-sample")
ax.set_yticks([])
ax.legend(fontsize=9, loc="upper left")
ax.set_title(
    "La mejor familia del estudio, dentro de la distribución de sus versiones sin señal",
    fontsize=12,
)
fig.tight_layout()
show(fig, "k03_nula_con_la_estrategia_dentro",
     caption="Distribución nula por rotación circular (posiciones desplazadas contra las mismas "
             "barras, costes y funding re-cobrados) agregada sobre las diez semillas, con el "
             "retorno real de cada semilla superpuesto.")

inside = sum(1 for v in reals.values() if lo <= v <= hi)
print(f"semillas reales dentro del 95% central de la nula: {inside}/10")
print(f"percentiles por semilla: {sorted(round(p, 3) for p in pcts.values())}")
"""
)

md(
    r"""
Esta es la figura que resume el trabajo. Las líneas azules — las diez
ejecuciones reales de la mejor familia del estudio — caen dentro de la banda
gris que producen sus propias posiciones rotadas al azar. No hace falta
estadística sofisticada para leerla, y toda la estadística sofisticada del
cuaderno 05 dice lo mismo que se ve a simple vista: **lo que el backtest midió
es indistinguible de la distribución del mercado repartida al azar sobre la
misma exposición.**

La letra pequeña honesta: la rotación conserva la estructura de la exposición
pero no las propiedades condicionales finas (una señal que solo operase tras
eventos concretos rotaría hacia barras sin el evento). Para una familia con
ventaja real, eso haría a esta nula *fácil* de batir — lo que hace más
informativo que no la bata nadie.
"""
)

# --------------------------------------------------------------------------- #
# 4. Costes
# --------------------------------------------------------------------------- #
md(
    r"""
## 4. Sensibilidad a costes — `DESCRIPTIVO`

Re-cobramos el camino real a múltiplos del coste efectivamente pagado
(comisión + deslizamiento), con las posiciones intactas — la misma convención
que el estrés 2x de la batería de robustez. El múltiplo donde el retorno cruza
cero dice cuánto margen de error deja el supuesto de costes del estudio.
"""
)

code(
    r"""
sweep = cost_multiplier_sweep(LED, multipliers=(0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0))
be = breakeven_multiplier(sweep)
save_table(sweep, "t04_barrido_costes", ctx,
           caption="Métricas del camino real de la semilla mediana re-cobrado a múltiplos del "
                   "coste pagado.")
display(sweep)

fig, ax = plt.subplots(figsize=(9.6, 5.0))
sw_sorted = sweep.sort("multiplier")
ax.plot(sw_sorted["multiplier"], sw_sorted["total_return"], marker="o", ms=7,
        lw=2.2, color="#0072B2")
ax.axhline(0, color="black", lw=1.2, ls="--")
if be is not None:
    ax.axvline(be, color="#D62728", lw=2.0, ls=":",
               label=f"cruce en {be:.2f}x el coste pagado")
    ax.legend(fontsize=9.5)
ax.axvline(1.0, color="#999999", lw=1.4)
ax.annotate("coste del estudio (1x)", xy=(1.0, ax.get_ylim()[0]), xytext=(6, 10),
            textcoords="offset points", fontsize=9, color="#555555", rotation=90)
ax.set_xlabel("múltiplo del coste por operación pagado")
ax.set_ylabel("retorno total neto")
ax.set_title("Cuánto coste extra aguanta el resultado antes de anularse", fontsize=12)
fig.tight_layout()
show(fig, "k04_barrido_costes",
     caption="Retorno total de la semilla mediana re-cobrando comisión y deslizamiento a "
             "múltiplos del coste realmente pagado, posiciones intactas.")
"""
)

# --------------------------------------------------------------------------- #
# 5. Cuenta fondeada
# --------------------------------------------------------------------------- #
md(
    r"""
## 5. Reglas de cuenta fondeada — `DESCRIPTIVO`, parámetros como entradas

Aplicamos reglas tipo *prop firm* — objetivo de beneficio, drawdown máximo,
pérdida diaria máxima, ventana de días — a mil caminos bootstrap de los
retornos netos de la propia estrategia. Dos aclaraciones obligatorias. Primera:
**los parámetros de la firma son entradas ajustables del análisis, no un
resultado**; los declaramos en la tabla y cualquiera puede re-ejecutar con
otros. Segunda: la fase 2 se evalúa sobre la *continuación* del mismo camino,
de modo que ambas fases comparten régimen en vez de ser sorteos independientes
— que es como funcionan de verdad.
"""
)

code(
    r"""
RULES = PropFirmRules(
    profit_target=0.08, max_total_drawdown=0.10, max_daily_loss=0.05,
    max_days=60, bars_per_day=24,
)
result = prop_firm_pass_probability(
    BAR_R, rules=RULES, block_length=BLOCK, n_paths=1000, seed=SEED
)
T05 = pl.DataFrame([{**RULES.to_dict(), **result}])
save_table(T05, "t05_cuenta_fondeada", ctx,
           caption="Reglas de cuenta fondeada aplicadas (entradas del análisis) y probabilidad "
                   "estimada de superarlas sobre caminos bootstrap de la semilla mediana.")
display(T05)

fig, ax = plt.subplots(figsize=(8.0, 4.6))
labels = ["supera fase 1", "supera fases 1 y 2"]
values = [result["pass_phase1"], result["pass_both"]]
bars = ax.bar(labels, values, width=0.5, color=["#0072B2", "#D55E00"],
              hatch=["", "///"])
for b, v in zip(bars, values, strict=True):
    ax.annotate(f"{v:.1%}", xy=(b.get_x() + b.get_width() / 2, v), xytext=(0, 6),
                textcoords="offset points", ha="center", fontsize=11, fontweight="bold")
ax.set_ylim(0, 1)
ax.set_ylabel("probabilidad sobre 1.000 caminos bootstrap")
ax.set_title(
    f"Objetivo {RULES.profit_target:.0%} · DD máx {RULES.max_total_drawdown:.0%} · "
    f"pérdida diaria {RULES.max_daily_loss:.0%} · {RULES.max_days} días",
    fontsize=10.5,
)
fig.tight_layout()
show(fig, "k05_cuenta_fondeada",
     caption="Probabilidad de superar una evaluación de cuenta fondeada (parámetros en el "
             "título, ajustables) con caminos bootstrap de la estrategia mediana.")
"""
)

# --------------------------------------------------------------------------- #
# Cierre
# --------------------------------------------------------------------------- #
md(
    r"""
## 6. Qué establece este cuaderno — y qué lo habría contradicho

Tres cosas. Primera: la maquinaria de riesgo — cuatro remuestreadores, barrido
de costes, simulador de reglas de cuenta — funciona de punta a punta sobre
ledgers reales, con semilla única y salida determinista. Segunda: la mejor
familia del estudio vive dentro de su propia nula; el resultado que el cuaderno
05 estableció por inferencia, aquí se ve en una sola imagen. Tercera: un Sharpe
alto puntual en backtest es compatible con todo lo anterior siendo ruido — las
distribuciones de la sección 2 muestran cuánta variación produce la propia
estrategia sobre sí misma sin cambiar nada.

Lo que habría contradicho esta lectura, y no ocurrió: las diez semillas reales
agrupadas en la cola derecha de la nula (percentiles altos y consistentes), un
retorno que sobreviviera holgadamente a 2-3x los costes, o una probabilidad de
superar dos fases de evaluación fondeada muy por encima de lo que la banda gris
de la nula produce sola.

Y lo que este cuaderno **no** dice: no dice que ninguna estrategia pueda pasar
una evaluación fondeada — dice que *esta*, la mejor de un estudio cerrado en
negativo, ofrece las probabilidades que se ven arriba bajo reglas declaradas.
Cambiar las reglas cambia el número; no cambia de qué lado de la nula vive la
estrategia.

### De la pregunta local a la memoria

| Pregunta local | Alimenta | Cómo |
|---|---|---|
| P1 (¿percentil en la nula, supervivencia a costes y reglas?) | RQ5 y cierre de RQ1 | evidencia negativa adicional en formato visual; la figura k03 es el resumen del TFM |

---

**Qué deja este cuaderno y a dónde va.** Figuras `k01`-`k05` y tablas
`t01`-`t05` bajo `reports/{figures,tables}/montecarlo/`. `k03` es la figura
central del capítulo 6 y del anexo Monte Carlo; `k04` alimenta la sección de
costes del capítulo 7; `k05`, la discusión del simulador de cuentas en la
plataforma. El 08 encadena las figuras clave de 01-07 en el argumento completo,
de una lectura.
"""
)


def _write() -> None:
    nb = nbf.v4.new_notebook()
    nb["cells"] = CELLS
    nb["metadata"] = {
        "language_info": {"name": "python"},
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    }
    out = Path("notebooks/07_monte_carlo_nula.ipynb")
    out.write_text(nbf.writes(nb), encoding="utf-8")
    subprocess.run(["ruff", "check", "--fix", "--quiet", str(out)], check=False)
    subprocess.run(["ruff", "format", "--quiet", str(out)], check=False)
    print(f"Wrote {out} with {len(CELLS)} cells (ruff-formatted).")


if __name__ == "__main__":
    _write()
