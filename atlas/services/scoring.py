def climate_match(tavg_c, precip_mm):
    """Return a score in [0, 1] for a month given average temperature and precipitation.

    Rule (from design 7.3):
        temp_score   = max(0, 1 - |t - 18| / 15)
        precip_score = max(0, 1 - max(0, p - 80) / 120)
        combined     = (temp_score + precip_score) / 2
    """
    try:
        t = float(tavg_c)
        p = float(precip_mm)
    except (TypeError, ValueError):
        return 0.0
    temp_score = max(0.0, 1 - abs(t - 18.0) / 15.0)
    precip_score = max(0.0, 1 - max(0.0, p - 80.0) / 120.0)
    return (temp_score + precip_score) / 2


def verdict(score):
    if score >= 0.8:
        return "Ideal"
    if score >= 0.5:
        return "Good"
    if score >= 0.25:
        return "Fair"
    return "Poor"
