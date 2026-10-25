"""Stable adapter to the unchanged SatQuery RGB detector."""
import base64
import io
import numpy as np
from PIL import Image
from backend.tools.cloud_detector import (detect_clouds_from_array, BRIGHTNESS_THRESHOLD,
    WHITENESS_THRESHOLD, MORPH_OPEN_RADIUS, MORPH_CLOSE_RADIUS)
from .metrics import validate_mask

PARAMETERS = dict(algorithm="rgb_cloud_detector_v1", brightness_threshold=BRIGHTNESS_THRESHOLD,
    whiteness_threshold=WHITENESS_THRESHOLD, opening_radius=MORPH_OPEN_RADIUS, closing_radius=MORPH_CLOSE_RADIUS)

def detect(image):
    if image.dtype != np.uint8 or image.ndim != 3 or image.shape[2] != 3:
        raise ValueError("Detector input must be HxWx3 uint8 RGB")
    result = detect_clouds_from_array(image)
    mask = np.array(Image.open(io.BytesIO(base64.b64decode(result.cloud_mask_b64))))
    validate_mask(mask, image.shape[:2])
    return mask, {"detector_fraction":float((mask>0).mean()), "detector_latency_ms":result.processing_time_ms}
