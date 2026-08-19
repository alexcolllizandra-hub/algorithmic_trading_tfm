"""Deterministically (re)build the supervised meta-labeling notebook (06).

Run with: ``uv run python scripts/build_ml_notebook.py``

The notebook narrates a CLOSED exploratory artifact
(``reports/meta_labeling_real/meta_labeling_real.json``); it computes nothing
new and adds nothing to any test count. Figure and table names live under the
``ml/`` group (m01-m05, t01-t04) and are frozen once the thesis map cites them.
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
# Meta-etiquetado supervisado sobre datos reales

> **INFRAESTRUCTURA / EXPLORATORIO — §5 del contrato metodológico (ADR 0017).**
> El estudio que este cuaderno narra corrió sin primaria elegible (el cierre
> fue negativo), así que nada de lo que sigue es un hallazgo sobre la familia
> primaria ni promueve candidato alguno. Sus ajustes modelo-x-fold quedan fuera
> del denominador congelado del cierre y están contados en el artefacto.

**¿Qué pregunta responde este cuaderno?** Si un clasificador —regresión
logística, random forest o LightGBM, el trío preregistrado en
`experiment.yaml`— puede decidir *cuándo actuar* sobre las señales de una regla
primaria, y qué separa una mejora económica de una capacidad predictiva real.
**¿Con qué datos?** El artefacto cerrado del estudio walk-forward sobre 1.172
eventos reales de `crt_htf_range_reversal` en BTCUSDT (2020-2025, desarrollo).
**¿Qué va a encontrar el lector?** Que el brazo filtrado pierde menos dinero
que la primaria en los cuatro folds, y que esa mejora **no** proviene de saber
predecir: proviene de abstenerse y de operar menos. La parte incómoda es
doble: los bloques de test son diminutos (22-48 eventos), y en la primera
ejecución el trío fue en silencio un dúo — los NaN de warm-up excluían a la
logística y quedó registrado como «not fittable» en cada fold.

**Qué recibe del anterior.** El 05 cerró el estudio con cero supervivientes;
este cuaderno usa la mejor familia CRT *rechazada* como banco de pruebas del
utillaje supervisado. **Qué entrega al siguiente.** La distinción
económico-vs-predictivo que el 07 (Monte Carlo) generaliza: resultados
positivos compatibles con azar.

Todos los bloques de este cuaderno son **DESCRIPTIVOS**: leen un artefacto
cerrado. El único contraste que existió —la selección de modelo y umbral por
fold— ya está contado dentro del contrato exploratorio del artefacto.

### La pregunta local

- **P1.** ¿La mejora económica del filtro sobrevive a mirar su capacidad
  predictiva? (Alimenta **RQ3** de la memoria.)
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
    "notebook": "06_meta_etiquetado_supervisado",
    "inputs": ["reports/meta_labeling_real/meta_labeling_real.json"],
    "outputs": {
        "figures": ["m01_economia_por_fold", "m02_habilidad_predictiva",
                     "m03_calibracion", "m04_shap_importancia",
                     "m05_decision_y_regimen"],
        "tables": ["t01_resumen_folds", "t02_candidatos", "t03_shap",
                    "t04_por_regimen"],
        "dirs": ["reports/figures/ml", "reports/tables/ml"],
    },
    # El cuaderno no muestrea: lee un artefacto cerrado. La semilla del estudio
    # subyacente (42) vive en el propio artefacto.
    "seed": None,
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
from perp_lab.reporting import ArtifactContext, apply_house_style, save_figure, save_table

apply_house_style()
PATHS = Paths()
FIG_DPI = 300

PAYLOAD = json.loads(Path(NB_CONTRACT["inputs"][0]).read_text(encoding="utf-8"))
STUDY = PAYLOAD["study"]
SUMMARY = STUDY["summary"]
FOLDS = STUDY["folds"]

_contract = load_data_contract("configs/data_contract.yaml")
ctx = ArtifactContext(
    notebook=NB_CONTRACT["notebook"],
    figures_dir=PATHS.reports_root / "figures" / "ml",
    tables_dir=PATHS.reports_root / "tables" / "ml",
    metadata_dir=PATHS.reports_root / "metadata" / "ml",
    datasets=INPUT_HASHES,
    config={
        "seed": NB_CONTRACT["seed"],
        "study_seed": PAYLOAD["study"]["config"]["seed"],
        "code_commit_resolved": REPO_COMMIT,
        "data_contract_cutoff": str(_contract.cutoff_date),
        "contract_label": "INFRAESTRUCTURA/EXPLORATORIO (seccion 5; ADR 0017)",
        "family": PAYLOAD["family"],
        "symbol": PAYLOAD["symbol"],
        "n_events": PAYLOAD["n_events"],
        "models": PAYLOAD["study"]["config"]["models"],
    },
    period="development walk-forward out-of-sample; holdout never loaded",
    repo_root=".",
)


def show(fig, name, caption=""):
    save_figure(fig, name, ctx, caption=caption, dpi=FIG_DPI)
    display(fig)
    plt.close(fig)


print(f"contrato del estudio : {PAYLOAD['contract'][:80]}...")
print(f"primaria             : {PAYLOAD['family']} / {PAYLOAD['symbol']} {PAYLOAD['timeframe']}")
print(f"eventos etiquetados  : {PAYLOAD['n_events']} | tasa positiva "
      f"{PAYLOAD['meta_label_positive_rate']:.3f}")
print(f"modelos              : {', '.join(PAYLOAD['study']['config']['models'])}")
print(f"folds                : {SUMMARY['n_folds']} utiles ({len(SUMMARY['notes'] or [])} "
      f"descartados por <30 eventos)")
"""
)

md(
    r"""
La tasa positiva merece una pausa antes de mirar ningún modelo: **0,495**. De
cada dos señales de la primaria, una habría sido rentable tras costes y la otra
no. El clasificador parte de una moneda equilibrada — no hay clase mayoritaria
que explotar, y cualquier acierto tendrá que venir de las características, no
del desbalance.
"""
)

# --------------------------------------------------------------------------- #
# 1. Resumen por fold
# --------------------------------------------------------------------------- #
md(
    r"""
## 1. Qué pasó, fold a fold — `DESCRIPTIVO`

Cada fold entrena en su bloque, calibra y elige umbral **y modelo** en su
validación, y solo entonces mira el test una vez. El filtro puede abstenerse:
si ningún candidato mejora el retorno neto de la primaria *en validación*, el
brazo filtrado no opera ese fold. Abstenerse es una predicción, no una excusa a
posteriori.
"""
)

code(
    r"""
rows = []
for f in FOLDS:
    tp, tm, pr = f["test_primary"], f["test_meta"], f["test_predictive"]
    rows.append({
        "fold": f["fold"], "n_test": f["n_test"],
        "modelo": f["selected_model"], "actuo": not f["abstained"],
        "señales": f["test_signal_rate"],
        "ret_primaria": tp["net_return"], "ret_meta": tm["net_return"],
        "delta": f["net_return_delta"],
        "trades_prim": tp["n_trades"], "trades_meta": tm["n_trades"],
        "roc_auc": (pr or {}).get("roc_auc"),
        "pr_auc_lift": (pr or {}).get("pr_auc_lift"),
        "motivo_abstencion": (f["abstention_reason"] or "")[:70],
    })
T01 = pl.DataFrame(rows)
save_table(T01, "t01_resumen_folds", ctx,
           caption="Cada fold del estudio: modelo elegido, decisión de actuar, economía de ambos "
                   "brazos y habilidad predictiva donde el filtro operó.")
display(T01)

acted = T01.filter(pl.col("actuo"))
print(f"\nFolds que actuaron: {acted.height}/{T01.height}")
print(f"Retorno total primaria : {SUMMARY['primary_only_total_return']:+.4f}")
print(f"Retorno total filtrado : {SUMMARY['primary_plus_meta_total_return']:+.4f}")
print(f"Mejora en todos los folds: {SUMMARY['folds_improved']}/{SUMMARY['n_folds']}")
"""
)

code(
    r"""
# --- M01: la economia por fold ------------------------------------------------
ff = [f["fold"] for f in FOLDS]
prim = [f["test_primary"]["net_return"] for f in FOLDS]
meta = [f["test_meta"]["net_return"] for f in FOLDS]
abst = [f["abstained"] for f in FOLDS]
xx = np.arange(len(ff))

fig, ax = plt.subplots(figsize=(10.6, 5.2))
ax.bar(xx - 0.19, prim, width=0.36, color="#999999", label="primaria sola")
ax.bar(xx + 0.19, meta, width=0.36, color="#0072B2", hatch="///",
       label="primaria + filtro")
for i, a in enumerate(abst):
    if a:
        ax.annotate("se abstuvo", xy=(xx[i] + 0.19, 0), xytext=(0, 8),
                    textcoords="offset points", ha="center", fontsize=8.5,
                    color="#0072B2")
ax.axhline(0, color="black", lw=1.0)
ax.set_xticks(xx)
ax.set_xticklabels([f"fold {i}" for i in ff])
ax.set_ylabel("retorno neto del bloque de test")
ax.set_title("El filtro pierde menos en los cuatro folds — dos veces por no operar")
ax.legend(fontsize=9)
ax.grid(axis="x", visible=False)
fig.tight_layout()
show(fig, "m01_economia_por_fold",
     caption="Retorno neto por fold de la primaria sola frente a la primaria filtrada. Donde el "
             "filtro se abstiene, el brazo filtrado queda plano por construcción.")
"""
)

md(
    r"""
Los cuatro deltas son positivos, y la lectura ingenua —«el filtro funciona»—
dura hasta mirar *de dónde* sale cada delta. En los folds 0 y 3 el filtro no
operó: mejorar a una regla que pierde absteniéndose no requiere habilidad
alguna. En los folds 1 y 2 sí operó, con menos operaciones que la primaria
(26 frente a 44, y 9 frente a 42), y **siguió perdiendo dinero** — solo que
menos. La pregunta honesta no es si el brazo filtrado acaba mejor, sino si el
clasificador demuestra saber algo. Eso se mide en la sección siguiente, no en
esta.
"""
)

# --------------------------------------------------------------------------- #
# 2. Habilidad predictiva
# --------------------------------------------------------------------------- #
md(
    r"""
## 2. La habilidad predictiva, separada de la economía — `DESCRIPTIVO`

El ROC-AUC mide si el clasificador ordena bien los eventos (1 = perfecto,
0,5 = moneda); el PR-AUC lift compara su precisión-cobertura contra la tasa
base (1,0 = nada por encima del azar). Se calculan solo en los folds donde el
filtro actuó, porque en una abstención no hay predicciones que evaluar.
"""
)

code(
    r"""
# --- M02: AUC y lift por fold, con el tamano de test a la vista ---------------
act = [f for f in FOLDS if not f["abstained"] and f["test_predictive"]]
labels = [f"fold {f['fold']}\n({f['selected_model']}, n={f['test_predictive']['n']})"
          for f in act]
auc = [f["test_predictive"]["roc_auc"] for f in act]
lift = [f["test_predictive"]["pr_auc_lift"] for f in act]
xx = np.arange(len(act))

fig, (axA, axB) = plt.subplots(1, 2, figsize=(11.6, 4.8))
axA.bar(xx, auc, width=0.5, color="#0072B2")
axA.axhline(0.5, color="#D62728", lw=2.0, ls="--", label="moneda (0,5)")
axA.set_xticks(xx)
axA.set_xticklabels(labels, fontsize=9)
axA.set_ylim(0, 1)
axA.set_ylabel("ROC-AUC en test")
axA.set_title("(a) Ordenar eventos: al nivel de una moneda")
axA.legend(fontsize=9)
axA.grid(axis="x", visible=False)

axB.bar(xx, lift, width=0.5, color="#D55E00", hatch="///")
axB.axhline(1.0, color="#D62728", lw=2.0, ls="--", label="tasa base (lift 1,0)")
axB.set_xticks(xx)
axB.set_xticklabels(labels, fontsize=9)
axB.set_ylabel("PR-AUC / tasa base")
axB.set_title("(b) Precisión-cobertura: idem")
axB.legend(fontsize=9)
axB.grid(axis="x", visible=False)

fig.suptitle("Con 42-48 eventos por bloque, nada de esto se distingue del azar", fontsize=12)
fig.tight_layout()
show(fig, "m02_habilidad_predictiva",
     caption="ROC-AUC (a) y lift de PR-AUC sobre la tasa base (b) en los folds donde el filtro "
             "operó, con el modelo elegido y el tamaño del bloque de test.")
"""
)

md(
    r"""
El 0,601 del fold 1 es el número que más fácil se malinterpreta. Con 48
eventos y una tasa base del 0,5, el intervalo de un AUC estimado abarca
holgadamente la moneda: ese valor es tan compatible con azar como el 0,494 del
fold 2. La mediana entre ambos (0,548) no es evidencia de habilidad — es lo
que produce el ruido cuando se le dan dos oportunidades. Si el estudio hubiera
salido con AUC así sobre *miles* de eventos, la conversación sería otra; con
decenas, la única lectura defendible es la nula.
"""
)

# --------------------------------------------------------------------------- #
# 3. Calibracion
# --------------------------------------------------------------------------- #
md(
    r"""
## 3. Lo que dicen las probabilidades — `DESCRIPTIVO`

Las probabilidades de los clasificadores se calibran (isotónica) en la primera
mitad de la validación antes de elegir umbral en la segunda. Un modelo
calibrado y sin señal produce un diagrama de fiabilidad que serpentea alrededor
de la tasa base con bins minúsculos — exactamente lo que conviene enseñar.
"""
)

code(
    r"""
# --- M03: fiabilidad en los folds que actuaron ---------------------------------
fig, ax = plt.subplots(figsize=(7.2, 6.4))
markers = {1: "o", 2: "s"}
colors = {1: "#0072B2", 2: "#D55E00"}
for f in act:
    cal = f["calibration"] or []
    mp = [b["mean_predicted"] for b in cal]
    orate = [b["observed_rate"] for b in cal]
    nn = [b["n"] for b in cal]
    ax.scatter(mp, orate, s=[24 + 14 * n for n in nn], alpha=0.75,
               marker=markers.get(f["fold"], "o"), color=colors.get(f["fold"], "#0072B2"),
               label=f"fold {f['fold']} ({f['selected_model']})")
    for x, y, n in zip(mp, orate, nn, strict=True):
        ax.annotate(str(n), xy=(x, y), fontsize=7.5, ha="center", va="center")
ax.plot([0, 1], [0, 1], color="black", lw=1.4, ls="--", label="calibración perfecta")
ax.set_xlim(0, 1)
ax.set_ylim(-0.03, 1.03)
ax.set_xlabel("probabilidad media predicha (bin)")
ax.set_ylabel("frecuencia observada de acierto")
ax.set_title("Fiabilidad por bin — el número es cuántos eventos caen en cada bin")
ax.legend(fontsize=9, loc="upper left")
fig.tight_layout()
show(fig, "m03_calibracion",
     caption="Diagrama de fiabilidad de los folds que actuaron. Bins con 1-3 eventos hacen que "
             "cualquier desviación de la diagonal sea ruido de conteo, no descalibración.")
"""
)

# --------------------------------------------------------------------------- #
# 4. SHAP
# --------------------------------------------------------------------------- #
md(
    r"""
## 4. Atribuciones sobre señal inexistente — `DESCRIPTIVO`

SHAP descompone cada predicción del último ganador que actuó en contribuciones
por característica. Lo mostramos como diagnóstico del utillaje y como
advertencia: **las atribuciones se calculan igual de bien cuando el modelo no
sabe clasificar**. Una lista de features «importantes» no es un descubrimiento
de señal; es la anatomía de las decisiones de un modelo cuya tasa de acierto ya
medimos arriba.
"""
)

code(
    r"""
shap_rows = STUDY.get("shap_importance") or []
T03 = pl.DataFrame(shap_rows)
save_table(T03, "t03_shap", ctx,
           caption="Importancia media |SHAP| por característica para el último modelo ganador "
                   "que actuó. Diagnóstico del utillaje, no descubrimiento de señal.")
display(T03)

fig, ax = plt.subplots(figsize=(8.8, 4.8))
feats_ = [r["feature"] for r in shap_rows][::-1]
vals = [r["mean_abs_shap"] for r in shap_rows][::-1]
ax.barh(feats_, vals, color="#0072B2")
ax.set_xlabel("media de |SHAP| sobre los eventos de test explicados")
ax.set_title("Un ranking perfectamente computable de un modelo que no acierta")
fig.tight_layout()
show(fig, "m04_shap_importancia",
     caption="Importancias SHAP del último ganador que actuó. Se muestran como advertencia "
             "metodológica: la atribución no implica capacidad predictiva.")
"""
)

# --------------------------------------------------------------------------- #
# 5. Decision y regimen
# --------------------------------------------------------------------------- #
md(
    r"""
## 5. Dónde decide actuar, y en qué régimen — `DESCRIPTIVO`

Dos vistas del comportamiento del filtro: cuánta señal deja pasar cada fold
(con su motivo cuando se abstiene), y cómo se reparten los eventos aceptados
por régimen de volatilidad.
"""
)

code(
    r"""
cand_rows = []
for f in FOLDS:
    for c in f["candidates"]:
        vm = c.get("validation_metrics") or {}
        cand_rows.append({
            "fold": f["fold"], "modelo": c["model"], "disponible": c["available"],
            "delta_validacion": c.get("validation_delta"),
            "umbral": (c.get("threshold") or {}).get("threshold"),
            "auc_validacion": vm.get("roc_auc"),
            "elegido": c["model"] == f["selected_model"],
        })
T02 = pl.DataFrame(cand_rows)
save_table(T02, "t02_candidatos", ctx,
           caption="Los tres candidatos preregistrados en cada fold: disponibilidad, delta de "
                   "validación, umbral elegido y AUC de validación.")
display(T02)

reg_rows = []
for f in FOLDS:
    for r in f.get("per_regime") or []:
        reg_rows.append({"fold": f["fold"], **{k: r[k] for k in
                        ("regime", "n_events", "base_rate", "accepted")}})
T04 = pl.DataFrame(reg_rows)
save_table(T04, "t04_por_regimen", ctx,
           caption="Eventos y aceptaciones del filtro por régimen de volatilidad y fold.")
display(T04.head(8))
"""
)

code(
    r"""
# --- M05: decision por fold y aceptacion por regimen ---------------------------
fig, (axA, axB) = plt.subplots(1, 2, figsize=(12.2, 4.9),
                               gridspec_kw={"width_ratios": [1.0, 1.0]})

sr = [f["test_signal_rate"] for f in FOLDS]
xx = np.arange(len(FOLDS))
bars = axA.bar(xx, sr, width=0.5,
               color=["#BBBBBB" if f["abstained"] else "#0072B2" for f in FOLDS],
               hatch=["" if f["abstained"] else "///" for f in FOLDS])
axA.set_xticks(xx)
axA.set_xticklabels([f"fold {f['fold']}" for f in FOLDS])
axA.set_ylabel("fracción de señales aceptadas en test")
axA.set_title("(a) Cuánta señal deja pasar (gris = se abstuvo)")
axA.grid(axis="x", visible=False)

agg = (T04.group_by("regime")
       .agg(pl.col("n_events").sum(), pl.col("accepted").sum())
       .sort("regime"))
regs = agg["regime"].to_list()
yy = np.arange(len(regs))
axB.barh(yy + 0.18, agg["n_events"].to_list(), height=0.34, color="#999999",
         label="eventos de la primaria")
axB.barh(yy - 0.18, agg["accepted"].to_list(), height=0.34, color="#0072B2",
         hatch="///", label="aceptados por el filtro")
axB.set_yticks(yy)
axB.set_yticklabels(regs)
axB.set_xlabel("eventos (todos los folds)")
axB.set_title("(b) Aceptación por régimen de volatilidad")
axB.legend(fontsize=9)
axB.grid(axis="y", visible=False)

fig.suptitle("El filtro sobrevive recortando exposición, no eligiendo bien", fontsize=12)
fig.tight_layout()
show(fig, "m05_decision_y_regimen",
     caption="Fracción de señales aceptadas por fold (a) y reparto de eventos frente a "
             "aceptaciones por régimen de volatilidad (b).")
"""
)

# --------------------------------------------------------------------------- #
# Cierre
# --------------------------------------------------------------------------- #
md(
    r"""
## 6. Lo que este experimento establece — y lo que lo habría contradicho

Establece tres cosas, todas bajo la etiqueta de infraestructura con la que
abrimos. Primera: la maquinaria supervisada completa —triple barrera sobre
retornos netos, calibración isotónica, selección de umbral y de modelo en
bloques purgados, tres backends, SHAP— funciona de punta a punta sobre datos
reales sin fugas estructurales, porque la función de ajuste ni siquiera acepta
el bloque de test. Segunda: sobre esta primaria y estas características, la
mejora económica del filtro es una historia de **abstención y recorte de
exposición**, no de predicción — los AUC son de moneda y los bloques de test
son demasiado pequeños para acreditar otra cosa. Tercera: el episodio de la
logística excluida por NaN quedó registrado como «no disponible» en vez de
sustituirse en silencio, que es exactamente el comportamiento que se le pide a
un banco de pruebas.

Lo que habría contradicho esta lectura, y no ocurrió: AUC consistentemente por
encima de 0,5 en bloques grandes, mejora económica concentrada en los folds
donde el filtro *actúa* con cobertura alta, y un ranking SHAP estable entre
folds respaldado por aciertos. Ninguna de las tres condiciones se dio.

Dejamos también dicho lo que este cuaderno **no** dice: no dice que el
meta-etiquetado no funcione — dice que no puede rescatar a una primaria sin
edge, que es distinto y era lo esperable. La capa queda validada y lista para
el día en que exista una primaria que la merezca, sobre datos nuevos y con su
denominador contado.

### De la pregunta local a la memoria

| Pregunta local | Alimenta | Cómo |
|---|---|---|
| P1 (¿economía o predicción?) | RQ3 | respuesta directa bajo contrato exploratorio: la mejora existe y no es predictiva |

---

**Qué deja este cuaderno y a dónde va.** Figuras `m01`-`m05` y tablas
`t01`-`t04` bajo `reports/{figures,tables}/ml/`. Alimentan el capítulo 5.8
(metodología de la capa) y la subsección RQ3 del capítulo 6; `m04` es también
material del capítulo 7 (la advertencia sobre atribuciones). El cuaderno 07
recoge el testigo: si una mejora económica puede no ser predicción, el Monte
Carlo pregunta cuánto de *cualquier* resultado positivo cabe esperar del puro
azar.
"""
)


def _write() -> None:
    nb = nbf.v4.new_notebook()
    nb["cells"] = CELLS
    nb["metadata"] = {
        "language_info": {"name": "python"},
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    }
    out = Path("notebooks/06_meta_etiquetado_supervisado.ipynb")
    out.write_text(nbf.writes(nb), encoding="utf-8")
    subprocess.run(["ruff", "check", "--fix", "--quiet", str(out)], check=False)
    subprocess.run(["ruff", "format", "--quiet", str(out)], check=False)
    print(f"Wrote {out} with {len(CELLS)} cells (ruff-formatted).")


if __name__ == "__main__":
    _write()
