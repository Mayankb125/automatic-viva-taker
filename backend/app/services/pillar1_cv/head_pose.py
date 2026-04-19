"""Head pose analysis using MediaPipe landmarks and PnP geometry."""

from __future__ import annotations

import time


_FACE_MESH = None
_SESSION_TURN_STARTED_AT: dict[str, float | None] = {}


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


def _extract_pose_angles(landmarks, width: int, height: int):
    import cv2
    import numpy as np

    image_points = np.array(
        [
            (landmarks[1].x * width, landmarks[1].y * height),
            (landmarks[152].x * width, landmarks[152].y * height),
            (landmarks[33].x * width, landmarks[33].y * height),
            (landmarks[263].x * width, landmarks[263].y * height),
            (landmarks[61].x * width, landmarks[61].y * height),
            (landmarks[291].x * width, landmarks[291].y * height),
        ],
        dtype=np.float64,
    )

    model_points = np.array(
        [
            (0.0, 0.0, 0.0),
            (0.0, -330.0, -65.0),
            (-225.0, 170.0, -135.0),
            (225.0, 170.0, -135.0),
            (-150.0, -150.0, -125.0),
            (150.0, -150.0, -125.0),
        ],
        dtype=np.float64,
    )

    focal_length = float(width)
    center = (width / 2.0, height / 2.0)
    camera_matrix = np.array(
        [
            [focal_length, 0.0, center[0]],
            [0.0, focal_length, center[1]],
            [0.0, 0.0, 1.0],
        ],
        dtype=np.float64,
    )
    dist_coeffs = np.zeros((4, 1), dtype=np.float64)

    success, rotation_vector, translation_vector = cv2.solvePnP(
        model_points,
        image_points,
        camera_matrix,
        dist_coeffs,
        flags=cv2.SOLVEPNP_ITERATIVE,
    )
    if not success:
        raise RuntimeError("solvePnP failed")

    rotation_matrix, _ = cv2.Rodrigues(rotation_vector)
    projection_matrix = np.hstack((rotation_matrix, translation_vector))
    _, _, _, _, _, _, euler_angles = cv2.decomposeProjectionMatrix(projection_matrix)

    pitch = float(euler_angles[0])
    yaw = float(euler_angles[1])
    roll = float(euler_angles[2])
    return yaw, pitch, roll


def analyze_head_pose(
    frame,
    session_id: str,
    timestamp: float | None = None,
    yaw_threshold: float = 30.0,
    turned_seconds_threshold: float = 2.0,
):
    """Analyze head pose and flag prolonged left/right head turning."""
    now = timestamp if timestamp is not None else time.time()

    try:
        import cv2

        face_mesh = _get_face_mesh()
    except Exception as exc:
        return {
            "available": False,
            "yaw": 0.0,
            "pitch": 0.0,
            "roll": 0.0,
            "is_flagged": False,
            "flag_type": None,
            "turned_duration_seconds": 0.0,
            "error": f"head pose unavailable: {exc}",
        }

    height, width = frame.shape[:2]
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = face_mesh.process(rgb_frame)

    if not result.multi_face_landmarks:
        _SESSION_TURN_STARTED_AT[session_id] = None
        return {
            "available": True,
            "yaw": 0.0,
            "pitch": 0.0,
            "roll": 0.0,
            "is_flagged": False,
            "flag_type": None,
            "turned_duration_seconds": 0.0,
        }

    try:
        landmarks = result.multi_face_landmarks[0].landmark
        yaw, pitch, roll = _extract_pose_angles(landmarks, width, height)
    except Exception as exc:
        return {
            "available": False,
            "yaw": 0.0,
            "pitch": 0.0,
            "roll": 0.0,
            "is_flagged": False,
            "flag_type": None,
            "turned_duration_seconds": 0.0,
            "error": f"head pose solve failed: {exc}",
        }

    turned = abs(yaw) > yaw_threshold
    turned_started = _SESSION_TURN_STARTED_AT.get(session_id)

    if not turned:
        _SESSION_TURN_STARTED_AT[session_id] = None
        turned_duration = 0.0
        is_flagged = False
    else:
        if turned_started is None:
            turned_started = now
            _SESSION_TURN_STARTED_AT[session_id] = turned_started
        turned_duration = max(0.0, now - turned_started)
        is_flagged = turned_duration >= turned_seconds_threshold

    return {
        "available": True,
        "yaw": round(yaw, 2),
        "pitch": round(pitch, 2),
        "roll": round(roll, 2),
        "is_flagged": is_flagged,
        "flag_type": "head_turned" if is_flagged else None,
        "turned_duration_seconds": round(turned_duration, 2),
    }
