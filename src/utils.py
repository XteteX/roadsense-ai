"""Generate synthetic demo defects for Almaty (used to pre-fill the dashboard)."""
import json
import random
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "defects.json"

# Approximate bounding box of central Almaty
LAT_RANGE = (43.2000, 43.2700)
LON_RANGE = (76.8500, 76.9500)


def generate_almaty_defects(count: int = 50, seed: int | None = None) -> list[dict]:
    rng = random.Random(seed)
    defects = [
        {
            "id": i,
            "type": rng.choice(["pothole", "crack", "faded_marking", "rutting"]),
            "lat": round(rng.uniform(*LAT_RANGE), 6),
            "lon": round(rng.uniform(*LON_RANGE), 6),
            "size_cm": round(rng.uniform(5.0, 40.0), 1),
            "traffic_level": rng.choice([1, 2, 3]),          # 1 = low, 3 = high
            "is_near_social": rng.choice([True, False, False]),  # ~33% near a school/hospital
            "detected_at": "2026-03-28T15:00:00Z",
        }
        for i in range(1, count + 1)
    ]
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(defects, ensure_ascii=False, indent=4), encoding="utf-8")
    print(f"Generated {count} synthetic defects in {DATA_PATH.relative_to(DATA_PATH.parents[1])}")
    return defects


if __name__ == "__main__":
    generate_almaty_defects()
