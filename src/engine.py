"""Repair-priority scoring with a plain-language explanation for every score.

The rules are hand-written (there is no trained model behind them), so each
score can be traced back to the inputs. See the README for the formula.
"""
from __future__ import annotations

# Priority categories, from most to least urgent.
CRITICAL = "Critical"
HIGH = "High"
MEDIUM = "Medium"
LOW = "Low (planned)"
CATEGORIES = [CRITICAL, HIGH, MEDIUM, LOW]

# Categories stored by earlier (Russian) versions of the app -> current names.
LEGACY_CATEGORIES = {
    "Критический": CRITICAL,
    "Высокий": HIGH,
    "Средний": MEDIUM,
    "Низкий (Плановый)": LOW,
}


def normalize_category(category: str) -> str:
    return LEGACY_CATEGORIES.get(category, category)


class RoadAnalyzer:
    """Scores road defects and explains the score."""

    def __init__(self):
        # The more dangerous a defect is for vehicles, the higher its weight.
        self.type_weights = {
            "pothole": 1.5,
            "rutting": 1.1,
            "crack": 0.7,
            "faded_marking": 0.4,
        }
        self.type_labels = {
            "pothole": "pothole",
            "crack": "crack",
            "faded_marking": "faded road marking",
            "rutting": "rutting",
        }

    def calculate_priority(self, defect_type: str, size_cm: float, traffic_level: int,
                           is_near_social: bool = False) -> dict:
        """
        defect_type:    pothole, crack, faded_marking or rutting
        size_cm:        size (or depth) of the defect in cm
        traffic_level:  1 = low, 2 = medium, 3 = high
        is_near_social: a school, hospital or similar facility is nearby
        """
        weight = self.type_weights.get(defect_type, 1.0)
        base_score = weight * size_cm

        # Heavy traffic makes defects grow faster and makes them more dangerous.
        traffic_multiplier = 1.0 + (traffic_level - 1) * 0.4
        social_bonus = 15 if is_near_social else 0

        final_score = min(round(base_score * traffic_multiplier + social_bonus, 1), 100)

        return {
            "score": final_score,
            "category": self._get_category(final_score),
            "explanation": self.explain(defect_type, size_cm, traffic_level, is_near_social, final_score),
        }

    @staticmethod
    def _get_category(score: float) -> str:
        if score >= 80:
            return CRITICAL
        if score >= 50:
            return HIGH
        if score >= 25:
            return MEDIUM
        return LOW

    def explain(self, d_type: str, size: float, traffic: int, social: bool, score: float) -> str:
        label = self.type_labels.get(d_type, "defect")
        reasons = []

        if size > 15:
            reasons.append(f"large {label} ({size:.1f} cm)")
        else:
            reasons.append(f"{label} present ({size:.1f} cm)")

        if traffic == 3:
            reasons.append("heavy traffic (high accident risk)")
        elif traffic == 2:
            reasons.append("moderate traffic load")

        if social:
            reasons.append("close to a school or hospital")

        if score > 75 and d_type == "pothole":
            reasons.append("high risk of suspension damage and loss of control")

        return f"Priority {score}/100 is driven by: " + ", ".join(reasons) + "."


if __name__ == "__main__":
    analyzer = RoadAnalyzer()

    # A dangerous pothole on a busy road next to a school
    result = analyzer.calculate_priority("pothole", 20, 3, is_near_social=True)
    print(f"Example 1: {result['category']} - {result['score']}")
    print(f"Explanation: {result['explanation']}\n")

    # A small crack in a quiet residential street
    result = analyzer.calculate_priority("crack", 5, 1)
    print(f"Example 2: {result['category']} - {result['score']}")
    print(f"Explanation: {result['explanation']}")
