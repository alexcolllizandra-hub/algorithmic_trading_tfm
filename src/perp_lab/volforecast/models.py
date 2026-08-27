"""The three frozen models: persistence, HAR-RV (OLS) and a small LSTM.

The LSTM lives behind a lazy torch import so the package (and the classical
models) work without the optional ``dl`` extra. All randomness is seeded
explicitly; training is CPU-deterministic for a fixed seed.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from perp_lab.volforecast.data import VolDataset


# --------------------------------------------------------------------------- #
# Naive persistence
# --------------------------------------------------------------------------- #
def predict_naive(dataset: VolDataset, mask: np.ndarray) -> np.ndarray:
    """Forecast log RV(next 24h) with the trailing 24h log RV (column 0)."""
    return dataset.har_features[mask, 0]


# --------------------------------------------------------------------------- #
# HAR-RV (Corsi 2009), plain OLS on the three log-RV components
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class HarModel:
    coef: np.ndarray  # (4,) intercept + three components


def fit_har(dataset: VolDataset, mask: np.ndarray) -> HarModel:
    x = dataset.har_features[mask]
    y = dataset.target_log_rv[mask]
    design = np.column_stack([np.ones(x.shape[0]), x])
    coef, *_ = np.linalg.lstsq(design, y, rcond=None)
    return HarModel(coef=coef)


def predict_har(model: HarModel, dataset: VolDataset, mask: np.ndarray) -> np.ndarray:
    x = dataset.har_features[mask]
    design = np.column_stack([np.ones(x.shape[0]), x])
    return design @ model.coef


# --------------------------------------------------------------------------- #
# LSTM (optional torch)
# --------------------------------------------------------------------------- #
LSTM_WINDOW = 96
LSTM_HIDDEN = 32
LSTM_MAX_EPOCHS = 40
LSTM_PATIENCE = 5
LSTM_BATCH = 256
LSTM_LR = 1e-3


def _require_torch():
    try:
        import torch
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise ImportError(
            "The LSTM model needs the optional 'dl' extra: uv sync --extra dl"
        ) from exc
    return torch


def _sequences(
    features: np.ndarray, targets: np.ndarray, idx: np.ndarray, window: int
) -> tuple[np.ndarray, np.ndarray]:
    """Stack (window, n_features) input sequences ending at each index."""
    keep = idx[idx >= window - 1]
    seqs = np.stack([features[i - window + 1 : i + 1] for i in keep])
    return seqs.astype(np.float32), targets[keep].astype(np.float32)


def fit_predict_lstm(
    dataset: VolDataset,
    train_mask: np.ndarray,
    val_mask: np.ndarray,
    test_mask: np.ndarray,
    *,
    seed: int,
    window: int = LSTM_WINDOW,
    hidden: int = LSTM_HIDDEN,
    max_epochs: int = LSTM_MAX_EPOCHS,
    patience: int = LSTM_PATIENCE,
) -> np.ndarray:
    """Train on train, early-stop on validation MSE, predict the test rows.

    Inputs are standardised with train-only moments. Returns predictions of
    log RV aligned to ``test_mask``'s True rows (rows whose lookback window
    would cross the dataset start are filled with the naive forecast).
    """
    torch = _require_torch()
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)

    mu = dataset.bar_features[train_mask].mean(axis=0)
    sd = dataset.bar_features[train_mask].std(axis=0) + 1e-9
    feats = (dataset.bar_features - mu) / sd
    y_mu = float(dataset.target_log_rv[train_mask].mean())
    y_sd = float(dataset.target_log_rv[train_mask].std() + 1e-9)
    targets = (dataset.target_log_rv - y_mu) / y_sd

    train_idx = np.where(train_mask)[0]
    val_idx = np.where(val_mask)[0]
    test_idx = np.where(test_mask)[0]
    x_train, y_train = _sequences(feats, targets, train_idx, window)
    x_val, y_val = _sequences(feats, targets, val_idx, window)

    class Net(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.lstm = torch.nn.LSTM(feats.shape[1], hidden, batch_first=True)
            self.head = torch.nn.Linear(hidden, 1)

        def forward(self, x):
            out, _ = self.lstm(x)
            return self.head(out[:, -1]).squeeze(-1)

    net = Net()
    optim = torch.optim.Adam(net.parameters(), lr=LSTM_LR)
    loss_fn = torch.nn.MSELoss()
    xt = torch.from_numpy(x_train)
    yt = torch.from_numpy(y_train)
    xv = torch.from_numpy(x_val)
    yv = torch.from_numpy(y_val)

    best_val = np.inf
    best_state = {k: v.clone() for k, v in net.state_dict().items()}
    bad_epochs = 0
    n = xt.shape[0]
    for _epoch in range(max_epochs):
        net.train()
        order = rng.permutation(n)
        for start in range(0, n, LSTM_BATCH):
            batch = order[start : start + LSTM_BATCH]
            optim.zero_grad()
            loss = loss_fn(net(xt[batch]), yt[batch])
            loss.backward()
            optim.step()
        net.eval()
        with torch.no_grad():
            val_loss = float(loss_fn(net(xv), yv))
        if val_loss < best_val - 1e-5:
            best_val = val_loss
            best_state = {k: v.clone() for k, v in net.state_dict().items()}
            bad_epochs = 0
        else:
            bad_epochs += 1
            if bad_epochs >= patience:
                break
    net.load_state_dict(best_state)

    # Predict the test rows; early rows without a full window fall back to naive.
    predictable = test_idx[test_idx >= window - 1]
    out = predict_naive(dataset, test_mask).copy()
    if predictable.size:
        x_test, _ = _sequences(feats, targets, test_idx, window)
        net.eval()
        with torch.no_grad():
            pred_std = net(torch.from_numpy(x_test)).numpy()
        pred = pred_std * y_sd + y_mu
        position = np.searchsorted(test_idx, predictable)
        out[position] = pred
    return out
