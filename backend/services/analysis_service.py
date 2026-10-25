"""Local pipeline: resolved imagery, deterministic per-image repair, grounded summaries and recorded SSE events."""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional

from backend.schemas.models import (
    AnalysisSession, AnalysisInput, ImageMetadata, TaskType,
    TraceStep, ToolResult, ToolStatus, EvidenceStatus, ConfidenceLevel,
)
from backend.schemas.provenance import (
    ExecutionMode, InputProvenance, SecondaryEvidenceStatus
)
from backend.controller.central_controller import CentralController
from backend.tools.specialist_tools import get_tool


# In-memory session store (replace with DB in production)
SESSION_STORE: Dict[str, AnalysisSession] = {}

controller = CentralController()


# ─── Demo Scenario Data ───────────────────────────────────────────────────────

DEMO_SCENARIOS = {
    "demo1": {
        "title": "Real Change Scene",
        "description": "Bi-temporal registered change analysis (Sentinel-2 L2A).",
        "default_query": "Did the flood area expand near the river?",
        "task_type": TaskType.BI_TEMPORAL_CHANGE,
        "tags": ["REAL SATELLITE", "change detection", "bi-temporal", "flood"],
        "images": [
            ImageMetadata(sensor="Sentinel-2", acquisition_date="21 Apr 2022", image_type="Optical",
                         resolution_m=10.0, cloud_coverage_pct=9.0, cloud_status="Clear",
                         processing_status="Ready", filename="pre_flood.tif"),
            ImageMetadata(sensor="Sentinel-2", acquisition_date="15 Jul 2022", image_type="Optical",
                         resolution_m=10.0, cloud_coverage_pct=48.0, cloud_status="Detected",
                         processing_status="Ready", filename="peak_flood.tif"),
        ],
    },
    "demo3": {
        "title": "Real Cloud Scene",
        "description": "Optical cloud-quality analysis (Sentinel-2 L2A).",
        "default_query": "Detect clouds and reconstruct the hazy areas.",
        "task_type": TaskType.CLOUD_ANALYSIS,
        "tags": ["REAL SATELLITE", "cloud reconstruction", "automated"],
        "images": [
            ImageMetadata(sensor="Sentinel-2", acquisition_date="15 Jul 2022", image_type="Optical",
                         resolution_m=10.0, cloud_coverage_pct=35.0, cloud_status="Detected",
                         processing_status="Reconstruction required", filename="cloudy_scene.tif"),
        ],
    },
    "demo2": {
        "title": "SAR + Optical",
        "description": "Cross-modal reasoning. (EXPERIMENTAL / DATA PENDING)",
        "default_query": "Compare the optical and SAR images and identify built-up areas.",
        "task_type": TaskType.SAR_OPTICAL,
        "tags": ["EXPERIMENTAL", "SAR", "optical", "fusion"],
        "images": [
            ImageMetadata(sensor="Sentinel-2", acquisition_date="18 Oct 2025", image_type="Optical",
                         resolution_m=10.0, cloud_coverage_pct=5.0, cloud_status="Clear",
                         processing_status="Ready", filename="optical_scene.tif"),
            ImageMetadata(sensor="Sentinel-1", acquisition_date="19 Oct 2025", image_type="SAR",
                         resolution_m=10.0, cloud_coverage_pct=0.0, cloud_status="N/A (SAR)",
                         processing_status="Ready", filename="sar_scene.tif"),
        ],
    },
}


def get_demo_scenarios():
    return DEMO_SCENARIOS


def _tool_done_event(step_i: int, tool_name: str, step_desc: Dict, result: ToolResult) -> Dict:
    """Build the tool_done SSE event dict including provenance fields."""
    return {
        "type": "tool_done",
        "step_index": step_i,
        "tool_name": tool_name,
        "step_name": step_desc.get("step_name", tool_name),
        "status": result.status.value,
        "confidence": result.confidence,
        "message": result.message,
        "result": result.result,
        "visual_output": result.visual_output,
        "visual_type": result.visual_type,
        "metadata": result.metadata,
        "execution_time_ms": result.execution_time_ms,
        "is_auto_inserted": step_desc.get("is_auto_inserted", False),
        # Provenance fields for frontend badge
        "execution_mode": result.execution_mode.value if result.execution_mode else None,
        "input_provenance": result.input_provenance.value if result.input_provenance else None,
        "algorithm": result.algorithm,
        "evidence_excludable": result.evidence_excludable,
        "warnings": result.warnings,
        "registration_quality": result.registration_quality.value if result.registration_quality else None,
    }


async def run_analysis(
    query: str, demo_scenario: Optional[str] = None,
    image_ids: Optional[List[str]] = None, uploaded_images: Optional[List[str]] = None,
    image_metadata: Optional[List[Dict]] = None,
) -> AsyncGenerator[Dict, None]:
    """Execute a deterministic queue over resolved inputs, recording every event."""
    import hashlib
    import json
    from dataclasses import replace
    from backend.services.input_resolution import resolve_inputs, pixel_hash
    from backend.tools.scene_loader import UploadedSceneLoader
    from backend.tools.evidence import compute_evidence_strength, LOW_EVIDENCE_THRESHOLD, HIGH_EVIDENCE_THRESHOLD, RESEARCH_THRESHOLD, eligible
    from backend.solution_space.strategy_registry import CLOUD_THRESHOLD
    import base64

    session = AnalysisSession(query=query, status="running", is_demo=bool(demo_scenario and not uploaded_images))
    SESSION_STORE[session.analysis_id] = session

    def emit(event):
        session.events.append({**event, "timestamp": datetime.now(timezone.utc).isoformat()})
        return event

    yield emit({"type": "session_created", "analysis_id": session.analysis_id})
    limitations = []
    forced_outcome = None
    scenes, originals, working = [], [], []
    try:
        scenes, session.inputs = resolve_inputs(uploaded_images, demo_scenario, image_ids, image_metadata)
        originals = [s.image_b64 for s in scenes]
        working = list(scenes)
    except Exception as exc:
        limitations.append(f"INPUT_VALIDATION_FAILED: {exc}")
        forced_outcome = "failed"

    plan = controller.interpret_query(query, image_count=len(scenes))
    session.task_type, session.intent = plan.task_type, plan.intent
    task = plan.task_type.value
    if not forced_outcome and task == "bi_temporal_change":
        if len(scenes) != 2:
            limitations.append("MISSING_TEMPORAL_PAIR: two optical images are required.")
            forced_outcome = "unsupported"
        elif any(i.metadata.image_type.lower() != "optical" for i in session.inputs):
            limitations.append("INCOMPATIBLE_MODALITY: grayscale change requires two optical inputs.")
            forced_outcome = "unsupported"
        elif scenes[0].image_np.shape != scenes[1].image_np.shape:
            limitations.append("INCOMPATIBLE_DIMENSIONS: submit spatially corresponding rasters with equal dimensions.")
            forced_outcome = "unsupported"
        elif session.inputs[0].metadata.pixel_sha256 == session.inputs[1].metadata.pixel_sha256:
            limitations.append("DUPLICATE_TEMPORAL_INPUT: identical pixels do not establish two acquisitions.")
            forced_outcome = "unsupported"
    if not forced_outcome and task == "sar_optical":
        modalities = [i.metadata.image_type.lower() for i in session.inputs]
        limitations.append("SAR processing is unavailable." if "sar" in modalities else "MISSING_SAR: no identified SAR input; SAR processing is unavailable.")
        forced_outcome = "unsupported"
    if not forced_outcome and any(i.metadata.image_type.lower() != "optical" for i in session.inputs):
        limitations.append("INCOMPATIBLE_MODALITY: RGB cloud processing supports optical inputs only.")
        forced_outcome = "unsupported"

    yield emit({"type": "inputs_resolved", "inputs": [i.model_dump(mode="json") for i in session.inputs], "is_demo": session.is_demo})
    yield emit({"type": "step", "step": "query_understanding", "status": "done", "message": plan.intent,
                "detail": {"task_type": task, "image_count": len(scenes), "requires_sar": plan.requires_sar}})
    queue = []
    if not forced_outcome:
        queue = [("image_validation", None, False)] + [("cloud_detection", i, False) for i in range(len(scenes))]
        if task == "bi_temporal_change":
            queue.append(("bi_temporal_change_detection", None, False))
    session.plan = [n for n, _, _ in queue] + ["answer_synthesis"]
    yield emit({"type": "step", "step": "strategy_selection", "status": "done", "message": "Local algorithm pipeline selected.", "detail": {"tools": session.plan}})
    yield emit({"type": "thumbnails", "thumbnails": originals})
    masks, repaired, repair_failed = {}, set(), set()
    index = 0
    while index < len(queue):
        name, input_index, inserted = queue[index]
        desc = {"step_name": name.replace("_", " ").title() + (f" — image {input_index+1}" if input_index is not None else ""), "is_auto_inserted": inserted}
        yield emit({"type": "tool_start", "step_index": index, "tool_name": name, **desc})
        selected = [working[input_index]] if input_index is not None else working
        context = {"query": query, "task_type": task, "tool_results": [r.model_dump() for r in session.tool_results],
                   "uploaded_images": [s.image_b64 for s in selected], "input_provenance": selected[0].input_provenance,
                   "cloud_mask_b64": masks.get(input_index), "is_demo": session.is_demo}
        try:
            result = await asyncio.to_thread(get_tool(name).timed_run, {
                "images": context["uploaded_images"], "loaded_scenes": selected,
                "metadata": [i.metadata.model_dump() for i in session.inputs], "context": context, "params": {}})
        except Exception as exc:
            result = ToolResult(tool_name=name, status=ToolStatus.ERROR, message=f"Algorithm failure: {exc}",
                                execution_mode=ExecutionMode.LIVE_ALGORITHM, evidence_excludable=True)
        if result.execution_mode is None:
            result.execution_mode = ExecutionMode.LIVE_ALGORITHM
        result.input_provenance = selected[0].input_provenance
        result.is_demo = session.is_demo or any(s.input_provenance in (InputProvenance.SYNTHETIC_DATA, InputProvenance.DEMO_ASSET) for s in selected)
        result.metadata.update({"input_index": input_index, "input_pixel_hashes": [pixel_hash(s) for s in selected]})
        if result.status in (ToolStatus.ERROR, ToolStatus.SKIPPED) or result.is_demo:
            result.evidence_excludable = True
        if name == "cloud_detection" and result.execution_mode == ExecutionMode.LIVE_ALGORITHM and result.status != ToolStatus.ERROR:
            session.inputs[input_index].metadata.cloud_coverage_pct = result.result.get("cloud_coverage_pct")
            session.inputs[input_index].metadata.cloud_status = "RGB candidates measured"
            masks[input_index] = result.visual_output
            fraction = result.result.get("cloud_pixel_count", 0) / max(1, result.result.get("total_pixel_count", 1))
            result.metadata["mask_sha256"] = hashlib.sha256(base64.b64decode(masks[input_index])).hexdigest() if masks[input_index] else None
            if fraction >= CLOUD_THRESHOLD and masks[input_index]:
                queue.insert(index+1, ("cloud_reconstruction", input_index, True))
                session.plan = [n for n, _, _ in queue] + ["answer_synthesis"]
                reason = f"Image {input_index+1}: measured cloud fraction {fraction:.6f} >= policy {CLOUD_THRESHOLD}; local CPU inpainting requested."
                result.metadata["injection_reason"] = reason
                yield emit({"type": "plan_updated", "message": reason, "new_plan": session.plan, "inserted_tool": "cloud_reconstruction", "input_index": input_index})
        if name == "cloud_reconstruction":
            if result.status == ToolStatus.SUCCESS and result.result.get("success") and result.visual_output:
                decoded = UploadedSceneLoader().load(base64.b64decode(result.visual_output))
                working[input_index] = replace(working[input_index], image_np=decoded.image_np, image_b64=decoded.image_b64)
                repaired.add(input_index)
                result.metadata["output_pixel_hash"] = pixel_hash(working[input_index])
            else:
                repair_failed.add(input_index)
            result.evidence_excludable = True  # interpolation is not independent supporting evidence
        if name == "bi_temporal_change_detection" and (repaired or repair_failed):
            result.evidence_excludable = True
            result.result["changed_area_pct"] = None
            result.result["changed_pixel_count"] = None
            result.result["unchanged_pixel_count"] = None
            result.message = "Change reporting withheld because inputs contain cloud-affected or estimated pixels."
            result.visual_output = None
            result.metadata.pop("heatmap_b64", None)
            result.warnings.append("Change reporting withheld: cloud-affected or estimated pixels require a validated clear-pixel comparison protocol.")
        if name == "cloud_detection" and task != "cloud_analysis":
            result.evidence_excludable = True  # quality checks cannot support semantic/change answers
        if result.status == ToolStatus.ERROR:
            limitations.append(f"{name} failed: {result.message}")
        session.tool_results.append(result)
        session.trace.append(TraceStep(step_index=index, step_name=desc["step_name"], description=result.message,
            status=result.status, tool_name=name, tool_result=result, timestamp=datetime.now(timezone.utc).isoformat(), is_auto_inserted=inserted))
        yield emit(_tool_done_event(index, name, desc, result))
        if name == "image_validation" and (result.status != ToolStatus.SUCCESS or not result.result.get("all_valid")):
            limitations.append("Image validation failed; downstream processing stopped.")
            forced_outcome = "failed"
            break
        index += 1

    if not forced_outcome and session.tool_results and all(r.status == ToolStatus.ERROR for r in session.tool_results if r.tool_name != "image_validation"):
        forced_outcome = "failed"
    answer_context = {"query": query, "task_type": task, "tool_results": [r.model_dump() for r in session.tool_results],
                      "limitations": limitations, "forced_outcome": forced_outcome, "is_demo": session.is_demo,
                      "input_provenance": scenes[0].input_provenance if scenes else InputProvenance.UNKNOWN}
    answer_index = len(session.trace)
    yield emit({"type": "tool_start", "step_index": answer_index, "tool_name": "answer_synthesis", "step_name": "Grounded summary"})
    answer = get_tool("answer_synthesis").timed_run({"context": answer_context})
    session.tool_results.append(answer)
    session.trace.append(TraceStep(step_index=answer_index, step_name="Grounded summary", description=answer.message,
        status=answer.status, tool_name=answer.tool_name, tool_result=answer, timestamp=datetime.now(timezone.utc).isoformat()))
    yield emit(_tool_done_event(answer_index, answer.tool_name, {"step_name": "Grounded summary"}, answer))
    session.final_answer = answer.result["final_answer"]
    session.status = answer.result["outcome"]
    dictionaries = [r.model_dump(mode="json") for r in session.tool_results]
    ev = compute_evidence_strength(dictionaries)
    session.confidence = ev.evidence_strength
    session.confidence_level = ConfidenceLevel.HIGH if ev.evidence_strength >= HIGH_EVIDENCE_THRESHOLD else ConfidenceLevel.MEDIUM if ev.evidence_strength >= LOW_EVIDENCE_THRESHOLD else ConfidenceLevel.LOW
    session.evidence_status = EvidenceStatus.INSUFFICIENT  # no independent same-claim verification exists
    session.evidence_points = [f"Computed: {r.tool_name} ({r.algorithm})" for r in session.tool_results if eligible(r.model_dump())]
    visuals = [{"type": "before" if i==0 else "after", "label": f"Original image {i+1} — {session.inputs[i].metadata.acquisition_date}", "b64": img} for i, img in enumerate(originals)]
    for r in session.tool_results:
        if r.visual_output and r.execution_mode == ExecutionMode.LIVE_ALGORITHM:
            visuals.append({"type": "reconstruction" if r.visual_type=="reconstructed" else r.visual_type or "image", "label": f"{'DEMONSTRATION: ' if r.is_demo else ''}{r.tool_name} — {r.algorithm}", "b64": r.visual_output})
    session.visual_outputs = visuals
    session.completed_at = datetime.now(timezone.utc).isoformat()
    digest_payload = {"pipeline": "phase1_v2", "query": query, "inputs": [i.model_dump(mode="json") for i in session.inputs],
                      "plan": session.plan, "results": dictionaries, "evidence": ev.breakdown, "outcome": session.status,
                      "policy": {"cloud": CLOUD_THRESHOLD, "low_evidence": LOW_EVIDENCE_THRESHOLD}}
    session.audit_manifest = digest_payload
    digest = hashlib.sha256(json.dumps(digest_payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    session.completion = {"type": "completed", "analysis_id": session.analysis_id, "outcome": session.status,
        "confidence": session.confidence, "confidence_level": session.confidence_level.value,
        "evidence_status": session.evidence_status.value, "final_answer": session.final_answer,
        "evidence_points": session.evidence_points, "visual_outputs": visuals, "conflicts": [],
        "evidence_breakdown": ev.breakdown, "evidence_formula": ev.formula, "evidence_interpretation": ev.interpretation,
        "low_evidence": ev.low_evidence, "has_real_images": bool(scenes) and not session.is_demo,
        "audit_hash": digest, "verified": False, "limitations": answer.result["limitations"],
        "inputs": [i.model_dump(mode="json") for i in session.inputs],
        "threshold_policy": {"low_evidence": LOW_EVIDENCE_THRESHOLD, "high_evidence": HIGH_EVIDENCE_THRESHOLD, "research": RESEARCH_THRESHOLD},
        "score_kind": "heuristic_evidence", "secondary_evidence_status": "NO_SECONDARY_EVIDENCE_AVAILABLE"}
    if ev.low_evidence:
        yield emit({"type": "low_evidence", "evidence_strength": ev.evidence_strength,
                    "threshold": LOW_EVIDENCE_THRESHOLD, "message": "Insufficient supporting heuristic evidence.",
                    "secondary_evidence_status": "NO_SECONDARY_EVIDENCE_AVAILABLE",
                    "secondary_evidence_reason": "No independent comparison was performed."})
    yield emit(session.completion)


def get_session(analysis_id: str) -> Optional[AnalysisSession]:
    return SESSION_STORE.get(analysis_id)
