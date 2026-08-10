"""Typed, mixed-type parameter-space system shared by every search algorithm.

A :class:`SearchSpace` describes one strategy family's tunable parameters as an
ordered tuple of typed :class:`Param` objects, plus family-specific *repair*,
*validation* and *build* callables. Both Random Search and the Genetic Algorithm
construct and manipulate candidates **only** through this representation, so they
share identical spaces, sampling, validation and canonical hashing.

Supported parameter types:

* :class:`IntParam` -- integer values on a discrete grid ``[low, high]`` (step);
* :class:`FloatParam` -- continuous floats, optionally log-scaled;
* :class:`CategoricalParam` -- an ordered tuple of discrete choices (values may
  themselves be tuples, e.g. a regime gate);
* :class:`BoolParam` -- ``True`` / ``False``.

Conditional parameters are expressed with ``active_when=(other_name, value)``:
the parameter is only *active* (sampled into the candidate, hashed, built and
mutated meaningfully) when ``other_name`` currently equals ``value``. Inactive
parameters never affect a candidate's identity, so two candidates that differ
only in an inactive parameter share the same canonical hash.

Everything here is deterministic given a NumPy ``Generator``; nothing samples
from global RNG state.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np

Activation = tuple[str, object] | None
ParamValue = object


def _jsonable(value: ParamValue) -> Any:
    """Convert a parameter value into a stable JSON-serialisable form."""
    if isinstance(value, tuple):
        return [_jsonable(v) for v in value]
    if isinstance(value, bool | int | str) or value is None:
        return value
    if isinstance(value, float):
        # Round to keep canonical hashes stable across trivial float noise.
        return round(value, 10)
    return str(value)


class Param(ABC):
    """One typed, named search dimension."""

    name: str
    active_when: Activation

    @abstractmethod
    def sample(self, rng: np.random.Generator) -> ParamValue: ...

    @abstractmethod
    def is_valid(self, value: ParamValue) -> bool: ...

    @abstractmethod
    def repair(self, value: ParamValue) -> ParamValue:
        """Coerce ``value`` to the nearest valid value (deterministic)."""

    @abstractmethod
    def mutate(self, value: ParamValue, rng: np.random.Generator) -> ParamValue: ...

    def jsonable(self, value: ParamValue) -> Any:
        return _jsonable(value)

    @abstractmethod
    def describe(self) -> dict[str, Any]: ...


@dataclass(frozen=True)
class IntParam(Param):
    name: str
    low: int
    high: int
    step: int = 1
    active_when: Activation = None

    def __post_init__(self) -> None:
        if self.low > self.high:
            raise ValueError(f"IntParam {self.name}: low > high.")
        if self.step <= 0:
            raise ValueError(f"IntParam {self.name}: step must be positive.")

    def _grid(self) -> list[int]:
        return list(range(self.low, self.high + 1, self.step))

    def sample(self, rng: np.random.Generator) -> ParamValue:
        grid = self._grid()
        return int(grid[int(rng.integers(0, len(grid)))])

    def is_valid(self, value: ParamValue) -> bool:
        return (
            isinstance(value, int)
            and not isinstance(value, bool)
            and self.low <= value <= self.high
            and (value - self.low) % self.step == 0
        )

    def repair(self, value: ParamValue) -> int:
        v = int(value) if isinstance(value, int | float) else self.low
        v = min(max(v, self.low), self.high)
        offset = round((v - self.low) / self.step) * self.step
        return int(min(self.low + offset, self.high))

    def mutate(self, value: ParamValue, rng: np.random.Generator) -> ParamValue:
        grid = self._grid()
        if len(grid) == 1:
            return grid[0]
        cur = self.repair(value)
        idx = grid.index(cur) if cur in grid else 0
        # Creep to an adjacent grid point (deterministic given rng).
        delta = int(rng.integers(1, min(3, len(grid))))
        sign = 1 if rng.random() < 0.5 else -1
        new_idx = min(max(idx + sign * delta, 0), len(grid) - 1)
        return int(grid[new_idx])

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": "int",
            "low": self.low,
            "high": self.high,
            "step": self.step,
            "active_when": list(self.active_when) if self.active_when else None,
        }


@dataclass(frozen=True)
class FloatParam(Param):
    name: str
    low: float
    high: float
    log: bool = False
    active_when: Activation = None

    def __post_init__(self) -> None:
        if self.low > self.high:
            raise ValueError(f"FloatParam {self.name}: low > high.")
        if self.log and self.low <= 0:
            raise ValueError(f"FloatParam {self.name}: log scale needs low > 0.")

    def sample(self, rng: np.random.Generator) -> ParamValue:
        if self.log:
            lo, hi = math.log(self.low), math.log(self.high)
            return float(math.exp(rng.uniform(lo, hi)))
        return float(rng.uniform(self.low, self.high))

    def is_valid(self, value: ParamValue) -> bool:
        return (
            isinstance(value, int | float)
            and not isinstance(value, bool)
            and math.isfinite(value)
            and self.low <= value <= self.high
        )

    def repair(self, value: ParamValue) -> float:
        v = float(value) if isinstance(value, int | float) else self.low
        if not math.isfinite(v):
            v = self.low
        return float(min(max(v, self.low), self.high))

    def mutate(self, value: ParamValue, rng: np.random.Generator) -> ParamValue:
        cur = self.repair(value)
        if self.log:
            lo, hi = math.log(self.low), math.log(self.high)
            scale = 0.1 * (hi - lo)
            new = math.exp(min(max(math.log(cur) + rng.normal(0.0, scale), lo), hi))
        else:
            scale = 0.1 * (self.high - self.low)
            new = min(max(cur + rng.normal(0.0, scale), self.low), self.high)
        return float(new)

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": "float",
            "low": self.low,
            "high": self.high,
            "log": self.log,
            "active_when": list(self.active_when) if self.active_when else None,
        }


@dataclass(frozen=True)
class CategoricalParam(Param):
    name: str
    choices: tuple[ParamValue, ...]
    active_when: Activation = None

    def __post_init__(self) -> None:
        if not self.choices:
            raise ValueError(f"CategoricalParam {self.name}: needs >= 1 choice.")

    def sample(self, rng: np.random.Generator) -> ParamValue:
        return self.choices[int(rng.integers(0, len(self.choices)))]

    def is_valid(self, value: ParamValue) -> bool:
        return value in self.choices

    def repair(self, value: ParamValue) -> ParamValue:
        return value if value in self.choices else self.choices[0]

    def mutate(self, value: ParamValue, rng: np.random.Generator) -> ParamValue:
        if len(self.choices) == 1:
            return self.choices[0]
        cur = self.repair(value)
        others = [c for c in self.choices if c != cur]
        return others[int(rng.integers(0, len(others)))]

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": "categorical",
            "choices": [_jsonable(c) for c in self.choices],
            "active_when": list(self.active_when) if self.active_when else None,
        }


@dataclass(frozen=True)
class BoolParam(Param):
    name: str
    active_when: Activation = None

    def sample(self, rng: np.random.Generator) -> ParamValue:
        return bool(rng.random() < 0.5)

    def is_valid(self, value: ParamValue) -> bool:
        return isinstance(value, bool)

    def repair(self, value: ParamValue) -> bool:
        return bool(value)

    def mutate(self, value: ParamValue, rng: np.random.Generator) -> ParamValue:
        return not bool(value)

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": "bool",
            "active_when": list(self.active_when) if self.active_when else None,
        }


BuildFn = Callable[[Mapping[str, ParamValue]], object]
RepairFn = Callable[[dict[str, ParamValue]], dict[str, ParamValue]]
ValidateFn = Callable[[Mapping[str, ParamValue]], tuple[bool, str | None]]


@dataclass(frozen=True)
class SearchSpace:
    """A strategy family's parameter space plus its build/repair/validate hooks."""

    family: str
    version: str
    params: tuple[Param, ...]
    build_fn: BuildFn
    repair_fn: RepairFn
    validate_fn: ValidateFn
    feature_items: tuple[Any, ...] = field(default_factory=tuple)

    def param_names(self) -> tuple[str, ...]:
        return tuple(p.name for p in self.params)

    def _is_active(self, param: Param, values: Mapping[str, ParamValue]) -> bool:
        if param.active_when is None:
            return True
        dep_name, dep_value = param.active_when
        return values.get(dep_name) == dep_value

    def active_params(self, values: Mapping[str, ParamValue]) -> dict[str, ParamValue]:
        """Only the parameters that are currently active (conditionals resolved)."""
        return {p.name: values[p.name] for p in self.params if self._is_active(p, values)}

    def sample(self, rng: np.random.Generator) -> dict[str, ParamValue]:
        values: dict[str, ParamValue] = {}
        for p in self.params:
            values[p.name] = p.sample(rng)
        return self.repair(values)

    def repair(self, values: dict[str, ParamValue]) -> dict[str, ParamValue]:
        """Per-parameter repair, then family-level repair (e.g. fast < slow)."""
        repaired: dict[str, ParamValue] = {}
        by_name = {p.name: p for p in self.params}
        for name, value in values.items():
            param = by_name.get(name)
            repaired[name] = param.repair(value) if param is not None else value
        return self.repair_fn(repaired)

    def is_valid(self, values: Mapping[str, ParamValue]) -> tuple[bool, str | None]:
        for p in self.params:
            if not self._is_active(p, values):
                continue
            if p.name not in values:
                return False, f"missing parameter {p.name!r}"
            if not p.is_valid(values[p.name]):
                return False, f"parameter {p.name!r} has invalid value {values[p.name]!r}"
        return self.validate_fn(values)

    def canonical(self, values: Mapping[str, ParamValue]) -> str:
        """Deterministic JSON of the *active* parameters (stable key order)."""
        active = self.active_params(values)
        payload = {k: _jsonable(v) for k, v in active.items()}
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    def candidate_hash(self, values: Mapping[str, ParamValue]) -> str:
        digest = hashlib.sha1(f"{self.family}|{self.version}|{self.canonical(values)}".encode())
        return f"{self.family}-{digest.hexdigest()[:16]}"

    def finite_cardinality(self, *, max_raw_combinations: int = 1_000_000) -> int | None:
        """Exact number of unique valid candidate identities, when finite.

        Conditional parameters, family repair and inactive values make a raw
        Cartesian product an over-count. Enumeration therefore passes every raw
        tuple through the same repair, validation and canonical-hash path used by
        the engines. ``None`` means the space contains a continuous parameter or
        is too large to enumerate safely.
        """
        grids: list[tuple[ParamValue, ...]] = []
        raw_size = 1
        for param in self.params:
            if isinstance(param, BoolParam):
                grid: tuple[ParamValue, ...] = (False, True)
            elif isinstance(param, CategoricalParam):
                grid = param.choices
            elif isinstance(param, IntParam):
                grid = tuple(param._grid())
            else:
                # FloatParam is continuous; future parameter classes are unknown.
                return None
            raw_size *= len(grid)
            if raw_size > max_raw_combinations:
                return None
            grids.append(grid)

        identities: set[str] = set()
        for combination in itertools.product(*grids):
            raw = {param.name: value for param, value in zip(self.params, combination, strict=True)}
            repaired = self.repair(raw)
            valid, _ = self.is_valid(repaired)
            if valid:
                identities.add(self.candidate_hash(repaired))
        return len(identities)

    def build(self, values: Mapping[str, ParamValue]) -> object:
        return self.build_fn(self.active_params(values))

    def describe(self) -> dict[str, Any]:
        return {
            "family": self.family,
            "version": self.version,
            "params": [p.describe() for p in self.params],
        }


def param_distance(
    space: SearchSpace, a: Mapping[str, ParamValue], b: Mapping[str, ParamValue]
) -> float:
    """Normalised mean per-parameter distance in ``[0, 1]`` (for GA diversity)."""
    names = space.param_names()
    if not names:
        return 0.0
    by_name = {p.name: p for p in space.params}
    total = 0.0
    for name in names:
        param = by_name[name]
        va, vb = a.get(name), b.get(name)
        if (
            isinstance(param, IntParam | FloatParam)
            and isinstance(va, int | float)
            and isinstance(vb, int | float)
        ):
            span = float(param.high - param.low) or 1.0
            total += min(abs(float(va) - float(vb)) / span, 1.0)
        else:
            total += 0.0 if va == vb else 1.0
    return total / len(names)


def population_diversity(
    space: SearchSpace, populations: Sequence[Mapping[str, ParamValue]]
) -> float:
    """Mean pairwise normalised parameter distance across a population."""
    n = len(populations)
    if n < 2:
        return 0.0
    acc = 0.0
    pairs = 0
    for i in range(n):
        for j in range(i + 1, n):
            acc += param_distance(space, populations[i], populations[j])
            pairs += 1
    return acc / pairs if pairs else 0.0
