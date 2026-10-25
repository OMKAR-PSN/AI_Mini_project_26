"""Deterministic summaries: values must be present in successful live results."""
from backend.schemas.provenance import ExecutionMode
import re


def synthesize(context):
    results = context.get("tool_results", [])
    facts, limitations = [], list(context.get("limitations", []))
    change_supported = False
    cloud_supported = False
    for r in results:
        name, data = r.get("tool_name"), r.get("result", {})
        live = r.get("execution_mode") == ExecutionMode.LIVE_ALGORITHM
        success = r.get("status") in ("success", "warning")
        if name == "cloud_detection" and live and success and "cloud_coverage_pct" in data:
            facts.append(f"Image {r.get('metadata', {}).get('input_index', 0) + 1}: RGB brightness/whiteness detector marked {data['cloud_coverage_pct']:.2f}% of pixels as cloud candidates.")
            cloud_supported = True
        elif name == "cloud_reconstruction":
            if live and success and data.get("success"):
                facts.append(f"Image {r.get('metadata', {}).get('input_index', 0) + 1}: CPU inpainting executed using {r.get('algorithm')}. Estimated pixels are not measured ground truth.")
            else:
                limitations.append("Cloud repair failed; original imagery retained. No completed repair is claimed.")
        elif name == "bi_temporal_change_detection":
            if live and success and not r.get("evidence_excludable") and data.get("changed_area_pct") is not None:
                facts.append(f"Grayscale intensity-change candidates cover {data['changed_area_pct']:.2f}% of raster pixels. This is not geographic area or semantic urban/vegetation/flood change.")
                change_supported = True
            else:
                limitations.append("Reliable change measurement unavailable; no change percentage is reported.")
    task = context.get("task_type", "unknown")
    if task not in ("cloud_analysis", "bi_temporal_change"):
        limitations.append("Semantic classification, object identification, spatial distance measurement and SAR fusion are unavailable in this phase.")
    if task == "bi_temporal_change":
        limitations.append("No semantic model or independently validated geometric accuracy is available.")
    if re.search(r"\b(urban|built-up|vegetation|flood|classify|classification|distance|metres|meters)\b", context.get("query", ""), re.I):
        limitations.append("The requested semantic or geographic interpretation is unsupported; only the listed pixel computations were performed.")
    supported = (task == "cloud_analysis" and cloud_supported) or (task == "bi_temporal_change" and change_supported)
    outcome = context.get("forced_outcome")
    if not outcome:
        outcome = "completed_supported" if supported and not limitations else "completed_partial" if facts else "abstained"
    if context.get("is_demo"):
        limitations.insert(0, "Demonstration run: excluded from scientific evaluation.")
        if outcome == "completed_supported":
            outcome = "completed_partial"
    text = " ".join(facts + list(dict.fromkeys(limitations))) or "Insufficient evidence to answer the query."
    return {"final_answer": text, "outcome": outcome,
            "query_answered": outcome == "completed_supported", "limitations": list(dict.fromkeys(limitations)),
            "verified": False, "score_kind": "heuristic_evidence"}
