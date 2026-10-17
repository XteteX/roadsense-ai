import pytest

from src.engine import CRITICAL, HIGH, LOW, MEDIUM, RoadAnalyzer, normalize_category


@pytest.fixture
def analyzer():
    return RoadAnalyzer()


def test_readme_example(analyzer):
    # 1.5 x 30 x 1.4 + 15 = 78.0 -> High
    r = analyzer.calculate_priority("pothole", 30, 2, is_near_social=True)
    assert r["score"] == 78.0 and r["category"] == HIGH
    assert r["explanation"].startswith("Priority 78.0/100")
    assert "close to a school or hospital" in r["explanation"]


def test_score_is_capped_at_100(analyzer):
    assert analyzer.calculate_priority("pothole", 40, 3, True)["score"] == 100
    assert analyzer.calculate_priority("pothole", 40, 3, True)["category"] == CRITICAL


@pytest.mark.parametrize("score,category", [(80, CRITICAL), (79.9, HIGH), (50, HIGH), (25, MEDIUM), (24.9, LOW)])
def test_category_thresholds(score, category):
    assert RoadAnalyzer._get_category(score) == category


def test_more_traffic_never_lowers_priority(analyzer):
    scores = [analyzer.calculate_priority("crack", 20, t)["score"] for t in (1, 2, 3)]
    assert scores == sorted(scores)


def test_legacy_russian_categories():
    assert normalize_category("Критический") == CRITICAL
    assert normalize_category("Низкий (Плановый)") == LOW
    assert normalize_category(HIGH) == HIGH
