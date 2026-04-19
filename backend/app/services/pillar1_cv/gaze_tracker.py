"""Gaze direction analysis with MediaPipe primary engine and OpenCV fallback."""

from __future__ import annotations

import time


_FACE_MESH = None
_HAAR_FACE = None
_HAAR_EYE = None
_SESSION_AWAY_STARTED_AT: dict[str, float | None] = {}
_SESSION_NO_EYES_STARTED_AT: dict[str, float | None] = {}
_SESSION_EYE_BASELINE: dict[str, float | None] = {}
_SESSION_EYE_BASELINE_COUNT: dict[str, int] = {}


def _get_face_mesh():
    global _FACE_MESH
    if _FACE_MESH is not None:
        return _FACE_MESH

    import mediapipe as mp

    _FACE_MESH = mp.solutions.face_mesh.FaceMesh(
        static_image_mode=False,
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    return _FACE_MESH


def _get_haar_face_detector():
    global _HAAR_FACE
    if _HAAR_FACE is not None:
        return _HAAR_FACE

    import cv2

    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    detector = cv2.CascadeClassifier(cascade_path)
    if detector.empty():
        raise RuntimeError("OpenCV Haar face detector unavailable")

    _HAAR_FACE = detector
    return _HAAR_FACE


def _get_haar_eye_detector():
    global _HAAR_EYE
    if _HAAR_EYE is not None:
        return _HAAR_EYE

    import cv2

    candidates = [
        cv2.data.haarcascades + "haarcascade_eye_tree_eyeglasses.xml",
        cv2.data.haarcascades + "haarcascade_eye.xml",
    ]
    for cascade_path in candidates:
        detector = cv2.CascadeClassifier(cascade_path)
        if not detector.empty():
            _HAAR_EYE = detector
            return _HAAR_EYE

    raise RuntimeError("OpenCV Haar eye detector unavailable")


def _update_away_state(session_id: str, now: float, is_away: bool) -> float:
    away_started = _SESSION_AWAY_STARTED_AT.get(session_id)

    if not is_away:
        _SESSION_AWAY_STARTED_AT[session_id] = None
        return 0.0

    if away_started is None:
        _SESSION_AWAY_STARTED_AT[session_id] = now
        return 0.0

    return max(0.0, now - away_started)


def _update_no_eyes_state(session_id: str, now: float, active: bool) -> float:
    no_eyes_started = _SESSION_NO_EYES_STARTED_AT.get(session_id)

    if not active:
        _SESSION_NO_EYES_STARTED_AT[session_id] = None
        return 0.0

    if no_eyes_started is None:
        _SESSION_NO_EYES_STARTED_AT[session_id] = now
        return 0.0

    return max(0.0, now - no_eyes_started)


def _get_direction(landmarks, frame_width: int, frame_height: int) -> str:
    left_iris = [468, 469, 470, 471, 472]
    right_iris = [473, 474, 475, 476, 477]

    left_eye_outer = landmarks[33]
    left_eye_inner = landmarks[133]
    left_eye_top = landmarks[159]
    left_eye_bottom = landmarks[145]

    right_eye_outer = landmarks[362]
    right_eye_inner = landmarks[263]
    right_eye_top = landmarks[386]
    right_eye_bottom = landmarks[374]

    left_iris_x = sum(landmarks[i].x for i in left_iris) / len(left_iris)
    left_iris_y = sum(landmarks[i].y for i in left_iris) / len(left_iris)
    right_iris_x = sum(landmarks[i].x for i in right_iris) / len(right_iris)
    right_iris_y = sum(landmarks[i].y for i in right_iris) / len(right_iris)

    left_x_span = max(1e-6, abs(left_eye_inner.x - left_eye_outer.x))
    right_x_span = max(1e-6, abs(right_eye_outer.x - right_eye_inner.x))
    left_y_span = max(1e-6, abs(left_eye_bottom.y - left_eye_top.y))
    right_y_span = max(1e-6, abs(right_eye_bottom.y - right_eye_top.y))

    left_x_ratio = (left_iris_x - min(left_eye_outer.x, left_eye_inner.x)) / left_x_span
    right_x_ratio = (right_iris_x - min(right_eye_inner.x, right_eye_outer.x)) / right_x_span
    left_y_ratio = (left_iris_y - min(left_eye_top.y, left_eye_bottom.y)) / left_y_span
    right_y_ratio = (right_iris_y - min(right_eye_top.y, right_eye_bottom.y)) / right_y_span

    avg_x = (left_x_ratio + right_x_ratio) / 2.0
    avg_y = (left_y_ratio + right_y_ratio) / 2.0

    if avg_x < 0.28:
        return "left"
    if avg_x > 0.72:
        return "right"
    if avg_y < 0.30:
        return "up"
    if avg_y > 0.70:
        return "down"

    _ = (frame_width, frame_height)
    return "center"


def _eye_ratio_from_roi(eye_roi_gray) -> float | None:
    import cv2

    if eye_roi_gray is None or eye_roi_gray.size == 0:
        return None

    h, w = eye_roi_gray.shape[:2]
    if h < 10 or w < 16:
        return None

    proc = cv2.equalizeHist(eye_roi_gray)
    proc = cv2.GaussianBlur(proc, (5, 5), 0)
    top = int(h * 0.20)
    bottom = int(h * 0.85)
    band = proc[top:bottom, :]
    if band.size == 0:
        return None

    _, bin_inv = cv2.threshold(band, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    moments = cv2.moments(bin_inv)
    if moments["m00"] <= 0:
        return None

    cx = float(moments["m10"] / moments["m00"])
    ratio = cx / max(1.0, float(band.shape[1]))
    return max(0.0, min(1.0, ratio))


def _estimate_haar_direction(frame_gray, face_box) -> tuple[str, bool, int, float | None]:
    x, y, w, h = [int(v) for v in face_box]
    frame_h, frame_w = frame_gray.shape[:2]

    # Head-position estimate from face center in the frame.
    center_x_ratio = (float(x) + float(w) / 2.0) / max(1.0, float(frame_w))
    center_y_ratio = (float(y) + float(h) / 2.0) / max(1.0, float(frame_h))

    if center_x_ratio < 0.18:
        head_direction = "left"
    elif center_x_ratio > 0.82:
        head_direction = "right"
    elif center_y_ratio < 0.18:
        head_direction = "up"
    elif center_y_ratio > 0.82:
        head_direction = "down"
    else:
        head_direction = "center"

    # Eye estimate inside face ROI helps detect eyes-away even when head is centered.
    face_roi = frame_gray[max(0, y):min(frame_h, y + h), max(0, x):min(frame_w, x + w)]
    if face_roi.size == 0:
        return head_direction, False, 0, None

    try:
        eye_detector = _get_haar_eye_detector()
        eyes = eye_detector.detectMultiScale(
            face_roi,
            scaleFactor=1.1,
            minNeighbors=4,
            minSize=(16, 16),
        )
    except Exception:
        eyes = []

    eye_ratios: list[float] = []
    for ex, ey, ew, eh in eyes:
        # Ignore detections too low on the face to reduce mouth/cheek false positives.
        if ey > int(h * 0.65):
            continue
        eye_roi = face_roi[ey:ey + eh, ex:ex + ew]
        ratio = _eye_ratio_from_roi(eye_roi)
        if ratio is not None:
            eye_ratios.append(ratio)
        if len(eye_ratios) >= 2:
            break

    eyes_detected = len(eye_ratios)
    if eyes_detected == 0:
        return head_direction, False, 0, None

    eyes_confident = eyes_detected >= 2
    avg_eye_ratio = sum(eye_ratios) / float(eyes_detected)

    return head_direction, eyes_confident, eyes_detected, avg_eye_ratio


def analyze_gaze(
    frame,
    session_id: str,
    timestamp: float | None = None,
    away_seconds_threshold: float = 2.0,
):
    """Analyze gaze direction and flag prolonged away-from-screen behavior."""
    now = timestamp if timestamp is not None else time.time()

    try:
        import cv2
    except Exception as exc:
        return {
            "available": False,
            "gaze_direction": "unavailable",
            "is_flagged": False,
            "flag_type": None,
            "away_duration_seconds": 0.0,
            "error": f"gaze tracker unavailable: {exc}",
        }

    height, width = frame.shape[:2]
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    try:
        face_mesh = _get_face_mesh()
        mesh_result = face_mesh.process(rgb_frame)
    except Exception:
        face_mesh = None
        mesh_result = None

    if mesh_result is not None and mesh_result.multi_face_landmarks:
        face_landmarks = mesh_result.multi_face_landmarks[0].landmark
        direction = _get_direction(face_landmarks, width, height)
        away_duration = _update_away_state(session_id, now, direction != "center")
        is_flagged = away_duration >= away_seconds_threshold
        return {
            "available": True,
            "engine": "mediapipe",
            "gaze_direction": direction,
            "is_flagged": is_flagged,
            "flag_type": "gaze_away" if is_flagged else None,
            "away_duration_seconds": round(away_duration, 2),
        }

    try:
        detector = _get_haar_face_detector()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(50, 50))
    except Exception as exc:
        return {
            "available": False,
            "gaze_direction": "unavailable",
            "is_flagged": False,
            "flag_type": None,
            "away_duration_seconds": 0.0,
            "error": f"gaze tracker unavailable: {exc}",
        }

    if len(faces) == 0:
        direction = "no_face"
        _update_no_eyes_state(session_id, now, False)
        away_duration = _update_away_state(session_id, now, True)
        is_flagged = away_duration >= away_seconds_threshold
    else:
        face_box = max(faces, key=lambda f: int(f[2]) * int(f[3]))
        direction, eyes_confident, eyes_detected, avg_eye_ratio = _estimate_haar_direction(gray, face_box)

        eye_baseline = _SESSION_EYE_BASELINE.get(session_id)
        eye_baseline_count = int(_SESSION_EYE_BASELINE_COUNT.get(session_id, 0) or 0)

        if avg_eye_ratio is not None and eyes_confident:
            if eye_baseline is None:
                eye_baseline = avg_eye_ratio
                eye_baseline_count = 1
            else:
                # Build a stable center baseline from initial confident frames.
                if eye_baseline_count < 15:
                    eye_baseline = (
                        (eye_baseline * eye_baseline_count) + avg_eye_ratio
                    ) / float(eye_baseline_count + 1)
                    eye_baseline_count += 1
                elif abs(avg_eye_ratio - eye_baseline) < 0.18:
                    # After warmup, keep adapting slowly to natural drift.
                    eye_baseline = (0.97 * eye_baseline) + (0.03 * avg_eye_ratio)

            _SESSION_EYE_BASELINE[session_id] = eye_baseline
            _SESSION_EYE_BASELINE_COUNT[session_id] = eye_baseline_count

            baseline_ready = eye_baseline_count >= 8
            if eye_baseline is not None and baseline_ready:
                delta = 0.18
                if avg_eye_ratio < (eye_baseline - delta):
                    direction = "left"
                elif avg_eye_ratio > (eye_baseline + delta):
                    direction = "right"
                elif direction in {"left", "right"}:
                    direction = "center"
            elif direction in {"left", "right"}:
                # Avoid false side-direction during initial baseline warmup.
                direction = "center"

        # Do not trust side direction when eye tracking is low confidence.
        if not eyes_confident and direction in {"left", "right"}:
            direction = "center"

        no_eyes_duration = _update_no_eyes_state(
            session_id,
            now,
            active=(eyes_detected == 0),
        )
        if (eyes_detected == 0) and direction == "center" and no_eyes_duration >= 1.2:
            direction = "no_eyes"

        away_duration = _update_away_state(session_id, now, direction != "center")
        is_flagged = away_duration >= away_seconds_threshold

    payload = {
        "available": True,
        "engine": "haar-eye",
        "gaze_direction": direction,
        "is_flagged": is_flagged,
        "flag_type": "gaze_away" if is_flagged else None,
        "away_duration_seconds": round(away_duration, 2),
    }
    if len(faces) > 0:
        payload["eyes_detected"] = int(eyes_detected)
        payload["eyes_confident"] = bool(eyes_confident)
        payload["avg_eye_ratio"] = round(float(avg_eye_ratio), 3) if avg_eye_ratio is not None else None
        payload["eye_baseline"] = round(float(_SESSION_EYE_BASELINE.get(session_id)), 3) if _SESSION_EYE_BASELINE.get(session_id) is not None else None
        payload["eye_baseline_samples"] = int(_SESSION_EYE_BASELINE_COUNT.get(session_id, 0) or 0)

    return payload
