"""Stable identities and atomic, configuration-isolated checkpoints."""
import csv
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import platform
import subprocess
import uuid
from datetime import datetime, timezone
import numpy as np

REPO = Path(__file__).resolve().parents[3]

def utcnow():
    return datetime.now(timezone.utc).isoformat()

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()

def image_digest(array):
    a = np.ascontiguousarray(array)
    return hashlib.sha256(str((a.shape, a.dtype.str)).encode() + a.tobytes()).hexdigest()

def atomic_bytes(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    with temp.open("wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, path)

def atomic_json(path, value):
    atomic_bytes(path, json.dumps(value, indent=2, sort_keys=True, allow_nan=False).encode())

def write_csv(path, rows, fields=None):
    rows = list(rows)
    fields = fields or sorted({key for row in rows for key in row})
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    atomic_bytes(path, output.getvalue().encode("utf-8"))

def source_fingerprint():
    paths = list((REPO / "research/src").rglob("*.py")) + [REPO / p for p in (
        "backend/tools/cloud_detector.py", "backend/providers/cpu_provider.py",
        "backend/providers/base.py", "backend/schemas/provenance.py",
        "backend/solution_space/strategy_registry.py")]
    return {str(p.relative_to(REPO)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(paths)}

def environment():
    names = ["numpy", "pillow", "opencv-python-headless", "torch", "torchvision", "datasets",
             "transformers", "accelerate", "huggingface-hub", "satellite-cloud-generator", "kornia", "matplotlib",
             "scipy", "scikit-image", "pandas", "PyYAML", "imageio", "pydantic", "pyarrow"]
    versions = {}
    for name in names:
        try: versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError: versions[name] = None
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=REPO, text=True))
    except (OSError, subprocess.CalledProcessError): commit, dirty = None, None
    info = {"python": platform.python_version(), "platform": platform.platform(), "packages": versions,
            "git_commit": commit, "working_tree_dirty": dirty, "cuda_available": False}
    try:
        import torch
        info.update(torch_version=torch.__version__, cuda_version=torch.version.cuda,
                    cuda_available=torch.cuda.is_available())
        if torch.cuda.is_available():
            free, total = torch.cuda.mem_get_info()
            info.update(gpu=torch.cuda.get_device_name(0), gpu_free_bytes=free, gpu_total_bytes=total)
    except ImportError: pass
    return info

class Checkpoints:
    def __init__(self, folder, identity):
        self.folder = Path(folder)
        self.identity = identity
        path = self.folder / "identity.json"
        if path.exists() and json.loads(path.read_text()) != identity:
            raise ValueError("Configuration/source/environment mismatch: use a new run directory")
        atomic_json(path, identity)

    def path(self, kind, key):
        if not kind.replace("_", "").isalnum(): raise ValueError("Invalid checkpoint kind")
        return self.folder / "records" / kind / (digest(key) + ".json")

    def get(self, kind, key):
        p = self.path(kind, key)
        return json.loads(p.read_text()) if p.exists() else None

    def put(self, kind, key, row):
        existing = self.get(kind, key)
        if existing is not None and existing != row:
            raise ValueError("Refusing to replace an existing completed item")
        atomic_json(self.path(kind, key), row)

    def rows(self, kind):
        return [json.loads(p.read_text()) for p in sorted((self.folder / "records" / kind).glob("*.json"))]
