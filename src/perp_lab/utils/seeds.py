"""Deterministic seeding for reproducibility.

A multi-seed study needs more than one number. Every stochastic component --
each search engine, each asset, each fold's regime fit -- must draw from its own
independent stream, and every stream must be reconstructible from a single
recorded base seed. Reusing one seed for several components couples them for no
reason: two engines started from the same RNG state are not "comparable", they
merely share an arbitrary starting point, and a stream that shifts when an
unrelated component changes its number of draws is not reproducible.
"""

from __future__ import annotations

import hashlib
import os
import random
from dataclasses import dataclass
from typing import Any

import numpy as np

# Upper bound for the derived seeds handed to ``np.random.default_rng`` and to
# any library that expects a 32-bit seed.
_SEED_MODULUS = 2**32


def set_global_seed(seed: int) -> None:
    """Seed Python's ``random``, NumPy and ``PYTHONHASHSEED``.

    Any additional libraries introduced in later phases (e.g. scikit-learn,
    LightGBM, DEAP) must also be seeded from the same value at their call site.
    """
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)


def _label(namespace: str, keys: dict[str, Any]) -> str:
    """Stable textual identity of one stream (order-independent)."""
    parts = "|".join(f"{k}={keys[k]}" for k in sorted(keys))
    return f"{namespace}|{parts}"


@dataclass(frozen=True)
class SeedScheduler:
    """Derives independent, reproducible RNG streams from one base seed.

    Streams are addressed by a namespace plus arbitrary keyword keys, e.g.
    ``stream("engine", symbol="BTCUSDT", seed=7, engine="random_search")``. The
    derivation is a pure function of the base seed and the key set, so:

    * a stream never moves when an unrelated component is added or reordered;
    * the same key set always yields the same seed, on any machine;
    * different key sets yield streams with no exploitable relationship, because
      the key is hashed into ``SeedSequence``'s spawn key rather than being added
      to the seed (``base + 1`` and ``base + 2`` are adjacent, not independent).

    The base seed is the only value that needs to be recorded to reproduce an
    entire multi-seed experiment.
    """

    base_seed: int

    def _sequence(self, namespace: str, keys: dict[str, Any]) -> np.random.SeedSequence:
        digest = hashlib.blake2b(_label(namespace, keys).encode("utf-8"), digest_size=16).digest()
        spawn_key = (
            int.from_bytes(digest[:8], "big"),
            int.from_bytes(digest[8:], "big"),
        )
        return np.random.SeedSequence(entropy=self.base_seed, spawn_key=spawn_key)

    def stream(self, namespace: str, **keys: Any) -> int:
        """A deterministic 32-bit seed for the stream identified by the keys."""
        state = self._sequence(namespace, keys).generate_state(1, dtype=np.uint32)
        return int(state[0]) % _SEED_MODULUS

    def generator(self, namespace: str, **keys: Any) -> np.random.Generator:
        """A NumPy generator for the stream identified by the keys."""
        return np.random.default_rng(self._sequence(namespace, keys))

    def describe(self, namespace: str, **keys: Any) -> dict[str, Any]:
        """Serialisable record of one derived stream, for the run manifest."""
        return {
            "base_seed": self.base_seed,
            "namespace": namespace,
            "keys": {k: keys[k] for k in sorted(keys)},
            "derived_seed": self.stream(namespace, **keys),
        }
