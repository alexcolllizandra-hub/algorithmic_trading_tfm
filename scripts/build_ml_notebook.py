"""Deterministically (re)build the supervised meta-labeling notebook (06).

Run with: ``uv run python scripts/build_ml_notebook.py``

The notebook narrates a CLOSED exploratory artifact
(``reports/meta_labeling_real/meta_labeling_real.json``); it computes nothing
new and adds nothing to any test count. Prose is English (repo-wide policy,
2026-08-19). Figure and table names under ``ml/`` (m01-m05, t01-t04) are frozen
identifiers cited by the thesis map.
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


# Apertura
md(
    r"""
# Supervised meta-labeling on real data

> **INFRASTRUCTURE / EXPLORATORY — methodology contract section 5 (ADR 0017).**
> The study this notebook narrates ran with no eligible primary (the closure
> was negative), so nothing here is a finding about the primary family and
> nothing promotes any candidate. Its model-by-fold fits sit outside the
> closure's frozen denominator and are counted in the artifact.

**What question does this notebook answer?** Whether a classifier — logistic
regression, random forest or LightGBM, the trio pre-registered in
`experiment.yaml` — can decide *when to act* on a primary rule's signals, and
what separates an economic improvement from genuine predictive skill. **On
what data?** The closed walk-forward artifact over 1,172 real events of
`crt_htf_range_reversal` on BTCUSDT (2020-2025, development). **What will the
reader find?** That the filtered arm loses less money than the primary in all
four folds, and that the improvement does **not** come from knowing how to
predict: it comes from abstaining and from trading less. The uncomfortable
part is twofold: the test blocks are tiny (22-48 events), and on the first run
the trio was silently a duo — warm-up NaNs excluded logistic regression, which
was recorded as "not fittable" in every fold.

**What it receives from the previous notebook.** 05 closed the study with zero
survivors; this one uses the best *rejected* CRT family as a test bench for
the supervised tooling. **What it hands to the next.** The
economics-versus-prediction distinction that 07 (Monte Carlo) generalises:
positive results compatible with chance.

Every block here is **DESCRIPTIVE**: it reads a closed artifact. The only test
that ever existed — model and threshold selection per fold — is already
counted inside the artifact's exploratory contract.

### The local question

- **Q1.** Does the filter's economic improvement survive a look at its
  predictive skill? (Feeds **RQ3** of the thesis.)
"""
)

# Setup + contrato
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
The base rate deserves a pause before any model is looked at: **0.495**. Of
every two signals the primary fires, one would have been profitable after
costs and one would not. The classifier starts from a balanced coin — there is
no majority class to exploit, and any skill will have to come from the
features, not from the imbalance.
"""
)

# 1. Resumen por fold
md(
    r"""
## 1. What happened, fold by fold — `DESCRIPTIVE`

Each fold trains on its block, calibrates and picks a threshold **and a model**
on its validation slice, and only then looks at test once. The filter may
abstain: if no candidate improves the primary's net return *on validation*, the
filtered arm does not trade that fold. Abstaining is a prediction, not a
post-hoc excuse.
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
           caption="Every fold of the study: model chosen, decision to act, economics of both "
                   "arms, and predictive skill where the filter traded.")
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
ax.bar(xx - 0.19, prim, width=0.36, color="#999999", label="primary alone")
ax.bar(xx + 0.19, meta, width=0.36, color="#0072B2", hatch="///",
       label="primary + filter")
for i, a in enumerate(abst):
    if a:
        ax.annotate("abstained", xy=(xx[i] + 0.19, 0), xytext=(0, 8),
                    textcoords="offset points", ha="center", fontsize=8.5,
                    color="#0072B2")
ax.axhline(0, color="black", lw=1.0)
ax.set_xticks(xx)
ax.set_xticklabels([f"fold {i}" for i in ff])
ax.set_ylabel("net return of the test block")
ax.set_title("The filter loses less in all four folds - twice by not trading")
ax.legend(fontsize=9)
ax.grid(axis="x", visible=False)
fig.tight_layout()
show(fig, "m01_economia_por_fold",
     caption="Net return per fold of the primary alone against the filtered primary. Where the "
             "filter abstains, the filtered arm is flat by construction.")
"""
)

md(
    r"""
All four deltas are positive, and the naive reading — "the filter works" —
survives exactly until you ask *where* each delta comes from. In folds 0 and 3
the filter did not trade: beating a losing rule by abstaining requires no skill
whatsoever. In folds 1 and 2 it did trade, with fewer trades than the primary
(26 against 44, and 9 against 42), and it **still lost money** — just less. The
honest question is not whether the filtered arm ends up better, but whether the
classifier demonstrates knowing anything. That is measured in the next section,
not this one.
"""
)

# 2. Habilidad predictiva
md(
    r"""
## 2. Predictive skill, separated from economics — `DESCRIPTIVE`

ROC-AUC measures whether the classifier ranks events well (1 = perfect,
0.5 = coin); PR-AUC lift compares its precision-recall against the base rate
(1.0 = nothing above chance). Both are computed only on folds where the filter
acted, because an abstention leaves no predictions to score.
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
axA.axhline(0.5, color="#D62728", lw=2.0, ls="--", label="coin (0.5)")
axA.set_xticks(xx)
axA.set_xticklabels(labels, fontsize=9)
axA.set_ylim(0, 1)
axA.set_ylabel("ROC-AUC on test")
axA.set_title("(a) Ranking events: at coin level")
axA.legend(fontsize=9)
axA.grid(axis="x", visible=False)

axB.bar(xx, lift, width=0.5, color="#D55E00", hatch="///")
axB.axhline(1.0, color="#D62728", lw=2.0, ls="--", label="base rate (lift 1.0)")
axB.set_xticks(xx)
axB.set_xticklabels(labels, fontsize=9)
axB.set_ylabel("PR-AUC / base rate")
axB.set_title("(b) Precision-recall: same")
axB.legend(fontsize=9)
axB.grid(axis="x", visible=False)

fig.suptitle("With 42-48 events per block, none of this separates from chance", fontsize=12)
fig.tight_layout()
show(fig, "m02_habilidad_predictiva",
     caption="ROC-AUC (a) and PR-AUC lift over the base rate (b) on the folds where the filter "
             "traded, with the model chosen and the test block size.")
"""
)

md(
    r"""
Fold 1's 0.601 is the number most easily misread. With 48 events and a base
rate of 0.5, the interval around an estimated AUC comfortably spans the coin:
that value is as compatible with chance as fold 2's 0.494. The median of the
two (0.548) is not evidence of skill — it is what noise produces when given two
chances. Had the study returned AUCs like these over *thousands* of events, the
conversation would be different; over dozens, the null is the only defensible
reading.
"""
)

# 3. Calibracion
md(
    r"""
## 3. What the probabilities say — `DESCRIPTIVE`

Classifier probabilities are calibrated (isotonic) on the first half of the
validation slice before a threshold is chosen on the second. A calibrated model
with no signal produces a reliability diagram that wanders around the base rate
in tiny bins — exactly what is worth showing.
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
ax.plot([0, 1], [0, 1], color="black", lw=1.4, ls="--", label="perfect calibration")
ax.set_xlim(0, 1)
ax.set_ylim(-0.03, 1.03)
ax.set_xlabel("mean predicted probability (bin)")
ax.set_ylabel("observed hit frequency")
ax.set_title("Reliability per bin - the number is how many events fall in each bin")
ax.legend(fontsize=9, loc="upper left")
fig.tight_layout()
show(fig, "m03_calibracion",
     caption="Reliability diagram of the acting folds. Bins holding 1-3 events make any "
             "departure from the diagonal counting noise, not miscalibration.")
"""
)

# 4. SHAP
md(
    r"""
## 4. Attributions over a signal that is not there — `DESCRIPTIVE`

SHAP decomposes each prediction of the last acting winner into per-feature
contributions. We show it as a diagnostic of the tooling and as a warning:
**attributions compute just as cleanly when the model cannot classify**. A list
of "important" features is not a signal discovery; it is the anatomy of the
decisions of a model whose hit rate we measured above.
"""
)

code(
    r"""
shap_rows = STUDY.get("shap_importance") or []
T03 = pl.DataFrame(shap_rows)
save_table(T03, "t03_shap", ctx,
           caption="Mean |SHAP| importance per feature for the last acting winning model. A "
                   "diagnostic of the tooling, not a signal discovery.")
display(T03)

fig, ax = plt.subplots(figsize=(8.8, 4.8))
feats_ = [r["feature"] for r in shap_rows][::-1]
vals = [r["mean_abs_shap"] for r in shap_rows][::-1]
ax.barh(feats_, vals, color="#0072B2")
ax.set_xlabel("mean |SHAP| over the explained test events")
ax.set_title("A perfectly computable ranking from a model that does not hit")
fig.tight_layout()
show(fig, "m04_shap_importancia",
     caption="SHAP importances of the last acting winner, shown as a methodological warning: "
             "attribution does not imply predictive skill.")
"""
)

# 5. Decision y regimen
md(
    r"""
## 5. Where it decides to act, and in which regime — `DESCRIPTIVE`

Two views of the filter's behaviour: how much signal each fold lets through
(with its reason when it abstains), and how accepted events distribute across
volatility regimes.
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
           caption="The three pre-registered candidates in each fold: availability, validation "
                   "delta, chosen threshold and validation AUC.")
display(T02)

reg_rows = []
for f in FOLDS:
    for r in f.get("per_regime") or []:
        reg_rows.append({"fold": f["fold"], **{k: r[k] for k in
                        ("regime", "n_events", "base_rate", "accepted")}})
T04 = pl.DataFrame(reg_rows)
save_table(T04, "t04_por_regimen", ctx,
           caption="Events and filter acceptances by volatility regime and fold.")
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
axA.set_ylabel("share of signals accepted on test")
axA.set_title("(a) How much signal it lets through (grey = abstained)")
axA.grid(axis="x", visible=False)

# maintain_order: group_by does not guarantee row order; the explicit sort on
# a unique key makes the result reproducible regardless.
agg = (T04.group_by("regime", maintain_order=True)
       .agg(pl.col("n_events").sum(), pl.col("accepted").sum())
       .sort("regime"))
regs = agg["regime"].to_list()
yy = np.arange(len(regs))
axB.barh(yy + 0.18, agg["n_events"].to_list(), height=0.34, color="#999999",
         label="primary events")
axB.barh(yy - 0.18, agg["accepted"].to_list(), height=0.34, color="#0072B2",
         hatch="///", label="accepted by the filter")
axB.set_yticks(yy)
axB.set_yticklabels(regs)
axB.set_xlabel("events (all folds)")
axB.set_title("(b) Acceptance by volatility regime")
axB.legend(fontsize=9)
axB.grid(axis="y", visible=False)

fig.suptitle("The filter survives by cutting exposure, not by choosing well", fontsize=12)
fig.tight_layout()
show(fig, "m05_decision_y_regimen",
     caption="Share of signals accepted per fold (a) and events against acceptances by "
             "volatility regime (b).")
"""
)

# Cierre
md(
    r"""
## 6. What this experiment establishes — and what would have contradicted it

It establishes three things, all under the infrastructure label we opened
with. First: the complete supervised machinery — triple-barrier labels on net
returns, isotonic calibration, threshold and model selection on purged blocks,
three backends, SHAP — runs end to end on real data with no structural leakage,
because the fitting function does not even accept the test block. Second: on
this primary and these features, the filter's economic improvement is a story
of **abstention and exposure throttling**, not of prediction — the AUCs are
coin-level and the test blocks are too small to certify anything else. Third:
the episode of the NaN-excluded logistic regression was recorded as
"unavailable" rather than silently substituted, which is exactly the behaviour
a test bench is supposed to have.

What would have contradicted this reading, and did not occur: AUCs
consistently above 0.5 on large blocks, economic improvement concentrated in
the folds where the filter *acts* with high coverage, and a SHAP ranking stable
across folds and backed by hits. None of the three held.

We also state what this notebook does **not** say: it does not say
meta-labeling fails — it says it cannot rescue a primary with no edge, which is
a different claim and was the expected one. The layer stands validated and
ready for the day an eligible primary exists, on new data and with its own
denominator counted.

### From the local question to the thesis

| Local question | Feeds | How |
|---|---|---|
| Q1 (economics or prediction?) | RQ3 | direct answer under the exploratory contract: the improvement is real and is not predictive |

---

**What this notebook leaves behind, and where it goes.** Figures `m01`-`m05`
and tables `t01`-`t04` under `reports/{figures,tables}/ml/`. They feed chapter
5.8 (methodology of the layer) and the RQ3 subsection of chapter 6; `m04` is
also chapter 7 material (the warning about attributions). Notebook 07 takes the
baton: if an economic improvement can fail to be prediction, Monte Carlo asks
how much of *any* positive result chance alone would hand out.
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
