"""RoadSense AI REST API (FastAPI).

Run from the project root:  uvicorn src.main:app --reload
Interactive docs:           http://127.0.0.1:8000/docs
"""
from io import BytesIO
from typing import Literal

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from src.database import get_defect, get_defects, init_db
from src.engine import RoadAnalyzer

app = FastAPI(title="RoadSense AI API", version="1.1.0")
analyzer = RoadAnalyzer()
init_db()
_detector = None  # YOLO model is loaded lazily on the first /detect call


class PriorityRequest(BaseModel):
    type: Literal["pothole", "crack", "faded_marking", "rutting"] = "pothole"
    size_cm: float = Field(gt=0, le=500, description="Size or depth of the defect in cm")
    traffic_level: int = Field(ge=1, le=3, description="1 = low, 2 = medium, 3 = high")
    is_near_social: bool = False


@app.get("/")
def read_root():
    return {"status": "RoadSense AI is online", "version": app.version}


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/defects")
def list_defects(category: str | None = None, limit: int = 100):
    """Reports sorted by priority (highest first), optionally filtered by category."""
    defects = sorted(get_defects(), key=lambda d: d["score"], reverse=True)
    if category:
        defects = [d for d in defects if d["category"] == category]
    return defects[:limit]


@app.get("/defects/{defect_id}")
def read_defect(defect_id: int):
    defect = get_defect(defect_id)
    if defect is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return defect


@app.post("/priority")
def priority(req: PriorityRequest):
    """Score a defect with the rule-based priority engine."""
    return analyzer.calculate_priority(req.type, req.size_cm, req.traffic_level, req.is_near_social)


@app.post("/detect")
async def detect(file: UploadFile = File(...)):
    """Run pothole detection on an uploaded photo (does not save a report)."""
    global _detector
    from PIL import Image

    try:
        image = Image.open(BytesIO(await file.read())).convert("RGB")
    except Exception:  # PIL (or Ultralytics' HEIF patch) could not decode the file
        raise HTTPException(status_code=400, detail="The file is not a valid image")
    if _detector is None:
        from src.detection import RoadDetector

        _detector = RoadDetector()
    result = _detector.detect_and_process(image)
    defect = result["defect"]
    if defect:
        defect = {k: v for k, v in defect.items() if k != "coords"}
    return {"potholes_found": result["count"], "best": defect}
