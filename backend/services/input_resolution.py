"""Resolve exactly the submitted imagery; never default to a demonstration."""
import base64
import hashlib
from backend.tools.scene_loader import UploadedSceneLoader, load_scene
from backend.schemas.models import ImageMetadata, AnalysisInput


def pixel_hash(scene):
    return hashlib.sha256(str(scene.image_np.shape).encode() + scene.image_np.tobytes()).hexdigest()


def resolve_inputs(uploaded_images, demo_scenario, image_ids, image_metadata):
    supplied = uploaded_images or []
    metadata = image_metadata or []
    if metadata and len(metadata) != len(supplied):
        raise ValueError("Image metadata count must match submitted image count")
    if image_ids and len(image_ids) != len(supplied):
        raise ValueError("Image IDs require matching submitted pixels; uploads are not persisted")
    if supplied:
        scenes = []
        for i, encoded in enumerate(supplied):
            m = metadata[i] if metadata else {}
            scene = UploadedSceneLoader().load(base64.b64decode(encoded, validate=True), m.get("filename", f"submitted_{i+1}.png"), m.get("sensor", "Unknown"))
            scene.acquisition_date = m.get("acquisition_date")
            scene.metadata.update(m)
            scenes.append(scene)
    elif demo_scenario:
        from backend.services.analysis_service import DEMO_SCENARIOS
        if demo_scenario not in DEMO_SCENARIOS:
            raise ValueError("Unknown explicit demonstration scenario")
        scenes = load_scene(demo_scenario)
    else:
        raise ValueError("No imagery supplied. Submit pixels or explicitly select a demonstration")
    if not 1 <= len(scenes) <= 2:
        raise ValueError("This pipeline accepts one image or one two-image pair")
    identities = []
    for i, scene in enumerate(scenes):
        raw = metadata[i] if supplied and metadata else {}
        digest = pixel_hash(scene)
        image_id = (image_ids[i] if image_ids else raw.get("image_id")) or digest
        meta = ImageMetadata(image_id=image_id, filename=raw.get("filename", scene.metadata.get("filename", f"image_{i+1}")),
            sensor=scene.sensor, acquisition_date=scene.acquisition_date or "Unknown",
            image_type=raw.get("image_type", "Optical"), resolution_m=raw.get("resolution_m"),
            width_px=scene.width, height_px=scene.height, source=raw.get("source", "user-submitted (unverified metadata)") if supplied else scene.source_path or "explicit demo",
            provenance=scene.input_provenance, pixel_sha256=digest)
        identities.append(AnalysisInput(role=f"image_{i+1}", image_id=image_id, metadata=meta))
    return scenes, identities
