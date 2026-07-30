from datetime import UTC, datetime
from typing import cast

from perp_lab.data.splits import split_by_holdout, tag_holdout


def test_holdout_partitions_are_disjoint_and_complete(klines_5m):
    holdout_start = datetime(2021, 1, 1, 18, 0, tzinfo=UTC)
    split = split_by_holdout(klines_5m, holdout_start)
    # Disjoint + complete: heights sum to the original.
    assert split.development.height + split.holdout.height == klines_5m.height


def test_development_strictly_before_holdout(klines_5m):
    holdout_start = datetime(2021, 1, 1, 18, 0, tzinfo=UTC)
    split = split_by_holdout(klines_5m, holdout_start)
    assert cast(datetime, split.development["open_time"].max()) < holdout_start
    assert cast(datetime, split.holdout["open_time"].min()) >= holdout_start


def test_no_overlap_of_timestamps(klines_5m):
    holdout_start = datetime(2021, 1, 1, 12, 0, tzinfo=UTC)
    split = split_by_holdout(klines_5m, holdout_start)
    dev_times = set(split.development["open_time"].to_list())
    hold_times = set(split.holdout["open_time"].to_list())
    assert dev_times.isdisjoint(hold_times)


def test_tag_holdout_boolean(klines_5m):
    holdout_start = datetime(2021, 1, 1, 12, 0, tzinfo=UTC)
    tagged = tag_holdout(klines_5m, holdout_start)
    assert cast(datetime, tagged.filter(~tagged["is_holdout"])["open_time"].max()) < holdout_start
