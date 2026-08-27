"""Deterministically (re)build the synthesis notebook (08).

Run with: ``uv run python scripts/build_sintesis_notebook.py``

This notebook computes NOTHING. It chains the key figures of 01-07 into the
thesis argument in one reading. Its only code cell verifies that every figure
it embeds exists and records their hashes, so the chain breaks loudly if an
upstream notebook stops producing what this one shows.
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


FIGURES = [
    "eda/f03_price_evolution_drawdown",
    "features/g04_leakage_counterexample",
    "backtest/h05_walk_forward_geometry",
    "backtest/h02_cost_decomposition",
    "search/i02_selection_optimism",
    "search/i05_seed_instability",
    "closure/j02_multiple_testing",
    "closure/j03_deflated_sharpe_pbo",
    "eda/f27_macro_event_study",
    "closure/j05_crt_round",
    "closure/j06_overlay_and_dl",
    "ml/m01_economia_por_fold",
    "ml/m02_habilidad_predictiva",
    "montecarlo/k03_nula_con_la_estrategia_dentro",
    "montecarlo/k05_cuenta_fondeada",
]


def fig(name: str) -> str:
    return f"![{name}](../reports/figures/{name}.png)"


# --------------------------------------------------------------------------- #
md(
    r"""
# The complete argument, in one reading

**What question does this notebook answer?** None that is new: it chains what
notebooks 01-07 already established, in the order the argument holds together.
**On what data?** On their figures, exactly as they were saved -- nothing is
computed here and there is not a single analysis cell. **What will the reader
find?** The whole thesis in fifteen images: a difficult market, an apparatus
that does not fool itself, a search that finds noise, a verdict that
replicates on fresh hypothesis spaces -- nine intraday families, a news
overlay, a deep-learning annex -- and two layers, supervised learning and
Monte Carlo, that confirm it from angles that had no obligation to agree.

If only ten minutes are available to assess this work, this is the document.
"""
)

code(
    r"""
# Contract: this notebook only embeds figures. We verify they exist and record
# their hashes, so the chain breaks loudly if an upstream notebook stops
# producing what this one shows.
import hashlib
import os
import sys
from pathlib import Path

_root = Path.cwd()
while not (_root / "pyproject.toml").exists() and _root != _root.parent:
    _root = _root.parent
os.chdir(_root)

NB_CONTRACT = {
    "notebook": "08_sintesis",
    "inputs": [
        "reports/figures/eda/f03_price_evolution_drawdown.png",
        "reports/figures/features/g04_leakage_counterexample.png",
        "reports/figures/backtest/h05_walk_forward_geometry.png",
        "reports/figures/backtest/h02_cost_decomposition.png",
        "reports/figures/search/i02_selection_optimism.png",
        "reports/figures/search/i05_seed_instability.png",
        "reports/figures/closure/j02_multiple_testing.png",
        "reports/figures/closure/j03_deflated_sharpe_pbo.png",
        "reports/figures/eda/f27_macro_event_study.png",
        "reports/figures/closure/j05_crt_round.png",
        "reports/figures/closure/j06_overlay_and_dl.png",
        "reports/figures/ml/m01_economia_por_fold.png",
        "reports/figures/ml/m02_habilidad_predictiva.png",
        "reports/figures/montecarlo/k03_nula_con_la_estrategia_dentro.png",
        "reports/figures/montecarlo/k05_cuenta_fondeada.png",
    ],
    "outputs": {"figures": [], "tables": [], "dirs": []},
    "seed": None,
}

missing = [f for f in NB_CONTRACT["inputs"] if not Path(f).exists()]
if missing:
    raise FileNotFoundError(f"An upstream notebook no longer produces: {missing}")
for f in NB_CONTRACT["inputs"]:
    digest = hashlib.sha256(Path(f).read_bytes()).hexdigest()
    print(f"{digest[:16]}  {f}")
"""
)

md(
    rf"""
## 1. The terrain: six years containing everything

{fig("eda/f03_price_evolution_drawdown")}

Two liquid assets, 2020-2025: a 68% drawdown from highs, two bull markets,
endless sideways months. Anyone claiming an edge over this period cannot
attribute it to having seen only one regime -- and anyone failing to find one
cannot plead a shortage of variety either. *(Notebook 01.)*

## 2. The apparatus earned trust before it gave an opinion

{fig("features/g04_leakage_counterexample")}

Before evaluating any strategy, we planted an information leak on purpose -- a
feature that reads the future -- and confirmed the causality tests catch it
instantly. Tooling that cannot find the trap you set for it yourself has not
earned belief in anything else it reports. *(Notebook 02.)*

## 3. Time is respected and costs are paid

{fig("backtest/h05_walk_forward_geometry")}

{fig("backtest/h02_cost_decomposition")}

Fifteen walk-forward folds with purge and embargo derived rather than chosen
by eye, and an execution ledger charging fee, slippage and funding on every
bar. The signal is decided on the closed candle and executed at the next open:
the first price reachable without clairvoyance. *(Notebook 03.)*

## 4. The search finds... what noise hands out

{fig("search/i02_selection_optimism")}

{fig("search/i05_seed_instability")}

Selection optimism, measured: what the validation winner promises against what
it then delivers on test. And seed instability: changing the search's initial
randomness changes the winner -- fourteen distinct parameterisations across
fifteen folds in the later round. A search operating on structure converges;
one operating on noise shuffles. *(Notebook 04.)*

## 5. The verdict, told honestly

{fig("closure/j02_multiple_testing")}

{fig("closure/j03_deflated_sharpe_pbo")}

Thirteen families, 496,500 configurations examined, and the study's smallest
raw p-value sits at 0.345 -- far from the threshold *before* correcting
anything, and panel (b) shows no reasonable way of counting the tests changes
that. The deflated Sharpe says the best result does not clear what luck already
promised; the PBO, pinned at 0.5, says picking the in-sample best is a coin
toss. Three independent diagnostics, one message. *(Notebook 05.)*

## 6. The verdict replicates: nine more families, the news, and deep learning

{fig("eda/f27_macro_event_study")}

{fig("closure/j05_crt_round")}

{fig("closure/j06_overlay_and_dl")}

After the closure froze its denominator, three more attempts ran under frozen
rules of their own -- and reproduced the negative. Nine intraday liquidity
families at full study scale: zero of eighteen cells promoted, including one
(`pdl_reclaim_long` on BTC) that ends positive on all ten seeds and still
fails, its profit concentrated in a handful of trades no bootstrap interval
can distinguish from luck. A news brake built on a *true* fact -- volatility
multiplies by 2.5-3.2x around CPI and FOMC releases, the first image -- that
shifts its carrier's whole seed distribution downward on both assets, with
zero of ten seeds positive: a real fact about volatility is not yet a
tradable fact about returns. And an LSTM that edges the econometric HAR on
QLIKE for both assets but never earns the pre-registered Diebold-Mariano
rejection. Each round counted itself before running; none moved the verdict.
*(Notebooks 01 and 05.)*

## 7. And with supervised learning? It improves without knowing

{fig("ml/m01_economia_por_fold")}

{fig("ml/m02_habilidad_predictiva")}

The pre-registered trio -- logistic regression, random forest, LightGBM --
decides when to act on a primary's signals. The filtered arm loses less in
every fold... at a coin-level AUC: the entire improvement comes from abstaining
and cutting exposure, not from predicting. An economic improvement is not
evidence of knowledge, and keeping the two apart is what stops the first being
published as if it were the second. *(Notebook 06, exploratory contract.)*

## 8. The image that summarises the work

{fig("montecarlo/k03_nula_con_la_estrategia_dentro")}

The study's best family -- already rejected by the statistics -- against a
thousand versions of itself with the positions rotated at random over the same
bars: same exposure, same costs, zero information. The ten real runs scatter
inside the chance band, at percentiles from 0.22 to 0.97 -- exactly the way ten
draws scatter. The whole of chapter 5's statistics lives in this image.
*(Notebook 07.)*

## 9. And the warning with a number of its own

{fig("montecarlo/k05_cuenta_fondeada")}

Under the published rules of two real crypto prop firms -- mapped with their
sources, and with every unmodelled rule making passing harder -- this
chance-indistinguishable strategy clears phase 1 between 13.7% and 17.8% of the
time. A coin flip with the same trade timing and costs clears it between 9.2%
and 12.8%: a gap on the order of its own sampling error. Evaluation passes are
handed out to randomness often enough to manufacture believers, which is why
the platform's simulator exists. *(Notebook 07.)*

---

## What these fifteen images claim, and what they do not

They claim: that within this bounded space -- interpretable rules, intraday
liquidity patterns, a news overlay, a deep-learning volatility layer and a
meta-labeling layer, two perpetuals, hourly bars, six years, realistic costs
-- a rigorous search finds nothing that survives counting how many times we
looked, and that the measuring instrument was validated before and after with
planted traps, verified budgets and purpose-built nulls.

They do not claim: that markets are efficient, that algorithmic trading does
not work, or that another space -- higher frequency, more assets, different
information -- would return the same. Every limit of scope is a falsifiable
extension, and the first three are pre-registered in the future work.

The hardest thing to say is said too: the reserved partition was opened outside
protocol, the reading is withheld, and the commit chain proving it was kept
intact on purpose. A study that publishes its own discrepancy asks to be
believed on its records rather than its word -- and that, in the end, is the
standard this work proposes.
"""
)


def _write() -> None:
    nb = nbf.v4.new_notebook()
    nb["cells"] = CELLS
    nb["metadata"] = {
        "language_info": {"name": "python"},
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    }
    out = Path("notebooks/08_sintesis.ipynb")
    out.write_text(nbf.writes(nb), encoding="utf-8")
    subprocess.run(["ruff", "check", "--fix", "--quiet", str(out)], check=False)
    subprocess.run(["ruff", "format", "--quiet", str(out)], check=False)
    print(f"Wrote {out} with {len(CELLS)} cells (ruff-formatted).")


if __name__ == "__main__":
    _write()
