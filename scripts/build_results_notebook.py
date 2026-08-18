"""Deterministically (re)build the study-closure notebook.

Run with: ``uv run python scripts/build_results_notebook.py``

Prose is Spanish (the thesis language); figure and table names are frozen --
j01-j04 and t01-t09 regenerate at the same paths the thesis map already cites.
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
# Cierre del estudio: resultados, robustez y contraste múltiple

**¿Qué pregunta responde este cuaderno?** Qué encontró el estudio completo
—trece familias, dos activos, diez semillas, 496.500 configuraciones— y si algo
sobrevive a contar honestamente cuántas veces se ha mirado. **¿Con qué datos?**
Los artefactos de cierre bajo `reports/study_closure/`, congelados al cerrar el
estudio. **¿Qué va a encontrar el lector?** Un resultado negativo, y el
argumento de por qué ese negativo es informativo y no solo decepcionante —
incluida la parte incómoda: la partición reservada se abrió fuera de protocolo
y su lectura está retenida.

**Qué recibe de los cuadernos anteriores.** El 02 demostró que las
características no pueden ver el futuro; el 03, que la ejecución paga lo que se
paga y que los folds no se tocan; el 04, que la búsqueda estaba operando sobre
ruido a nivel de fold. **Qué entrega.** El veredicto agregado del estudio y las
cuatro figuras de cierre (j01-j04) que alimentan los capítulos 6 y 7 de la
memoria.

Una aclaración de contabilidad antes de empezar: todos los contrastes de este
cuaderno son **INFERENCIALES ya contados y cerrados** — se ejecutaron una vez,
quedaron registrados en los artefactos, y aquí se leen y se explican. Este
cuaderno no añade ninguna prueba nueva al denominador.

## 1. Resumen para quien no vaya a leer más

De trece familias, **ninguna sobrevive a la corrección por el número de
hipótesis que el estudio puso a prueba** — y el matiz importante es que ni
siquiera hace falta la corrección: el p-valor bruto más bajo de todo el estudio
queda lejísimos del umbral convencional antes de corregir nada. La conclusión
no depende de qué corrección prefiera el lector.

Tres diagnósticos que no tenían por qué estar de acuerdo lo están:

| Diagnóstico | Qué mide | Resultado |
|---|---|---|
| Contrastes por familia | ¿Alguna media de retorno se distingue de cero? | Ninguna, ni sin corregir |
| Sharpe deflactado | Dado todo lo que probamos, ¿cuán probable es que el mejor sea espurio? | Muy probablemente espurio |
| PBO | ¿El mejor en muestra sigue siéndolo fuera de ella? | Cara o cruz |

Un PBO cercano a 0,5 es la firma de una búsqueda operando sobre ruido: el que
gana en una mitad de los datos no tiene más probabilidad que el azar de ganar
en la otra.

**Lo que deliberadamente no se publica aquí.** El holdout congelado se abrió
una vez y su lectura existe en disco. No aparece en este cuaderno: el
repositorio registra esa apertura como `HOLDOUT_LOCKED` a la espera de una
auditoría de procedencia, y la sección 7 cuenta esa decisión entera. La
conclusión del estudio no depende de esa cifra.

### Las preguntas de este cuaderno

- **P1.** ¿Cuántas hipótesis puso a prueba realmente este estudio, y cambia eso la conclusión?
- **P2.** ¿Alguna familia cumple los criterios de promoción preregistrados?
- **P3.** ¿Alguna sobrevive a Holm-Bonferroni o a Benjamini-Hochberg?
- **P4.** ¿Cuán probable es que la mejor familia sea un artefacto estadístico?
- **P5.** ¿Condicionar por régimen rescata algo que falló sin condicionar?
- **P6.** ¿Qué se puede y qué no se puede concluir de un negativo con esta forma?
"""
)

# --------------------------------------------------------------------------- #
# Inventario
# --------------------------------------------------------------------------- #
md(
    r"""
## 2. El inventario del estudio — `DESCRIPTIVO`

Los artefactos de cierre agregan todas las puertas del estudio (R2, R3, S1, S2)
en una sola base de evidencia. Cada familia lleva su desenlace económico entre
semillas, su p-valor bruto, los dos ajustados, y si cumplió cada criterio de
promoción preregistrado. Aquí solo los cargamos y los miramos.
"""
)

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
import json
import platform

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import polars as pl
from IPython.display import display

from perp_lab import __version__ as perp_lab_version
from perp_lab.config import Paths
from perp_lab.reporting import ArtifactContext, apply_house_style, save_figure, save_table

apply_house_style()
PATHS = Paths()
FIG_DPI = 300
CLOSURE = Path("reports/study_closure")

DASH = json.loads((CLOSURE / "study_dashboard.json").read_text(encoding="utf-8"))
MT = json.loads((CLOSURE / "study_level_multiple_testing.json").read_text(encoding="utf-8"))
REG = json.loads((CLOSURE / "regime_conditioned.json").read_text(encoding="utf-8"))

STUDY = DASH["study"]
print("Environment")
print(f"  Python  : {platform.python_version()} | perp_lab {perp_lab_version}")
print(f"  polars  : {pl.__version__} | numpy {np.__version__} | matplotlib {matplotlib.__version__}")
print("\nStudy inventory")
print(f"  families evaluated        : {STUDY['n_families']}")
print(f"  units (family x asset x seed grids) : {STUDY['n_units']}")
print(f"  configurations evaluated  : {STUDY['n_configurations_evaluated']:,}")
print(f"  primary asset / engine    : {DASH['primary_symbol']} / {DASH['primary_engine']}")
print(f"  alpha                     : {STUDY['alpha']}")
print(f"  best family (by raw p)    : {STUDY['best_family']}")
print(f"  source commit             : {STUDY['source_commit'][:12]}")
print(f"  holdout accessed here     : {MT['holdout_accessed']}")
print(f"  holdout publication state : {DASH['holdout_publication']}")
"""
)

code(
    r"""
NB_ID = "05_study_closure_and_multiple_testing"
ctx = ArtifactContext(
    notebook=NB_ID,
    figures_dir=PATHS.reports_root / "figures" / "closure",
    tables_dir=PATHS.reports_root / "tables" / "closure",
    metadata_dir=PATHS.reports_root / "metadata" / "closure",
    config={
        "n_families": STUDY["n_families"],
        "n_units": STUDY["n_units"],
        "n_configurations": STUDY["n_configurations_evaluated"],
        "alpha": STUDY["alpha"],
        "source_commit": STUDY["source_commit"],
        "holdout_publication": DASH["holdout_publication"],
    },
    period="development walk-forward out-of-sample; holdout NOT published",
    repo_root=".",
)


def show(fig, name, caption=""):
    save_figure(fig, name, ctx, caption=caption, dpi=FIG_DPI)
    display(fig)
    plt.close(fig)


FAM = pl.DataFrame([
    {
        "family": f["family"], "gate": f["gate"], "symbol": f["symbol"],
        "n_seeds": f["n_seeds"], "total_return": f["total_return"],
        "sharpe": f["sharpe"], "max_drawdown": f["max_drawdown"],
        "p_value": f["p_value"], "holm_p": f["holm_adjusted_p"],
        "bh_p": f["bh_adjusted_p"], "survives": f["survives_correction"],
        "verdict": f.get("verdict", ""),
    }
    for f in DASH["families"]
]).sort("p_value")
save_table(FAM, "t01_family_results", ctx,
           caption="Cada celda familia-activo del estudio, con su desenlace económico, su p-valor "
                   "bruto y los dos ajustados.")
display(FAM)

print(f"\nCells: {FAM.height} | families: {FAM['family'].n_unique()}")
print(f"Cells with a positive total return : {int((FAM['total_return'] > 0).sum())} / {FAM.height}")
print(f"Cells surviving correction         : {int(FAM['survives'].sum())} / {FAM.height}")
print(f"Smallest raw p-value in the study  : {float(FAM['p_value'].min()):.4f} "
      f"(alpha = {STUDY['alpha']})")
"""
)

md(
    r"""
El número que más importa de esa tabla es el **p-valor bruto mínimo**. Antes de
cualquier corrección, antes de deflactar nada, y tomando la familia más
favorable del estudio al pie de la letra, nadie se acerca a la significación
convencional.

Eso es lo que hace la conclusión robusta al desacuerdo metodológico: quien crea
que Holm-Bonferroni es demasiado conservador, o que el recuento de pruebas se
eligió con intención, no llega por ello a una respuesta distinta — no hay nada
desde lo que corregir hacia abajo. Las correcciones que siguen cuantifican *a
qué distancia* de la significación queda el estudio; el veredicto no cuelga de
ellas.
"""
)

# --------------------------------------------------------------------------- #
# Criterios de promoción
# --------------------------------------------------------------------------- #
md(
    r"""
## 3. Los criterios de promoción, familia a familia — `INFERENCIAL — cerrado`

La significación estadística era necesaria pero no suficiente: un candidato
tenía que superar seis listones económicos preregistrados antes de poder
aspirar al holdout. Para cada familia y activo contamos cuántas de sus diez
semillas pasaron cada criterio, contra la mayoría exigida (6 de 10).

Que los umbrales se fijaran *antes* de ver resultados es lo que hace
informativo el suspenso: después ya no se pueden renegociar.
"""
)

code(
    r"""
crit_rows = []
for f in DASH["families"]:
    for c in f.get("criteria") or []:
        crit_rows.append({
            "family": f["family"], "symbol": f["symbol"],
            "criterion": c["label"], "key": c["key"],
            "passed": c["passed"], "of": c["of"], "required": c["required"], "met": c["met"],
        })
CRIT = pl.DataFrame(crit_rows)
save_table(CRIT, "t02_promotion_criteria", ctx,
           caption="Criterios de promoción preregistrados: semillas que pasan cada criterio por "
                   "celda familia-activo.")
display(CRIT.head(12))

SUMMARY = (
    CRIT.group_by("criterion")
    .agg(
        pl.len().alias("cells"),
        pl.col("met").sum().alias("cells_meeting"),
        (pl.col("passed").sum() / pl.col("of").sum()).alias("share_of_seeds_passing"),
    )
    .sort("share_of_seeds_passing", descending=True)
)
save_table(SUMMARY, "t03_criteria_summary", ctx,
           caption="Frecuencia con la que cada criterio de promoción se cumplió en el conjunto "
                   "del estudio.")
display(SUMMARY)
print(f"\nCells meeting ALL criteria: "
      f"{int(CRIT.group_by('family', 'symbol').agg(pl.col('met').all().alias('all_met'))['all_met'].sum())}"
      f" / {CRIT['family'].n_unique() * CRIT['symbol'].n_unique()}")
"""
)

code(
    r"""
# --- J01: the criteria heat map ----------------------------------------------
piv = CRIT.filter(pl.col("symbol") == DASH["primary_symbol"])
fams = sorted(piv["family"].unique().to_list())
crits = list(dict.fromkeys(CRIT["criterion"].to_list()))
M = np.full((len(fams), len(crits)), np.nan)
REQ = np.full((len(fams), len(crits)), np.nan)
for r in piv.iter_rows(named=True):
    i, j = fams.index(r["family"]), crits.index(r["criterion"])
    M[i, j] = r["passed"] / max(1, r["of"])
    REQ[i, j] = r["required"] / max(1, r["of"])

fig, ax = plt.subplots(figsize=(12.4, 0.46 * len(fams) + 3.2))
im = ax.imshow(M, cmap="RdYlGn", vmin=0, vmax=1, aspect="auto")
for i in range(len(fams)):
    for j in range(len(crits)):
        if np.isnan(M[i, j]):
            continue
        ax.text(j, i, f"{round(M[i, j] * 10)}/10", ha="center", va="center",
                fontsize=8.5, color="black")
ax.set_xticks(range(len(crits)))
ax.set_xticklabels(crits, rotation=35, ha="right", fontsize=9)
ax.set_yticks(range(len(fams)))
ax.set_yticklabels(fams, fontsize=9)
ax.grid(visible=False)
cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
cb.set_label("share of the 10 seeds passing")
ax.set_title(f"Promotion criteria, {DASH['primary_symbol']} - a majority (6/10) was required to pass",
             fontsize=12)
fig.tight_layout()
show(fig, "j01_promotion_criteria",
     caption="Proporción de semillas que pasa cada criterio de promoción preregistrado, por "
             "familia, en el activo principal.")
"""
)

md(
    r"""
El mapa es abrumadoramente rojo, y los dos criterios que más consistentemente
fallan son justo los que más importan económicamente: producir retorno neto
positivo, y que el intervalo bootstrap del Sharpe excluya el cero. Algunas
familias pasan criterios sueltos en una minoría de semillas — que es
exactamente lo que se espera del ruido: un criterio que se pasa por azar una
de cada tres veces se pasará en tres o cuatro semillas de diez — pero la
mayoría exigida no se alcanza prácticamente nunca.

Aquí se ve el valor del preregistro. Si los umbrales se hubieran puesto
*después* de mirar, habría sido fácil notar que una familia pasa cuatro de seis
criterios y argumentar que cuatro es un listón razonable. Como se fijaron
antes, ese argumento no está disponible, y los suspensos se pueden interpretar.
"""
)

# --------------------------------------------------------------------------- #
# Contraste múltiple
# --------------------------------------------------------------------------- #
md(
    r"""
## 4. Corregir por el número de hipótesis — `INFERENCIAL — cerrado`

Si pruebas trece familias al 5%, esperas más o menos un falso éxito por puro
azar. ¿Qué queda cuando eso se descuenta?

Se aplican las dos correcciones estándar, y reportar ambas es deliberado: si
discreparan, la conclusión dependería de una elección metodológica y habría que
decirlo así.

- **Holm-Bonferroni** controla la probabilidad de *un solo* falso positivo en
  todo el estudio (FWER) — la opción conservadora, apropiada cuando una sola
  afirmación falsa sale cara.
- **Benjamini-Hochberg** controla la proporción esperada de descubrimientos
  falsos (FDR) — más permisiva, pensada para cribar.
"""
)

code(
    r"""
CORR = MT["corrections"]
holm = CORR["holm_bonferroni"]
bh = CORR["benjamini_hochberg"]

COMP = pl.DataFrame({
    "correction": ["none (raw)", "Benjamini-Hochberg (FDR)", "Holm-Bonferroni (FWER)"],
    "n_tests": [CORR["n_tests"]] * 3,
    "n_rejected_at_alpha": [
        int(sum(1 for f in DASH["families"] if f["p_value"] < STUDY["alpha"])),
        int(bh["n_rejected"]),
        int(holm["n_rejected"]),
    ],
    "smallest_p_value": [
        float(min(f["p_value"] for f in DASH["families"])),
        float(min(bh["adjusted_p_values"].values())),
        float(min(holm["adjusted_p_values"].values())),
    ],
})
save_table(COMP, "t04_multiple_testing", ctx,
           caption="Rechazos a alfa = 0.05 antes y después de cada corrección por contraste "
                   "múltiple.")
display(COMP)

print(f"\nTests counted        : {CORR['n_tests']}")
print(f"Holm rejections      : {holm['n_rejected']}")
print(f"BH rejections        : {bh['n_rejected']}")
print(f"Best family          : {CORR['best_family']}")
"""
)

code(
    r"""
# --- Sensitivity: what counts as "a test"? -----------------------------------
SENS = pl.DataFrame([
    {"definition": k,
     "n_tests": v["n_tests"],
     "bonferroni_threshold": v["bonferroni_threshold"],
     "smallest_raw_p": v["smallest_raw_p_value"],
     "any_survive": v["any_survive"]}
    for k, v in MT["sensitivity"].items()
]).sort("n_tests")
save_table(SENS, "t05_test_count_sensitivity", ctx,
           caption="Sensibilidad de la conclusión a cómo se define el número de hipótesis "
                   "contrastadas.")
display(SENS)
print(f"\nDefinitions under which SOME family survives: "
      f"{int(SENS['any_survive'].sum())} / {SENS.height}")
"""
)

code(
    r"""
# --- J02: corrections and their sensitivity ----------------------------------
fig, (axA, axB) = plt.subplots(1, 2, figsize=(13.2, 5.6),
                               gridspec_kw={"width_ratios": [1.25, 1.0]})

order = sorted(holm["adjusted_p_values"], key=lambda k: holm["adjusted_p_values"][k])
raw_map = {}
for f in DASH["families"]:
    raw_map.setdefault(f["family"], []).append(f["p_value"])
raw = [min(raw_map[k]) for k in order]
hp = [holm["adjusted_p_values"][k] for k in order]
bp = [bh["adjusted_p_values"][k] for k in order]
yy = np.arange(len(order))
axA.barh(yy - 0.26, raw, height=0.24, color="#999999", label="raw p-value")
axA.barh(yy, bp, height=0.24, color="#0072B2", label="Benjamini-Hochberg")
axA.barh(yy + 0.26, hp, height=0.24, color="#D55E00", label="Holm-Bonferroni")
axA.axvline(STUDY["alpha"], color="#D62728", lw=2.0, ls="--")
axA.text(STUDY["alpha"], -1.0, f" alpha = {STUDY['alpha']}", color="#D62728", fontsize=9)
axA.set_yticks(yy)
axA.set_yticklabels(order, fontsize=8.5)
axA.invert_yaxis()
axA.set_xlim(0, 1.05)
axA.set_xlabel("p-value")
axA.set_title("(a) Nothing approaches the significance threshold")
axA.legend(fontsize=8.5, loc="lower right")
axA.grid(axis="y", visible=False)

labels = SENS["definition"].to_list()
nt = SENS["n_tests"].to_numpy()
thr = SENS["bonferroni_threshold"].to_numpy()
smallest = float(SENS["smallest_raw_p"][0])
axB.plot(nt, thr, marker="o", ms=8, lw=2.0, color="#0072B2", label="Bonferroni threshold")
axB.axhline(smallest, color="#D62728", lw=2.0, ls="--",
            label=f"smallest raw p in the study = {smallest:.3f}")
axB.set_xscale("log")
axB.set_yscale("log")
for x, y, lab in zip(nt, thr, labels, strict=True):
    axB.annotate(lab.replace("_", " "), xy=(x, y), xytext=(0, -16),
                 textcoords="offset points", fontsize=7.5, ha="center", color="#555555")
axB.set_xlabel("number of hypotheses counted (log scale)")
axB.set_ylabel("threshold / p-value (log scale)")
axB.set_title("(b) The conclusion does not depend on how tests are counted")
axB.legend(fontsize=8.5, loc="lower left")

fig.suptitle(f"Multiple-testing correction across {CORR['n_tests']} families "
             f"({STUDY['n_configurations_evaluated']:,} configurations evaluated)", fontsize=12)
fig.tight_layout()
show(fig, "j02_multiple_testing",
     caption="P-valores brutos y ajustados por familia (a), y sensibilidad del umbral de "
             "Bonferroni a cómo se cuenta el número de hipótesis (b).")
"""
)

md(
    r"""
El panel (a) enseña a las dos correcciones empujando cada p ajustado hasta el
techo de la escala — pero esa no es la parte informativa: las barras grises ya
estaban lejos del umbral antes de corregir.

El panel (b) es el que cierra la objeción habitual a cualquier argumento de
contraste múltiple: que el número de pruebas se eligió a conveniencia. Se puede
contar trece (una por familia), veintidós (familia por activo), ciento cuarenta
y dos (añadiendo semillas) o casi medio millón (cada configuración evaluada).
Cuatro órdenes de magnitud de diferencia, umbrales de Bonferroni desde ~4e-3
hasta ~1e-7 — y **todos quedan por debajo del p bruto mínimo observado**. La
línea roja discontinua va por encima de la curva azul en todo el rango: no
existe ninguna versión de este argumento en la que alguna familia sobreviva.
"""
)

# --------------------------------------------------------------------------- #
# DSR y PBO
# --------------------------------------------------------------------------- #
md(
    r"""
## 5. ¿Cuán probable es que el mejor resultado sea un artefacto? — `INFERENCIAL — cerrado`

Los p-valores responden «¿pudo salir esto por azar?» para una hipótesis. Dos
diagnósticos construidos a medida responden la pregunta que de verdad se hace
quien backtestea.

El **Sharpe deflactado** pregunta: dado que probamos N configuraciones, ¿qué
Sharpe alcanzaría la mejor *solo por suerte*, y supera el observado ese listón?

El **PBO** pregunta algo más directo y más difícil de discutir: parte en dos la
serie de observaciones muchas veces, elige al mejor en la mitad in-sample y
mide con qué frecuencia ese elegido cae en la *mitad mala* fuera. Un PBO cerca
de **0,5** significa que elegir no aporta información: el ganador in-sample es
una moneda al aire out-of-sample.
"""
)

code(
    r"""
ds = CORR["deflated_sharpe"]
pbo = CORR["probability_of_backtest_overfitting"]

DS = pl.DataFrame([
    {"scenario": k,
     "n_trials": v["n_trials"],
     "observed_sharpe_per_obs": v["observed_sharpe_per_observation"],
     "benchmark_sharpe_per_obs": v["benchmark_sharpe_per_observation"],
     "deflated_sharpe": v["deflated_sharpe"],
     "probability_best_is_spurious": v["probability_best_is_spurious"]}
    for k, v in ds.items()
])
save_table(DS, "t06_deflated_sharpe", ctx,
           caption="Sharpe deflactado de la mejor familia del estudio bajo dos definiciones del "
                   "número de ensayos.")
display(DS)

print(f"\nPBO                         : {pbo['pbo']:.4f}")
print(f"  splits evaluated          : {pbo['n_splits']}")
print(f"  configurations compared   : {pbo['n_configurations']}")
print(f"  observations              : {pbo['n_observations']:,}")
print("\nInterpretation of PBO:")
print("  0.0 = the in-sample winner always wins out of sample (no overfitting)")
print("  0.5 = the in-sample winner is a coin flip out of sample (selection is uninformative)")
print("  1.0 = the in-sample winner always LOSES out of sample (systematic overfitting)")
"""
)

code(
    r"""
# --- J03: deflated Sharpe and PBO --------------------------------------------
fig, (axA, axB) = plt.subplots(1, 2, figsize=(13.0, 5.4),
                               gridspec_kw={"width_ratios": [1.1, 1.0]})

scen = DS["scenario"].to_list()
obs = DS["observed_sharpe_per_obs"].to_numpy()
bench = DS["benchmark_sharpe_per_obs"].to_numpy()
xx = np.arange(len(scen))
axA.bar(xx - 0.2, obs, width=0.38, color="#0072B2", label="observed Sharpe of the best family")
axA.bar(xx + 0.2, bench, width=0.38, color="#D55E00",
        label="Sharpe the best would reach BY LUCK")
for i in range(len(scen)):
    axA.text(i + 0.2, bench[i] * 1.03,
             f"{DS['n_trials'][i]:,} trials", ha="center", fontsize=8.5, color="#8A4000")
axA.set_xticks(xx)
axA.set_xticklabels([s.replace("_", "\n") for s in scen], fontsize=9)
axA.set_ylabel("Sharpe per observation")
axA.set_title("(a) The best result does not clear the luck benchmark")
axA.legend(fontsize=8.5, loc="upper left")
axA.grid(axis="x", visible=False)

val = float(pbo["pbo"])
axB.barh([0], [1.0], color="#EEEEEE", height=0.42)
axB.barh([0], [val], color="#D62728", height=0.42)
axB.axvline(0.5, color="black", lw=2.0, ls="--")
axB.text(0.5, 0.36, "  coin flip", fontsize=9.5, fontweight="bold")
axB.text(val, 0, f" PBO = {val:.3f} ", va="center", ha="right", fontsize=12,
         fontweight="bold", color="white")
axB.text(0.02, -0.36, "no overfitting", fontsize=8.5, color="#555555")
axB.text(0.98, -0.36, "systematic overfitting", fontsize=8.5, color="#555555", ha="right")
axB.set_xlim(0, 1)
axB.set_ylim(-0.6, 0.6)
axB.set_yticks([])
axB.set_xlabel("probability of backtest overfitting")
axB.set_title(f"(b) Selection is uninformative\n({pbo['n_splits']} splits, "
              f"{pbo['n_observations']:,} observations)")
axB.grid(axis="y", visible=False)

fig.suptitle("Two diagnostics built for exactly this question, and they agree", fontsize=12)
fig.tight_layout()
show(fig, "j03_deflated_sharpe_pbo",
     caption="Sharpe deflactado bajo dos recuentos de ensayos (a) y probabilidad de sobreajuste "
             "del backtest (b).")
"""
)

md(
    r"""
El panel (a) hace concreto el argumento de la deflación. Contando solo las
trece familias como ensayos, el Sharpe que *el mejor de trece* alcanzaría por
suerte ya supera lo que la mejor familia consiguió de verdad — así que el mejor
observado no es solo poco impresionante: rinde por debajo del azar. Contando
las 496.500 configuraciones evaluadas, el listón de la suerte sube un orden de
magnitud y la probabilidad de que el mejor resultado sea espurio roza la
certeza.

El panel (b) es el número más limpio de la tesis. El PBO queda pegado a
**0,5**: elegir al mejor in-sample no da esencialmente ninguna ventaja fuera.
Es el mismo mecanismo que el cuaderno 04 observó fold a fold, ahora medido
sobre el estudio entero — así se ve desde dentro una búsqueda que opera sobre
ruido.

Conviene ser explícito con lo que el PBO *no* dice: no dice que las estrategias
sean malas en absoluto, ni que la implementación falle. Dice que **el ranking
que produce el rendimiento in-sample no se transfiere** — la búsqueda no sirve
para elegir un ganador, independientemente de lo buenos que pudieran ser los
candidatos por separado.
"""
)

# --------------------------------------------------------------------------- #
# Régimen
# --------------------------------------------------------------------------- #
md(
    r"""
## 6. ¿Condicionar por régimen rescata algo? — `INFERENCIAL — cerrado (exploratorio)`

Una estrategia podría tener una ventaja real que solo aparece en ciertas
condiciones de mercado y que el promedio incondicional difumina. ¿La revela
partir por régimen de volatilidad?

Cada familia se reevalúa dentro de cada celda de régimen —con un tamaño mínimo
de celda para no contrastar sobre un puñado de barras— y los p resultantes se
corrigen sobre el conjunto de celdas. El propio artefacto etiqueta este
análisis como **exploratorio**: multiplica el número de pruebas, así que es el
lugar más probable de todo el estudio para que aparezca un falso positivo. Que
no aparezca ninguno es, por eso mismo, una afirmación fuerte.
"""
)

code(
    r"""
CELLS_ = pl.DataFrame(REG["cells"]).sort("p_value")
save_table(CELLS_.head(20), "t07_regime_cells_top20", ctx,
           caption="Las veinte celdas familia-régimen más favorables, ordenadas por p-valor bruto.")
display(CELLS_.head(15))

rc = REG["correction"]
print(f"\nStatus                    : {REG['status']}")
print(f"Cells tested              : {rc['n_cells']} (testable: {rc['n_testable_cells']}, "
      f"excluded as too small: {rc['n_excluded_small_cells']}, min bars: {rc['min_cell_bars']})")
print(f"Holm rejections           : {rc['holm_bonferroni'].get('n_rejected', 0)}")
print(f"Benjamini-Hochberg        : {rc['benjamini_hochberg'].get('n_rejected', 0)}")
print(f"Survivors                 : {len(rc['survivors'])}")
print(f"Promoted candidate        : {REG['candidate']}")
print(f"\nSmallest raw p across all cells: {float(CELLS_['p_value'].min()):.4f}")
print(f"Cells with a positive total return: "
      f"{int((CELLS_['total_return'] > 0).sum())} / {CELLS_.height}")
"""
)

code(
    r"""
# --- J04: regime cells --------------------------------------------------------
fig, (axA, axB) = plt.subplots(1, 2, figsize=(13.2, 5.6),
                               gridspec_kw={"width_ratios": [1.0, 1.2]})

p = CELLS_["p_value"].to_numpy()
axA.hist(p, bins=20, range=(0, 1), color="#0072B2", edgecolor="white", linewidth=0.6)
axA.axvline(STUDY["alpha"], color="#D62728", lw=2.0, ls="--",
            label=f"alpha = {STUDY['alpha']} (uncorrected)")
n_nominal = int((p < STUDY["alpha"]).sum())
axA.set_xlabel("raw p-value")
axA.set_ylabel("family-by-regime cells")
axA.set_title(f"(a) {rc['n_cells']} cells; {n_nominal} nominally significant,\n"
              f"{len(rc['survivors'])} surviving correction")
axA.legend(fontsize=9)

regs = sorted(CELLS_["regime"].unique().to_list())
fams_r = sorted(CELLS_["family"].unique().to_list())
G = np.full((len(fams_r), len(regs)), np.nan)
for r in CELLS_.iter_rows(named=True):
    G[fams_r.index(r["family"]), regs.index(r["regime"])] = r["total_return"]
vmax = float(np.nanmax(np.abs(G)))
im = axB.imshow(G, cmap="RdYlGn", vmin=-vmax, vmax=vmax, aspect="auto")
axB.set_xticks(range(len(regs)))
axB.set_xticklabels(regs, rotation=25, ha="right", fontsize=8.5)
axB.set_yticks(range(len(fams_r)))
axB.set_yticklabels(fams_r, fontsize=8)
axB.grid(visible=False)
cb = fig.colorbar(im, ax=axB, fraction=0.035, pad=0.02)
cb.set_label("total return within the regime")
axB.set_title("(b) No regime is systematically favourable")

fig.suptitle("Regime-conditioned evaluation - EXPLORATORY, nothing promoted", fontsize=12)
fig.tight_layout()
show(fig, "j04_regime_conditioned",
     caption="Distribución de p-valores brutos en las celdas familia-régimen (a) y retorno total "
             "de cada celda (b). Ninguna celda sobrevive a la corrección.")
"""
)

md(
    r"""
El histograma del panel (a) es el diagnóstico que hay que leer. Bajo la nula
global —ninguna familia tiene ventaja en ningún régimen— los p se distribuyen
uniformes: histograma plano, con un ~5% de celdas por debajo de alfa por puro
azar. Eso es prácticamente lo que se observa, y **ninguna celda sobrevive a la
corrección**. Si hubiera un efecto condicional real, habría un exceso de masa
cerca de cero que la corrección no borraría. No lo hay. El panel (b) dice lo
mismo en términos económicos: los retornos se reparten sin ninguna columna
sistemáticamente favorable — así queda el ruido cuando se ordena en una rejilla.

La reserva honesta: un efecto real pero pequeño y confinado a un régimen
estrecho podría escapársele a este análisis — condicionar parte la muestra, y
las celdas pequeñas tienen menos potencia. Esta sección descarta ventajas
condicionales *fuertes*, no todas las concebibles. Por eso el artefacto la
etiqueta como exploratoria y de aquí no se promovió ningún candidato.
"""
)

# --------------------------------------------------------------------------- #
# Holdout
# --------------------------------------------------------------------------- #
md(
    r"""
## 7. El holdout congelado: abierto, registrado y deliberadamente no publicado — `DESCRIPTIVO`

Esta sección reporta una **decisión de proceso**, no un número — y esa
distinción es el contenido.

**Qué pasó.** La partición `[2026-01-01, 2026-07-01)` se congeló al inicio del
proyecto y no se tocó durante la exploración, el diseño de características, la
selección de familias ni la búsqueda de parámetros. Se abrió **una vez**, el
2026-08-13, sobre un candidato cuya regla de selección y parámetros se
commitearon *antes* de la apertura — un candidato que la corrección a nivel de
estudio **ya había rechazado**. Esa lectura existe en disco.

**Por qué no se publica aquí.** El repositorio registra la apertura como
`HOLDOUT_LOCKED`: la auditoría de procedencia posterior verificó que la
autorización prevista por el protocolo no existía en el momento de abrir (el
único control con ese nombre es un cerrojo de *publicación*, introducido
después), y quedó abierta una lista de nueve requisitos antes de que la cifra
pueda citarse. Los detalles, con su cronología y su evidencia, están en
`docs/methodology/holdout_audit_status.md`.

Lo importante: **no se reescribió la historia para ordenar esto.** Reescribirla
habría destruido justo la propiedad que hace auditable una apertura — que el
commit que congela al candidato precede de forma comprobable al que registra el
resultado. La cadena de commits *es* la evidencia.

**Por qué la conclusión no depende de ello.** El holdout iba a ser la prueba
confirmatoria de un candidato ya rechazado. El resultado de esta tesis es el
mapa de trece familias sin supervivientes con PBO en el entorno de 0,5 — y ese
resultado está completo sin abrir la partición. Publicar la lectura cambiaría
el énfasis de un párrafo, no la conclusión. Lo que sí se pierde para siempre es
la posibilidad de una confirmación limpia sobre este histórico: la partición
está consumida, y cualquier familia futura necesitará datos nuevos.
"""
)

code(
    r"""
lock_rows = [
    {"control": "Artifact layer",
     "state": "study_dashboard.json contains no holdout metrics unless --include-holdout is passed",
     "verified": DASH.get("holdout") is None},
    {"control": "Service layer",
     "state": "publication requires PERP_LAB_HOLDOUT_PUBLICATION == AUDITED_OPEN_FINAL_HOLDOUT",
     "verified": DASH.get("holdout_publication") != "PUBLISHED"},
    {"control": "This notebook",
     "state": "reads no holdout metrics; multiple-testing artifact confirms holdout_accessed = False",
     "verified": MT["holdout_accessed"] is False},
]
LOCKS = pl.DataFrame(lock_rows)
save_table(LOCKS, "t08_holdout_locks", ctx,
           caption="Controles independientes que impiden publicar la lectura del holdout "
                   "congelado.")
display(LOCKS)

print(f"Holdout publication state : {DASH['holdout_publication']}")
print(f"Holdout payload in dashboard : {DASH.get('holdout')}")
print(f"Holdout accessed by the study-level analysis : {MT['holdout_accessed']}")
print(f"\nAll locks engaged: {bool(LOCKS['verified'].all())}")
print("\nNo holdout metric is computed, displayed or exported by this notebook.")
"""
)

# --------------------------------------------------------------------------- #
# Conclusiones
# --------------------------------------------------------------------------- #
md(
    r"""
## 8. Qué establece un negativo con esta forma — `DESCRIPTIVO`

El estudio no encontró nada. ¿Qué se ha aprendido, exactamente?
"""
)

code(
    r"""
conclusions = [
    {"id": "C1",
     "claim": "Ninguna familia del estudio tiene ventaja demostrable en perpetuos BTC/ETH a 1h",
     "strength": "Fuerte",
     "basis": f"{FAM['family'].n_unique()} familias, {STUDY['n_units']} unidades, p bruto minimo "
              f"{float(FAM['p_value'].min()):.3f} antes de correccion alguna",
     "scope_limit": "Temporalidad 1h, 2020-2025, estos dos activos, estas familias de reglas"},
    {"id": "C2",
     "claim": "La conclusion es invariante a como se cuente el numero de hipotesis",
     "strength": "Fuerte",
     "basis": f"t05: {SENS.height} convenciones de recuento entre "
              f"{int(SENS['n_tests'].min())} y {int(SENS['n_tests'].max()):,} pruebas, ninguna produce superviviente",
     "scope_limit": "Aplica a los contrastes por familia realmente ejecutados"},
    {"id": "C3",
     "claim": "La seleccion in-sample no lleva esencialmente informacion out-of-sample",
     "strength": "Fuerte",
     "basis": f"PBO = {pbo['pbo']:.3f} sobre {pbo['n_splits']} particiones; el Sharpe deflactado "
              f"implica que la mejor familia es espuria con probabilidad "
              f"{ds['family_selection']['probability_best_is_spurious']:.2f}",
     "scope_limit": "Medido sobre el conjunto de configuraciones de este estudio"},
    {"id": "C4",
     "claim": "Condicionar por regimen no rescata ninguna familia",
     "strength": "Moderada",
     "basis": f"{rc['n_cells']} celdas, {len(rc['survivors'])} supervivientes tras correccion; "
              "histograma de p compatible con la nula global",
     "scope_limit": "Condicionar reduce potencia; un efecto debil y estrecho podria escapar"},
    {"id": "C5",
     "claim": "La busqueda evolutiva no ofrece ventaja sobre Random Search aqui",
     "strength": "Moderada",
     "basis": "Cuaderno 04: paridad de presupuesto verificada; 1 de 5 familias nominalmente "
              "significativa, compatible con el azar en cinco pruebas",
     "scope_limit": "Espacios de este tamano; nada dice de espacios mucho mayores"},
    {"id": "C6",
     "claim": "El aparato es solido, asi que el negativo habla del mercado y no del utillaje",
     "strength": "Fuerte",
     "basis": "Cuaderno 02: garantias de causalidad G1-G7 sobre datos reales; cuaderno 03: guardas "
              "de ejecucion, coste y geometria verificadas y fallando en cerrado",
     "scope_limit": "Los costes siguen siendo provisionales (ADR 0005)"},
]
CONC = pl.DataFrame(conclusions)
save_table(CONC, "t09_conclusions", ctx,
           caption="Afirmaciones que el estudio sostiene, con su base de evidencia y sus limites "
                   "de alcance.")
display(CONC)
print(f"\nArtifacts written under : {ctx.figures_dir} | {ctx.tables_dir}")
"""
)

md(
    r"""
Es fácil leer este resultado como «los mercados son eficientes» o «el trading
algorítmico no funciona». Ninguna de las dos es lo que hemos demostrado.

Lo que sí hemos demostrado es más estrecho y, creemos, más útil: dentro de un
espacio bien acotado —trece familias interpretables, dos perpetuos líquidos,
velas de una hora, seis años, un modelo de costes realista— una búsqueda
rigurosa no encuentra nada que sobreviva a contar honestamente cuántas veces se
ha mirado. Y esa acotación importa tanto como el hallazgo: cada uno de esos
límites es un sitio donde otro estudio, con otros datos u otra frecuencia,
podría llegar a una respuesta distinta. Los límites de alcance van anotados
junto a cada afirmación, no enterrados.

¿Por qué nos fiamos de este negativo y no lo tratamos como «no encontramos nada
porque el aparato fallaba»? Por tres razones que se sostienen solas: el aparato
se validó antes de usarse y detectó al instante una fuga plantada a propósito
(cuadernos 02 y 03); la búsqueda tuvo una oportunidad justa, con presupuesto
igualado y verificado en cada familia; y el negativo lo confirman tres
diagnósticos metodológicamente independientes —contraste de hipótesis, Sharpe
deflactado y PBO— que podían haber discrepado y no lo hicieron.

Lo que cambiaría la conclusión: datos de mayor frecuencia, donde vive la
microestructura; un espacio de hipótesis más rico — la capa de meta-etiquetado
que esta fase especificó se ejecutó después sobre datos reales en contrato
exploratorio, y su resultado (mejora económica sin capacidad predictiva alguna:
toda la ganancia viene de abstenerse) apunta en la misma dirección que el resto
del estudio; activos con menos participación institucional; o una estructura de
costes de quien solo aporta liquidez. Cada una es una extensión concreta y
falsable, no una excusa.

La aportación metodológica es la más transferible: no el veredicto sobre
ninguna familia, sino la demostración de que el veredicto es *de fiar* — cada
paso entre el dato crudo y la conclusión es auditable, cada guarda falla en
cerrado en vez de avisar, y el único momento en que el proceso se torció quedó
registrado a la vista en lugar de alisado. Un estudio que publica su propia
discrepancia es más creíble que uno que solo reporta aciertos.

---

**Qué deja este cuaderno y a dónde va.** Figuras `j01` (criterios de
promoción), `j02` (corrección múltiple y sensibilidad del recuento), `j03`
(Sharpe deflactado y PBO) y `j04` (régimen), y tablas `t01`-`t09`, todas bajo
`reports/{figures,tables}/closure/`. Alimentan el capítulo 6 (resultados: j01,
j02, t01-t05), el capítulo 7 (limitaciones: j02b, t08 y la sección del holdout)
y el capítulo 8 (discusión: j03, j04, t09). El cuaderno 06 recoge el testigo:
toma la mejor familia rechazada y la sitúa dentro de la distribución del azar.
"""
)


def _write() -> None:
    nb = nbf.v4.new_notebook()
    nb["cells"] = CELLS
    nb["metadata"] = {
        "language_info": {"name": "python"},
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    }
    out = Path("notebooks/05_study_closure_and_multiple_testing.ipynb")
    out.write_text(nbf.writes(nb), encoding="utf-8")
    subprocess.run(["ruff", "check", "--fix", "--quiet", str(out)], check=False)
    subprocess.run(["ruff", "format", "--quiet", str(out)], check=False)
    print(f"Wrote {out} with {len(CELLS)} cells (ruff-formatted).")


if __name__ == "__main__":
    raise SystemExit(_write())
