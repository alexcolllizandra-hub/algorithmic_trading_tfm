"""Tests for deterministic multi-stream seeding.

A multi-seed study is only reproducible if every stream is a pure function of the
recorded base seed and its own identity, and only honest if distinct streams are
genuinely independent rather than adjacent integers.
"""

from __future__ import annotations

import numpy as np

from perp_lab.utils.seeds import SeedScheduler


def test_same_keys_always_give_the_same_seed() -> None:
    a = SeedScheduler(42).stream("engine", symbol="BTCUSDT", engine="random_search")
    b = SeedScheduler(42).stream("engine", symbol="BTCUSDT", engine="random_search")
    assert a == b


def test_key_order_does_not_matter() -> None:
    s = SeedScheduler(42)
    assert s.stream("engine", symbol="BTCUSDT", engine="ga") == s.stream(
        "engine", engine="ga", symbol="BTCUSDT"
    )


def test_different_engines_get_different_streams() -> None:
    s = SeedScheduler(42)
    rs = s.stream("engine", symbol="BTCUSDT", engine="random_search")
    ga = s.stream("engine", symbol="BTCUSDT", engine="genetic_algorithm")
    assert rs != ga


def test_different_assets_folds_and_base_seeds_all_separate_streams() -> None:
    s = SeedScheduler(42)
    assert s.stream("regime", symbol="BTCUSDT", fold=0) != s.stream(
        "regime", symbol="ETHUSDT", fold=0
    )
    assert s.stream("regime", symbol="BTCUSDT", fold=0) != s.stream(
        "regime", symbol="BTCUSDT", fold=1
    )
    assert SeedScheduler(1).stream("regime", symbol="BTCUSDT", fold=0) != SeedScheduler(2).stream(
        "regime", symbol="BTCUSDT", fold=0
    )


def test_adjacent_base_seeds_do_not_produce_adjacent_streams() -> None:
    """Naive `base + i` seeding correlates streams; hashing into the spawn key must not."""
    seeds = [SeedScheduler(b).stream("engine", engine="rs") for b in range(20)]
    diffs = np.diff(sorted(seeds))
    assert len(set(seeds)) == len(seeds)
    assert not np.all(diffs == diffs[0])


def test_streams_are_far_apart_across_many_keys() -> None:
    """A large key set must not collide, or two components would share randomness."""
    s = SeedScheduler(7)
    generated = {
        s.stream("engine", symbol=sym, seed=i, engine=eng)
        for sym in ("BTCUSDT", "ETHUSDT")
        for i in range(10)
        for eng in ("random_search", "genetic_algorithm")
    }
    assert len(generated) == 2 * 10 * 2


def test_generator_is_deterministic_and_stream_specific() -> None:
    s = SeedScheduler(3)
    a = s.generator("engine", engine="rs").normal(size=5)
    b = s.generator("engine", engine="rs").normal(size=5)
    c = s.generator("engine", engine="ga").normal(size=5)
    assert np.array_equal(a, b)
    assert not np.array_equal(a, c)


def test_describe_records_everything_needed_to_reproduce() -> None:
    record = SeedScheduler(42).describe("engine", symbol="BTCUSDT", engine="rs")
    assert record["base_seed"] == 42
    assert record["keys"] == {"engine": "rs", "symbol": "BTCUSDT"}
    assert record["derived_seed"] == SeedScheduler(42).stream(
        "engine", symbol="BTCUSDT", engine="rs"
    )


def test_derived_seeds_fit_in_32_bits() -> None:
    """Downstream libraries and np.random.default_rng expect a 32-bit seed."""
    s = SeedScheduler(999)
    for i in range(50):
        value = s.stream("x", i=i)
        assert 0 <= value < 2**32
