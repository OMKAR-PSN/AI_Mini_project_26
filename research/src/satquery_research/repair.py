"""Reuse the CPU provider; never annotate scientific pixel arrays."""
import base64
import io
import time
import numpy as np
from PIL import Image
from backend.providers.cpu_provider import CPUInpaintingProvider
from .metrics import validate_mask

def encode(array):
    stream = io.BytesIO()
    Image.fromarray(array).save(stream, format="PNG")
    return base64.b64encode(stream.getvalue()).decode()

def repair(image, mask, algorithm="telea", radius=10):
    if image.dtype != np.uint8 or image.ndim != 3 or image.shape[2] != 3:
        raise ValueError("Require uint8 RGB")
    validate_mask(mask, image.shape[:2])
    if not np.isfinite(radius) or radius <= 0: raise ValueError("Positive finite radius required")
    start = time.perf_counter()
    result = CPUInpaintingProvider(algorithm=algorithm, radius=radius).reconstruct(encode(image), encode(mask))
    if not result.success: raise ValueError(result.message)
    output = np.array(Image.open(io.BytesIO(base64.b64decode(result.output_b64))).convert("RGB"))
    if not np.array_equal(output[mask == 0], image[mask == 0]):
        raise AssertionError("Provider modified unmasked pixels")
    return output, {"repair_algorithm":result.algorithm, "radius":radius,
        "mask_fraction":float((mask>0).mean()), "repair_latency_ms":1000*(time.perf_counter()-start),
        "empty_mask_noop":not bool(mask.any())}
