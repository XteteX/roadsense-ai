"""Import data/defects.json into SQLite, scoring each defect with the priority engine.

Run from the project root:  python -m src.migrate
"""
import json
from pathlib import Path

from src.database import add_defect, init_db
from src.engine import RoadAnalyzer

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "defects.json"


def migrate() -> int:
    init_db()
    analyzer = RoadAnalyzer()
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    for d in data:
        analysis = analyzer.calculate_priority(
            d["type"], d["size_cm"], d["traffic_level"], d.get("is_near_social", False)
        )
        add_defect({**d, "is_near_social": d.get("is_near_social", False), **analysis})
    print(f"Imported {len(data)} defects from JSON into SQLite.")
    return len(data)


if __name__ == "__main__":
    migrate()
