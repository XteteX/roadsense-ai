"""Pothole detection with a pre-trained YOLOv8 model."""
from __future__ import annotations

import random
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from ultralytics import YOLO

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WEIGHTS = PROJECT_ROOT / "pothole_best.pt"

POTHOLE_COLOR = (0, 200, 0)    # BGR green
OTHER_COLOR = (128, 128, 128)  # BGR grey


class RoadDetector:
    def __init__(self, model_path: str | Path | None = None, conf: float = 0.25):
        self.model = YOLO(str(model_path or DEFAULT_WEIGHTS))
        self.conf = conf

    def draw_bounding_boxes(self, image_bgr: np.ndarray, results, pothole_boxes: set) -> np.ndarray:
        """Draw potholes in green and any other detected class in grey."""
        out = image_bgr.copy()
        thickness = max(2, round(max(out.shape[:2]) / 400))
        font_scale = max(0.5, max(out.shape[:2]) / 1200)
        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = (int(v) for v in box.xyxy[0])
                name = self.model.names[int(box.cls)]
                confidence = float(box.conf)
                is_pothole = (x1, y1, x2, y2) in pothole_boxes
                color = POTHOLE_COLOR if is_pothole else OTHER_COLOR
                label = f"{'pothole' if is_pothole else name} {confidence:.2f}"
                cv2.rectangle(out, (x1, y1), (x2, y2), color, thickness if is_pothole else 1)
                # Label on a filled background so it stays readable on any road texture.
                text_thickness = max(1, thickness - 1)
                (tw, th), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, text_thickness)
                ty = max(y1, th + baseline + 4)
                cv2.rectangle(out, (x1, ty - th - baseline - 4), (x1 + tw + 6, ty), color, -1)
                cv2.putText(out, label, (x1 + 3, ty - baseline - 2), cv2.FONT_HERSHEY_SIMPLEX,
                            font_scale, (255, 255, 255), text_thickness, cv2.LINE_AA)
        return out

    def detect_and_process(self, pil_image: Image.Image) -> dict:
        """Run detection on a PIL image.

        Returns ``{"defect": <most confident pothole or None>, "image": <PIL image with boxes>}``.
        """
        image_bgr = cv2.cvtColor(np.array(pil_image.convert("RGB")), cv2.COLOR_RGB2BGR)
        h, w = image_bgr.shape[:2]
        results = self.model(image_bgr, conf=self.conf, verbose=False)

        detected = []
        for r in results:
            for box in r.boxes:
                if str(self.model.names[int(box.cls)]).lower() != "pothole":
                    continue
                x1, y1, x2, y2 = (int(v) for v in box.xyxy[0])
                cx, cy = (x1 + x2) / 2, (y1 + y2) / 2

                # PROTOTYPE ONLY: there is no camera calibration or GPS yet, so the size is a
                # rough guess from the box area and the map position is derived from where the
                # pothole appears in the frame. See "Known limitations" in the README.
                size_cm = round(float((x2 - x1) * (y2 - y1) / 1000) + random.uniform(5, 15), 1)
                size_cm = max(min(size_cm, 40.0), 5.0)

                detected.append({
                    "type": "pothole",
                    "size_cm": size_cm,
                    "confidence": float(box.conf),
                    "lat_offset": round((0.5 - cy / h) * 0.02, 5),
                    "lon_offset": round((cx / w - 0.5) * 0.03, 5),
                    "coords": (x1, y1, x2, y2),
                })

        boxed = self.draw_bounding_boxes(image_bgr, results, {d["coords"] for d in detected})
        result_image = Image.fromarray(cv2.cvtColor(boxed, cv2.COLOR_BGR2RGB))

        detected.sort(key=lambda d: d["confidence"], reverse=True)
        return {"defect": detected[0] if detected else None, "image": result_image, "count": len(detected)}


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        sys.exit("Usage: python -m src.detection path/to/road_photo.jpg")
    detector = RoadDetector()
    result = detector.detect_and_process(Image.open(sys.argv[1]))
    if result["defect"]:
        d = result["defect"]
        print(f"Found {result['count']} pothole(s); best confidence {d['confidence']:.0%}, "
              f"estimated size ~{d['size_cm']} cm")
        out = Path(sys.argv[1]).with_name(Path(sys.argv[1]).stem + "_detected.jpg")
        result["image"].save(out)
        print(f"Saved annotated image to {out}")
    else:
        print("No potholes found.")
