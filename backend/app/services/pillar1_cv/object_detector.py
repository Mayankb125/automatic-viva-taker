"""YOLO object detector for phone/book/laptop proctoring flags."""

from __future__ import annotations


_YOLO_MODEL = None

TARGET_LABEL_TO_FLAG = {
    "cell phone": "phone",
    "book": "book",
    "laptop": "laptop",
}


def load_yolo_model():
    """Load YOLOv8 model once per process."""
    global _YOLO_MODEL
    if _YOLO_MODEL is not None:
        return _YOLO_MODEL

    from ultralytics import YOLO

    _YOLO_MODEL = YOLO("yolov8n.pt")
    return _YOLO_MODEL


def run_yolo_inference(frame, confidence_threshold: float = 0.6):
    """Run YOLO inference and return first result item."""
    model = load_yolo_model()
    results = model.predict(frame, conf=confidence_threshold, verbose=False)
    if not results:
        return None
    return results[0]


def _parse_yolo_labels(yolo_result):
    if yolo_result is None or yolo_result.boxes is None:
        return []

    names = yolo_result.names or {}
    parsed = []
    for box in yolo_result.boxes:
        class_id = int(box.cls[0].item())
        confidence = float(box.conf[0].item())
        label = names.get(class_id, str(class_id))
        parsed.append(
            {
                "label": str(label).lower(),
                "confidence": round(confidence, 3),
            }
        )
    return parsed


def detect_objects(frame, confidence_threshold: float = 0.6, yolo_result=None):
    """Detect prohibited objects and map them to integrity flag types."""
    try:
        result = yolo_result if yolo_result is not None else run_yolo_inference(
            frame,
            confidence_threshold=confidence_threshold,
        )
    except Exception as exc:
        return {
            "available": False,
            "detected_objects": [],
            "is_flagged": False,
            "flag_types": [],
            "error": f"object detector unavailable: {exc}",
        }

    parsed_labels = _parse_yolo_labels(result)
    flagged_types = sorted(
        {
            TARGET_LABEL_TO_FLAG[item["label"]]
            for item in parsed_labels
            if item["label"] in TARGET_LABEL_TO_FLAG
        }
    )

    return {
        "available": True,
        "detected_objects": parsed_labels,
        "is_flagged": len(flagged_types) > 0,
        "flag_types": flagged_types,
    }
