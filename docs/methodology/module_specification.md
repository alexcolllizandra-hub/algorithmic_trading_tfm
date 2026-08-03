# Module Specification (Chapter 5 pipeline) — v0.1

Planned public API for the modelling packages. **None of the 🟡 modules are
implemented yet**; this fixes their contracts so implementation can proceed
incrementally without redesign. Existing ✅ modules are listed for reference.
Type signatures are indicative (Polars frames, tz-aware UTC `open_time`).

## Existing (✅) — reused as-is

- `config/` — `DataContract`, `EdaConfig`, `AppSettings`, loaders. **Add**
  `ExperimentConfig` (Pydantic model over `configs/experiment.yaml`).
- `data/` — `bars.resample_ohlcv`, `splits.split_by_holdout`,
  `splits.resolve_holdout_start`, `manifest`, providers.
- `validation/` — `schemas`, `quality.quality_report`.
- `eda/` — descriptive analysis library (not used for decisions).
- `reporting/` — `save_figure`, `save_table`, house style.
- `utils/` — `timeutils`, `hashing`, `logging`, `seeds`.

## `features/` 🟡 — causal feature engine

Responsibility: turn validated bars + aux streams into **past-only, shifted**
feature frames per the catalogue.

```python
def build_features(bars: pl.DataFrame, *, config: ExperimentConfig,
                   funding: pl.DataFrame | None = None,
                   mark: pl.DataFrame | None = None) -> pl.DataFrame: ...
def assert_causal(frame: pl.DataFrame, feature_cols: list[str]) -> None:  # leakage guard
def as_of_join_past(left, right, *, on="open_time", tolerance) -> pl.DataFrame: ...
```

Guarantees: every feature column shifted ≥ 1 bar; expanding (not full-sample)
regime thresholds; as-of-past joins; deterministic column order.

## `strategies/` 🟡 — representation + baselines

```python
@dataclass(frozen=True)
class StrategyParams: ...          # one point in the shared search space
class Strategy(Protocol):
    def signals(self, feats: pl.DataFrame) -> pl.DataFrame: ...  # side ∈ {-1,0,1}, at close t
def decode(chromosome: np.ndarray) -> StrategyParams: ...        # GA <-> params
def encode(params: StrategyParams) -> np.ndarray: ...
def sample_params(rng) -> StrategyParams: ...                    # RS <-> params
```

Families: `Momentum`, `Breakout`, `MeanReversion` (see
`strategy_specification.md`). Signals are emitted at close *t*; execution lag is
applied by the backtester.

## `labeling/` 🟡 — triple-barrier + meta-labels

```python
def triple_barrier(bars, events, *, upper_atr, lower_atr, vertical_bars,
                   atr) -> pl.DataFrame:   # returns label ∈ {-1,0,1} + touch time
def meta_labels(trades, *, costs) -> pl.DataFrame:  # 1 if base trade profitable net of costs
```

Overlapping events tracked for purging; horizon feeds purge/embargo sizing.

## `backtesting/` 🟡 — cost-aware, next-bar

```python
@dataclass
class CostModel: taker_bps; maker_bps; slippage_bps; funding: str
def backtest(signals, bars, *, cost_model, sizing, risk) -> BacktestResult
class BacktestResult: equity; trades; metrics; exposure
```

Rules: signal@close *t* → fill@open *t+1*; fees + slippage per side; funding
paid/received on open positions (as-of past); leverage/exposure caps; explicit
missing-price handling; no look-ahead.

## `validation/` (walk-forward) 🟡

```python
def expanding_walk_forward(index, *, initial_train, val, test, step,
                           purge_bars, embargo_bars) -> list[Fold]
class Fold: train_idx; val_idx; test_idx   # chronological, purged, embargoed
```

Purge/embargo derived from `max(label_horizon, max_holding)` (not arbitrary).

## `search/` 🟡 — RS and GA (shared harness)

```python
def evaluate(params, *, folds, cost_model, fitness) -> FitnessResult   # one WF backtest
def random_search(space, *, budget, seed, evaluate) -> SearchReport
def genetic_algorithm(space, *, budget, seed, evaluate, ga_cfg) -> SearchReport
```

Both consume the identical `evaluate` harness, folds, costs and budget.

## `models/` 🟡 — meta-labeling

```python
def fit_meta_model(X_train, y_train, *, family, seed) -> Model
def calibrate(model, X_val, y_val, *, method="isotonic") -> CalibratedModel
def tune_threshold(probs_val, y_val, *, objective) -> float   # validation only
```

Families: logistic regression, random forest, LightGBM (optional dep).

## `evaluation/` 🟡 — metrics + robustness

```python
def performance_metrics(result) -> dict           # Sharpe, Sortino, MaxDD, Calmar, ...
def by_asset_fold_regime(results) -> pl.DataFrame
def robustness_battery(candidate, *, scenarios) -> pl.DataFrame
def deflated_sharpe(sharpe, *, n_trials, ...) -> float
```

## `tracking/` 🟡 — experiment provenance

```python
def start_run(config, *, dataset_manifests, code_commit) -> RunContext
def log_artifact(run, path, kind) -> None
def finalize(run, metrics) -> None
```

Lightweight JSON-based now (mirrors the EDA artifact metadata); MLflow deferred
to the platform phase.

## New dependencies (deferred)

Chapter 5 will add, when the corresponding module is implemented:
`scikit-learn` (meta-labeling, calibration), `lightgbm` (optional model),
and possibly a small GA implementation (custom or `deap`). These are **not**
added in this specification task to keep the Phase-1 environment unchanged.
