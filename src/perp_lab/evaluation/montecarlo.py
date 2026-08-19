"""Monte Carlo machinery for situating a strategy inside the distribution of chance.

Everything here is DESCRIPTIVE resampling of an already-closed result: it
quantifies how little a rejected strategy is distinguishable from luck, and it
exercises the risk machinery on real ledgers. Nothing in this module performs
or implies a new hypothesis test, and no output of it can promote anything --
the reserved partition is consumed (holdout_audit_status.md section 5.1).

Four generators plus two evaluators:

* :func:`iid_trade_bootstrap` -- resample closed trades with replacement. Asks
  "given this bag of trade outcomes, what paths could their composition have
  produced?"; sensitive to both the return distribution and the sequencing.
* :func:`permutation_paths` -- shuffle trade order without replacement. The
  compounded total return is invariant by construction, so any spread in
  drawdown and time-under-water isolates pure sequencing luck.
* :func:`stationary_bar_bootstrap` -- Politis-Romano stationary bootstrap over
  per-bar net returns (indices from
  :func:`perp_lab.evaluation.multiple_testing.stationary_bootstrap_indices`),
  preserving local autocorrelation with the expected block length reported by
  :func:`suggest_block_length`.
* :func:`null_circular_shifts` -- the null model: rotate the position series by
  a random offset against the same bar returns and re-price costs and funding
  identically. A rotation preserves the exposure share, the number of trades
  and the turnover exactly, while destroying any alignment between signal and
  future returns. Where the real strategy lands inside this distribution is
  the summary picture of the study.
* :func:`cost_multiplier_sweep` -- re-price the real ledger at cost multiples
  and report where the total return crosses zero.
* :func:`prop_firm_pass_probability` -- apply funded-account (prop-firm) style
  rules to bootstrap paths. The rules are inputs, never conclusions.

Determinism: every function takes a ``seed`` and draws only from its own
``numpy`` generator.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import polars as pl

BAR_NET_RETURN_EXPR = (
    pl.col("gross_return") - pl.col("fee") - pl.col("slippage") + pl.col("funding")
)


def bar_net_returns(ledger: pl.DataFrame) -> np.ndarray:
    """Per-bar net returns of the strategy from an engine ledger."""
    return ledger.select(BAR_NET_RETURN_EXPR.alias("r"))["r"].to_numpy().astype(float)


def path_metrics(returns: np.ndarray) -> dict[str, float]:
    """Compounded total return, per-observation Sharpe, max drawdown, time under water."""
    r = np.asarray(returns, dtype=float)
    if r.size == 0:
        return {"total_return": 0.0, "sharpe": 0.0, "max_drawdown": 0.0, "time_under_water": 0.0}
    equity = np.cumprod(1.0 + r)
    peak = np.maximum.accumulate(equity)
    drawdown = equity / peak - 1.0
    std = float(r.std(ddof=1)) if r.size > 1 else 0.0
    return {
        "total_return": float(equity[-1] - 1.0),
        "sharpe": float(r.mean() / std) if std > 0 else 0.0,
        "max_drawdown": float(drawdown.min()),
        "time_under_water": float((drawdown < 0).mean()),
    }


def _metric_table(paths: list[dict[str, float]]) -> dict[str, np.ndarray]:
    keys = ("total_return", "sharpe", "max_drawdown", "time_under_water")
    return {k: np.array([p[k] for p in paths], dtype=float) for k in keys}


def percentile_of(value: float, distribution: np.ndarray) -> float:
    """Share of the distribution at or below ``value``, in [0, 1]."""
    d = np.asarray(distribution, dtype=float)
    if d.size == 0:
        return float("nan")
    return float((d <= value).mean())


def suggest_block_length(
    returns: np.ndarray, *, max_lag: int = 168, floor: int = 6, ceiling: int = 168
) -> dict[str, Any]:
    """Heuristic stationary-bootstrap block length from the autocorrelation.

    The last lag whose absolute autocorrelation exceeds the 2/sqrt(n) noise band
    marks how far dependence visibly reaches; the block length is that horizon
    bounded to [floor, ceiling] bars. This is a documented heuristic, not the
    Politis-White optimal estimator: the notebook reports the ACF alongside so
    the choice is inspectable, and the bootstrap results are shown at the
    suggested length.
    """
    r = np.asarray(returns, dtype=float)
    n = r.size
    demeaned = r - r.mean()
    denom = float((demeaned**2).sum())
    band = 2.0 / np.sqrt(n)
    acf = []
    last_significant = 0
    for lag in range(1, min(max_lag, n // 4) + 1):
        rho = float((demeaned[lag:] * demeaned[:-lag]).sum() / denom) if denom > 0 else 0.0
        acf.append(rho)
        if abs(rho) > band:
            last_significant = lag
    block = int(min(max(last_significant, floor), ceiling))
    return {
        "block_length": block,
        "last_significant_lag": last_significant,
        "noise_band": float(band),
        "acf": np.array(acf, dtype=float),
    }


def _stationary_indices(
    n_observations: int, path_length: int, mean_block_length: float, rng: np.random.Generator
) -> np.ndarray:
    """Stationary-bootstrap index path of arbitrary length.

    Same geometric-block construction as
    :func:`perp_lab.evaluation.multiple_testing.stationary_bootstrap_indices`
    (restart at a uniform position with probability 1/mean_block_length at each
    step); generalised here because prop-firm simulation needs paths longer
    than the sample, which the inference-layer helper deliberately does not
    offer. That helper stays untouched: it belongs to the closed inferential
    layer.
    """
    p = 1.0 / max(mean_block_length, 1.0)
    restarts = rng.random(path_length) < p
    restarts[0] = True
    positions = rng.integers(0, n_observations, size=path_length)
    idx = np.empty(path_length, dtype=np.int64)
    current = 0
    for i in range(path_length):
        current = positions[i] if restarts[i] else (current + 1) % n_observations
        idx[i] = current
    return idx


def iid_trade_bootstrap(
    trade_returns: np.ndarray, *, n_resamples: int = 1000, seed: int = 42
) -> dict[str, np.ndarray]:
    """Resample closed-trade net returns with replacement; metrics per path."""
    r = np.asarray(trade_returns, dtype=float)
    rng = np.random.default_rng(seed)
    paths = [path_metrics(r[rng.integers(0, r.size, size=r.size)]) for _ in range(int(n_resamples))]
    return _metric_table(paths)


def permutation_paths(
    trade_returns: np.ndarray, *, n_resamples: int = 1000, seed: int = 42
) -> dict[str, np.ndarray]:
    """Shuffle trade order without replacement; total return is invariant."""
    r = np.asarray(trade_returns, dtype=float)
    rng = np.random.default_rng(seed)
    paths = [path_metrics(rng.permutation(r)) for _ in range(int(n_resamples))]
    return _metric_table(paths)


def stationary_bar_bootstrap(
    returns: np.ndarray,
    *,
    block_length: int,
    n_resamples: int = 1000,
    seed: int = 42,
) -> dict[str, np.ndarray]:
    """Politis-Romano stationary bootstrap of per-bar net returns."""
    r = np.asarray(returns, dtype=float)
    rng = np.random.default_rng(seed)
    paths = [
        path_metrics(r[_stationary_indices(r.size, r.size, float(block_length), rng)])
        for _ in range(int(n_resamples))
    ]
    return _metric_table(paths)


def null_circular_shifts(
    ledger: pl.DataFrame,
    *,
    n_shifts: int = 1000,
    min_offset_bars: int = 24,
    seed: int = 42,
) -> dict[str, Any]:
    """Rotate the position series against the same bars; re-price identically.

    The rotation preserves exposure share, trade count and turnover exactly
    (up to the single wrap-around boundary), so the null differs from the real
    strategy in one thing only: whether the positions know anything about the
    returns in front of them. Costs are re-charged from the rotated turnover at
    the run's own realised cost rate, and funding is re-charged from the
    rotated positions against the bar-aligned funding rate.
    """
    position = ledger["position"].to_numpy().astype(float)
    oo = ledger["oo_return"].to_numpy().astype(float)
    funding_rate = ledger["funding_rate_in_bar"].to_numpy().astype(float)

    turnover_real = np.abs(np.diff(position, prepend=0.0)).sum()
    cost_real = float((ledger["fee"] + ledger["slippage"]).sum())
    cost_per_turnover = (cost_real / turnover_real) if turnover_real > 0 else 0.0

    n = position.size
    rng = np.random.default_rng(seed)
    offsets = rng.integers(min_offset_bars, n - min_offset_bars, size=int(n_shifts))

    paths: list[dict[str, float]] = []
    for off in offsets:
        pos = np.roll(position, int(off))
        gross = pos * oo
        turnover = np.abs(np.diff(pos, prepend=0.0))
        net = gross - cost_per_turnover * turnover + pos * funding_rate
        paths.append(path_metrics(net))

    real = path_metrics(bar_net_returns(ledger))
    table = _metric_table(paths)
    return {
        "null": table,
        "real": real,
        "real_percentile": {k: percentile_of(real[k], v) for k, v in table.items()},
        "cost_per_turnover": float(cost_per_turnover),
        "exposure_share": float((position != 0).mean()),
        "offsets": offsets,
    }


def cost_multiplier_sweep(
    ledger: pl.DataFrame, *, multipliers: tuple[float, ...] = (0.0, 0.5, 1.0, 1.5, 2.0, 3.0)
) -> pl.DataFrame:
    """Re-price the real path at cost multiples; report metrics per multiple.

    Positions are unchanged -- only the already-charged fee and slippage are
    scaled, which is the same convention as the robustness battery's 2x stress
    (`evaluation/robustness.stress_costs`).
    """
    gross = ledger["gross_return"].to_numpy().astype(float)
    fee = ledger["fee"].to_numpy().astype(float)
    slippage = ledger["slippage"].to_numpy().astype(float)
    funding = ledger["funding"].to_numpy().astype(float)

    rows = []
    for m in multipliers:
        net = gross - m * (fee + slippage) + funding
        rows.append({"multiplier": float(m), **path_metrics(net)})
    return pl.DataFrame(rows)


def breakeven_multiplier(sweep: pl.DataFrame) -> float | None:
    """Linear interpolation of the multiplier where total return crosses zero."""
    s = sweep.sort("multiplier")
    m = s["multiplier"].to_numpy()
    t = s["total_return"].to_numpy()
    for i in range(1, m.size):
        if t[i - 1] > 0 >= t[i]:
            span = t[i - 1] - t[i]
            frac = t[i - 1] / span if span != 0 else 0.0
            return float(m[i - 1] + frac * (m[i] - m[i - 1]))
    return None


@dataclass(frozen=True)
class PropFirmRules:
    """Funded-account evaluation rules. Inputs to a simulation, never findings."""

    profit_target: float = 0.08
    max_total_drawdown: float = 0.10
    max_daily_loss: float = 0.05
    max_days: int = 60
    bars_per_day: int = 24

    def to_dict(self) -> dict[str, float | int]:
        return {
            "profit_target": self.profit_target,
            "max_total_drawdown": self.max_total_drawdown,
            "max_daily_loss": self.max_daily_loss,
            "max_days": self.max_days,
            "bars_per_day": self.bars_per_day,
        }


def _phase_outcome(returns: np.ndarray, rules: PropFirmRules) -> bool:
    """True when the path hits the target before any breach or the day cap."""
    equity = 1.0
    peak = 1.0
    n_days = min(returns.size // rules.bars_per_day, rules.max_days)
    for day in range(n_days):
        day_slice = returns[day * rules.bars_per_day : (day + 1) * rules.bars_per_day]
        day_start = equity
        for r in day_slice:
            equity *= 1.0 + r
            peak = max(peak, equity)
            if equity / day_start - 1.0 <= -rules.max_daily_loss:
                return False
            if equity / peak - 1.0 <= -rules.max_total_drawdown:
                return False
            if equity - 1.0 >= rules.profit_target:
                return True
    return False


def prop_firm_pass_probability(
    returns: np.ndarray,
    *,
    rules: PropFirmRules,
    block_length: int,
    n_paths: int = 1000,
    seed: int = 42,
) -> dict[str, float]:
    """P(pass phase 1) and P(pass two consecutive phases) over bootstrap paths.

    Paths are stationary-bootstrap resamples of the strategy's own per-bar net
    returns, long enough for two evaluation windows. Phase 2 is evaluated on
    the continuation of the same path, so the two phases share regime rather
    than being independent draws.
    """
    r = np.asarray(returns, dtype=float)
    horizon = 2 * rules.max_days * rules.bars_per_day
    rng = np.random.default_rng(seed)
    p1 = 0
    p_both = 0
    half = rules.max_days * rules.bars_per_day
    for _ in range(int(n_paths)):
        path = r[_stationary_indices(r.size, horizon, float(block_length), rng)]
        first = _phase_outcome(path[:half], rules)
        p1 += int(first)
        if first:
            p_both += int(_phase_outcome(path[half:], rules))
    n = max(int(n_paths), 1)
    return {
        "pass_phase1": p1 / n,
        "pass_both": p_both / n,
        "n_paths": float(n),
    }


# Published evaluation rules of real crypto-perp prop firms, mapped 2026-08-19.
# Only the three quantitative gates our simulator models are encoded (profit
# target, trailing max drawdown, daily loss). Rules we deliberately do NOT
# model -- consistency caps, mandatory stop-losses, minimum trading days --
# would each make passing HARDER, so the pass probabilities reported against
# these presets are optimistic upper bounds, which is the safe direction for a
# cautionary result. `max_days` is our evaluation horizon, not a firm rule.
PROP_FIRM_PRESETS: dict[str, dict[str, Any]] = {
    "breakout_1step_classic": {
        "rules": PropFirmRules(
            profit_target=0.10,
            max_total_drawdown=0.06,
            max_daily_loss=0.03,
            max_days=60,
            bars_per_day=24,
        ),
        "source": "https://www.kraken.com/learn/breakout-vs-hyrotrader",
        "retrieved": "2026-08-19",
        "notes": "Published target range 9-12% (10% modelled); Classic 6% DD, 3% daily; "
        "no minimum days. Not modelled: none material for this preset.",
    },
    "hyrotrader_2step": {
        "rules": PropFirmRules(
            profit_target=0.10,
            max_total_drawdown=0.06,
            max_daily_loss=0.04,
            max_days=60,
            bars_per_day=24,
        ),
        "source": "https://www.hyrotrader.com/evaluations/",
        "retrieved": "2026-08-19",
        "notes": "10% target per phase, 6% max loss, 4% daily. Not modelled: 40% "
        "consistency cap, 5-minute stop-loss rule, 5 minimum trading days -- "
        "all of which only lower the true pass rate.",
    },
}


def _trade_segments(position: np.ndarray) -> list[tuple[int, int]]:
    """Contiguous nonzero blocks of the position series as (start, end) pairs."""
    segments: list[tuple[int, int]] = []
    in_seg = False
    start = 0
    for i, p_ in enumerate(position):
        if p_ != 0 and not in_seg:
            in_seg, start = True, i
        elif p_ == 0 and in_seg:
            in_seg = False
            segments.append((start, i))
    if in_seg:
        segments.append((start, position.size))
    return segments


def coin_flip_pass_probability(
    ledger: pl.DataFrame,
    *,
    rules: PropFirmRules,
    n_paths: int = 1000,
    seed: int = 42,
) -> dict[str, float]:
    """Pass probability of a coin flip with the strategy's own timing and costs.

    Each path keeps the real ledger's trade timing and sizes (the |position|
    pattern) and flips a fair coin for the DIRECTION of every trade segment,
    re-pricing costs from the flipped turnover at the run's realised cost rate
    and funding from the flipped positions. The evaluation windows start at a
    random day so paths sample the whole history. This is the honest baseline
    the strategy has to beat: same activity, zero information.
    """
    position = ledger["position"].to_numpy().astype(float)
    oo = ledger["oo_return"].to_numpy().astype(float)
    funding_rate = ledger["funding_rate_in_bar"].to_numpy().astype(float)

    turnover_real = np.abs(np.diff(position, prepend=0.0)).sum()
    cost_real = float((ledger["fee"] + ledger["slippage"]).sum())
    cost_per_turnover = (cost_real / turnover_real) if turnover_real > 0 else 0.0

    segments = _trade_segments(position)
    horizon = 2 * rules.max_days * rules.bars_per_day
    half = rules.max_days * rules.bars_per_day
    n = position.size
    if n <= horizon:
        raise ValueError("Ledger shorter than two evaluation windows.")

    rng = np.random.default_rng(seed)
    p1 = 0
    p_both = 0
    for _ in range(int(n_paths)):
        signs = rng.choice([-1.0, 1.0], size=len(segments))
        pos = np.zeros(n)
        for (a, b), sgn in zip(segments, signs, strict=True):
            pos[a:b] = sgn * np.abs(position[a:b])
        net = pos * oo - cost_per_turnover * np.abs(np.diff(pos, prepend=0.0)) + pos * funding_rate
        start = int(rng.integers(0, n - horizon))
        window = net[start : start + horizon]
        first = _phase_outcome(window[:half], rules)
        p1 += int(first)
        if first:
            p_both += int(_phase_outcome(window[half:], rules))
    denom = max(int(n_paths), 1)
    return {"pass_phase1": p1 / denom, "pass_both": p_both / denom, "n_paths": float(denom)}
