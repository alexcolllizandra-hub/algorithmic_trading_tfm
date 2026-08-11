"""Build the Gate S2-B development-pilot report from the completed runs.

Reads the run index written by ``scripts/run_s2_pilots.py``, summarises every
(family, asset, seed, engine, fold) arm, computes the common-candidate PBO that
S1-B could not, and writes the DEV-ONLY report to ``reports/``.

DEVELOPMENT DATA ONLY. The frozen holdout is never loaded; the development
partition boundary is asserted before any backtest runs.

Run with `uv run python scripts/analyse_s2_pilot.py`.
"""

from __future__ import annotations

from pathlib import Path

from perp_lab.config.models import Paths
from perp_lab.config.settings import load_data_contract, load_experiment_config
from perp_lab.data.splits import resolve_holdout_start
from perp_lab.eda.datasets import DataLake
from perp_lab.reporting.s2_common_candidates import (
    CommonCandidateError,
    common_candidate_pbo,
)
from perp_lab.reporting.s2_pilot import (
    build_arm,
    build_s2_pilot_report,
    load_pilot_index,
    write_s2_pilot_report,
)
from perp_lab.search.registry import S2_FAMILIES

INDEX_PATH = Path("artifacts/runs/s2b_pilot_index.json")
OUTPUT_DIR = Path("reports/gate_s2b")
TIMEFRAME = "1h"


def main() -> int:
    entries = load_pilot_index(INDEX_PATH)
    arms = [build_arm(entry) for entry in entries]
    print(f"summarised {len(arms)} arms from {INDEX_PATH}")

    exp = load_experiment_config()
    contract = load_data_contract()
    lake = DataLake(contract, Paths())
    holdout_start = resolve_holdout_start(contract)

    pbo_rows = []
    for symbol in sorted({arm["symbol"] for arm in arms}):
        bars = lake.load_klines(symbol, TIMEFRAME, partition="development").frame
        last = bars["open_time"].max()
        assert last is not None and last < holdout_start, (
            f"{symbol} development bars reach {last}, at or past the frozen holdout"
        )
        funding = lake.load_funding(symbol, partition="development").frame
        for family in S2_FAMILIES:
            try:
                result = common_candidate_pbo(
                    exp,
                    family=family,
                    symbol=symbol,
                    bars=bars,
                    funding=funding,
                    timeframe=TIMEFRAME,
                    holdout_start=holdout_start,
                )
            except CommonCandidateError as error:
                print(f"  PBO unavailable for {family}/{symbol}: {error}")
                continue
            pbo_rows.append(result.to_dict())
            print(
                f"  PBO {family:<22} {symbol}  "
                f"{result.pbo:.3f}  ({result.n_candidates_evaluated} configs, "
                f"{result.n_blocks} blocks)"
            )

    report = build_s2_pilot_report(arms, pbo=pbo_rows)
    written = write_s2_pilot_report(report, OUTPUT_DIR)
    print(f"\nwrote {written['json']}\nwrote {written['markdown']}")

    signal = report["partial_signal"]
    print(f"\npartial signal fires: {signal['any_family_fires']}")
    for verdict in signal["per_family_asset"]:
        seeds = verdict["seeds_meeting_all_conditions"]
        print(
            f"  {verdict['family']:<22} {verdict['symbol']}  "
            f"seeds meeting all conditions: {seeds or 'none'}  "
            f"-> {'FIRES' if verdict['partial_signal'] else 'no'}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
