"""Event labeling for the pre-registered machine-learning layer.

Nothing in this package selects, tunes or promotes a strategy. It provides the
labeling machinery (triple barrier, label spans, purging/embargo and
concurrency-based sample weights) that the meta-labeling stage will consume once
a primary strategy is eligible.
"""

from perp_lab.labeling.triple_barrier import (
    FREE_LABELS,
    LabelCosts,
    LabelSpans,
    TripleBarrierSpec,
    average_uniqueness,
    concurrency,
    label_spans,
    purged_embargoed_mask,
    return_attributed_weights,
    triple_barrier_labels,
)

__all__ = [
    "FREE_LABELS",
    "LabelCosts",
    "LabelSpans",
    "TripleBarrierSpec",
    "average_uniqueness",
    "concurrency",
    "label_spans",
    "purged_embargoed_mask",
    "return_attributed_weights",
    "triple_barrier_labels",
]
