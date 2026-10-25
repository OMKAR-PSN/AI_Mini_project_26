"""Published opacity generator, plus a separately labelled legacy-style diagnostic."""
from contextlib import contextmanager
import importlib.metadata
import json
import random
import numpy as np
from .metrics import validate_mask

REVISION = 'd0787cbdc1b39a7976f89aa085f1430f3207eda6'

@contextmanager
def seeded(seed):
    import torch
    py, npstate = random.getstate(), np.random.get_state()
    with torch.random.fork_rng(devices=[]):
        random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
        try: yield
        finally: random.setstate(py); np.random.set_state(npstate)

def opacity_mask(opacity, threshold):
    if opacity.ndim != 2 or not np.isfinite(opacity).all() or np.any((opacity<0)|(opacity>1)):
        raise ValueError('Opacity must be finite HxW in [0,1]')
    if not 0 < threshold <= 1: raise ValueError('Opacity threshold must be in (0,1]')
    return ((opacity >= threshold)*255).astype(np.uint8)

def verify_generator():
    raw = importlib.metadata.distribution('satellite-cloud-generator').read_text('direct_url.json')
    revision = json.loads(raw or '{}').get('vcs_info', {}).get('commit_id')
    if revision != REVISION: raise RuntimeError('Install SatelliteCloudGenerator at the pinned Git revision')

def generate(image, target, seed, config):
    if image.dtype != np.uint8 or image.ndim != 3 or image.shape[2] != 3:
        raise ValueError('Require HxWx3 uint8 RGB')
    if not 0 <= target <= 1: raise ValueError('Target fraction outside [0,1]')
    threshold = config['opacity_threshold']
    shape = image.shape[:2]
    if target == 0:
        opacity = np.zeros(shape, np.float32)
        return image.copy(), opacity, opacity_mask(opacity, threshold), dict(clear_threshold=None, shadow_status='not generated')
    if config['name'] == 'legacy_style_opaque':
        # Original historical implementation was unavailable. This is a NEW sanity baseline.
        import cv2
        field = cv2.resize(np.random.default_rng(seed).random((8,8)).astype(np.float32),
                           (shape[1],shape[0]), interpolation=cv2.INTER_CUBIC)
        count = round(target*field.size)
        opacity = np.zeros(field.size, np.float32)
        opacity[np.argsort(field.ravel(), kind='stable')[-count:]] = 1 if count else 0
        opacity = opacity.reshape(shape)
        output = image.copy(); output[opacity>0] = 255
        return output, opacity, opacity_mask(opacity, threshold), dict(clear_threshold=None, shadow_status='not generated')
    if config['name'] != 'published': raise ValueError('Unknown generator')
    if config.get('revision') != REVISION: raise ValueError('Generator configuration revision mismatch')
    verify_generator()
    import torch
    from satellite_cloud_generator import add_cloud
    tensor = torch.from_numpy(image.copy()).permute(2,0,1)[None].float()/255
    low, high, best = 0., 1., None
    # Common random numbers: candidate thresholds use the identical noise field.
    for i in range(config['coverage_search_iterations']):
        cutoff = 0. if i == 0 else (low+high)/2
        with seeded(seed), torch.inference_mode():
            output, cloud = add_cloud(tensor, clear_threshold=cutoff, return_cloud=True, **config['parameters'])
        if tuple(cloud.shape) != tuple(tensor.shape): raise ValueError('Unexpected published BCHW opacity shape')
        opacity = cloud[0].mean(0).cpu().numpy().astype(np.float32).clip(0,1)
        mask = opacity_mask(opacity, threshold)
        achieved = float((mask>0).mean())
        error = abs(achieved-target)
        if best is None or error < best[0]:
            rgb = np.rint(output[0].permute(1,2,0).cpu().numpy().clip(0,1)*255).astype(np.uint8)
            best = error, rgb, opacity.copy(), mask, cutoff
        if achieved > target: low = cutoff
        else: high = cutoff
    _, rgb, opacity, mask, cutoff = best
    validate_mask(mask, shape)
    return rgb, opacity, mask, dict(clear_threshold=cutoff, shadow_status='not generated; add_cloud only')
