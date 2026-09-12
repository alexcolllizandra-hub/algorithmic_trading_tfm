# Chapter 9 evidence: the promotion gate's detection floor (positive control)

Built by `scripts/build_gate_positive_control.py` on top of
`perp_lab.evaluation.gate_control`. Synthetic strategies with a known net
annualised Sharpe (0.0, 0.3, 0.5, 1.0) are written in the exact layout of a
real run and scored by `analyse_run` and `evaluate_r3_promotion` unchanged.

Scaffolds: the Random Search seed runs of `volatility_breakout` (R3) and
`momentum` (R2), ten seeds on each of BTC and ETH. Their bars, positions,
fees, slippage, funding, fold geometry (fifteen folds with the study's purge
and embargo) and trade boundaries are kept; only the per-bar return is
replaced, and only on bars with a position. Innovations: Student-t (4 df),
AR(1) with the scaffold's lag-1 autocorrelation, scaled by the scaffold's
causal EWMA volatility path (half-life 24 bars). Drift on in-position bars is
solved analytically for the target net Sharpe over all bars.

Design: 50 replications per level and scaffold; a replication is one family
(20 seed runs) judged by the six promotion criteria, the minimum-trades veto
and the six-of-ten seed majority on both assets. 8,000 synthetic runs in
total, 2,864 s on 10 worker processes. Master seed 20260912 through
`numpy.random.SeedSequence`; the gate's own bootstrap keeps its fixed seed. No
timestamps are written.

Files: `t_gate_positive_control.csv` / `.md` (promotion rate and criterion
majority rates per level), `t_gate_positive_control_criteria.csv` / `.md`
(per-seed pass rate of every criterion per level and asset),
`t_gate_blocking_criteria.csv` / `.md` (what blocks the replications not
promoted), `gate_positive_control_replications.csv` (one row per replication),
`gate_positive_control.json` (design, scaffold run directories, commit),
`fig_gate_power_curve.png` / `.pdf`.

Not exercised: the search stage. A synthetic strategy of known Sharpe has no
parameters to select; the injected series stands in for the out-of-sample
outcome of the walk-forward selection.
