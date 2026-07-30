"""Deterministic seeding for reproducibility."""

from __future__ import annotations

import os
import random

import numpy as np


def set_global_seed(seed: int) -> None:
    """Seed Python's ``random``, NumPy and ``PYTHONHASHSEED``.

    Any additional libraries introduced in later phases (e.g. scikit-learn,
    LightGBM, DEAP) must also be seeded from the same value at their call site.
    """
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)
