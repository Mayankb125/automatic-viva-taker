"""Utilities for decoding base64 webcam frames into OpenCV images."""

import base64
import binascii


def decode_frame_base64(frame_b64: str):
    """Decode a data URL or raw base64 image payload to a BGR ndarray."""
    if not frame_b64 or not frame_b64.strip():
        raise ValueError("frame is empty")

    payload = frame_b64.strip()
    if payload.startswith("data:"):
        _, separator, encoded_data = payload.partition(",")
        if not separator or not encoded_data:
            raise ValueError("frame data URL is malformed")
        payload = encoded_data

    try:
        image_bytes = base64.b64decode(payload, validate=True)
    except binascii.Error as exc:
        raise ValueError("frame is not valid base64") from exc

    if not image_bytes:
        raise ValueError("decoded frame is empty")

    try:
        import cv2
        import numpy as np
    except Exception as exc:
        raise RuntimeError("OpenCV/Numpy not available for CV decoding") from exc

    np_arr = np.frombuffer(image_bytes, dtype=np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError("could not decode image bytes to frame")

    return frame
