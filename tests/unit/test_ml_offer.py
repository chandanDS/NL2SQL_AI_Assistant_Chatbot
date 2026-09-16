from data_generator.seed_ml_leads import calculate_aa_based_offer


def test_aa_offer_increases_only_on_positive_six_month_net_inflow():
    assert calculate_aa_based_offer(300_000, 400_000, 350_000) == 400_000
    assert calculate_aa_based_offer(300_000, 350_000, 350_000) == 300_000
    assert calculate_aa_based_offer(300_000, 300_000, 350_000) == 300_000


def test_aa_offer_uplift_is_capped_for_demo():
    assert calculate_aa_based_offer(300_000, 900_000, 200_000) == 500_000
