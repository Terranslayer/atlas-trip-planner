from atlas.services.scoring import climate_match, verdict


def test_ideal_when_temp_18_precip_80():
    score = climate_match(tavg_c=18.0, precip_mm=80.0)
    assert score >= 0.99


def test_zero_score_for_extremes():
    assert climate_match(tavg_c=-20.0, precip_mm=500.0) <= 0.05


def test_temp_score_monotonic_away_from_18():
    assert climate_match(15.0, 80) > climate_match(5.0, 80)
    assert climate_match(21.0, 80) > climate_match(30.0, 80)


def test_verdict_thresholds():
    assert verdict(0.9) == "Ideal"
    assert verdict(0.6) == "Good"
    assert verdict(0.3) == "Fair"
    assert verdict(0.1) == "Poor"
