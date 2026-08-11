from app.metrics import percentile


def test_percentile_basic() -> None:
    assert percentile([100, 200, 300, 400], 50) >= 100


def test_percentile_uses_nearest_rank() -> None:
    values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    assert percentile(values, 50) == 50
    assert percentile(values, 95) == 100
    assert percentile(values, 99) == 100


def test_percentile_handles_small_and_empty_samples() -> None:
    assert percentile([], 95) == 0.0
    assert percentile([7], 99) == 7
    assert percentile([1, 2], 50) == 1
