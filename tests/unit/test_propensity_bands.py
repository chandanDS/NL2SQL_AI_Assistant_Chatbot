import pytest

from data_generator.seed_ml_leads import propensity_band


@pytest.mark.parametrize("score,expected", [
    (0, "LOW"), (59, "LOW"), (60, "MEDIUM"), (74, "MEDIUM"),
    (75, "HIGH"), (90, "HIGH"), (91, "VERY_HIGH"), (100, "VERY_HIGH"),
])
def test_band_boundaries(score, expected):
    assert propensity_band(score) == expected


@pytest.mark.parametrize("score", [-1, 101])
def test_out_of_range_scores_rejected(score):
    with pytest.raises(ValueError):
        propensity_band(score)
