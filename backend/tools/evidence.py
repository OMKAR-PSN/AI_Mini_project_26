"""Heuristic evidence, not calibrated probability.

Nominal weights: quality .25, algorithm .30, registration screening .25,
independent agreement .20. Registration weight is equally redistributed if
not applicable. No current tool implements an independent agreement check.
Demo/synthetic, missing provenance, failed/excluded and bookkeeping outputs
cannot supply algorithm evidence. No eligible support forces total score zero.
Runtime low-evidence threshold remains .55; research threshold .60 is separate.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import hashlib
import json

from backend.schemas.provenance import (
    ExecutionMode, InputProvenance, RegistrationQuality, SecondaryEvidenceStatus
)


# ── Constants ─────────────────────────────────────────────────────────────────

WEIGHTS = {
    "data_quality":         0.25,
    "algorithm_confidence": 0.30,
    "registration_quality": 0.25,
    "cross_method_agreement": 0.20,
}
LOW_EVIDENCE_THRESHOLD = 0.55
RESEARCH_THRESHOLD = 0.60  # reporting protocol only; not a runtime decision threshold
HIGH_EVIDENCE_THRESHOLD = 0.75

META_TOOLS = {"image_validation", "cloud_reconstruction", "confidence_check", "evidence_comparison", "answer_synthesis"}

def eligible(r):
    return (r.get("tool_name") not in META_TOOLS
            and r.get("execution_mode") == ExecutionMode.LIVE_ALGORITHM
            and not r.get("evidence_excludable", False)
            and not r.get("is_demo", True)
            and r.get("status", "success") in ("success", "warning")
            and r.get("input_provenance") in (InputProvenance.USER_UPLOAD, InputProvenance.REAL_SATELLITE_DATA, InputProvenance.BENCHMARK_DATA)
            and r.get("registration_quality") not in (RegistrationQuality.FAILED, RegistrationQuality.PARTIAL))


# ── Result data class ─────────────────────────────────────────────────────────

@dataclass
class EvidenceStrengthResult:
    evidence_strength: float
    confidence_level: str           # "high" | "moderate" | "low" | "very_low"
    breakdown: Dict[str, Dict]      # factor → {score, reason, weight}
    formula: str
    low_evidence: bool
    secondary_evidence_status: Optional[SecondaryEvidenceStatus]
    secondary_evidence_reason: Optional[str]
    interpretation: str
    audit_hash: str
    warnings: list = field(default_factory=list)


def _interpret(score: float) -> str:
    if score >= HIGH_EVIDENCE_THRESHOLD:
        return "High heuristic evidence; not calibrated probability or independent verification."
    elif score >= LOW_EVIDENCE_THRESHOLD:
        return "Moderate evidence — minor caveats apply."
    elif score >= 0.40:
        return "Low evidence — results should be treated with caution."
    else:
        return "Very low evidence — result is not suitable for authoritative reporting."


def _confidence_level(score: float) -> str:
    if score >= HIGH_EVIDENCE_THRESHOLD:
        return "high"
    elif score >= LOW_EVIDENCE_THRESHOLD:
        return "moderate"
    elif score >= 0.35:
        return "low"
    return "very_low"


# ── Factor calculators ────────────────────────────────────────────────────────

def _data_quality_factor(tool_results: List[Dict]) -> Dict:
    score = 1.0
    reasons = []

    # Check provenance across all results
    provenances = [r.get("input_provenance") for r in tool_results if r.get("input_provenance")]
    has_synthetic = any(p == InputProvenance.SYNTHETIC_DATA for p in provenances)
    has_unknown = not tool_results or any(not r.get("input_provenance") or r.get("input_provenance") == InputProvenance.UNKNOWN for r in tool_results)

    if has_synthetic:
        score -= 0.30
        reasons.append("Synthetic input (-0.30)")
    if has_unknown:
        score -= 0.20
        reasons.append("Missing or unknown input provenance (-0.20)")

    # Check cloud contamination
    for r in tool_results:
        result_data = r.get("result", {})
        cloud_pct = result_data.get("cloud_percentage") or result_data.get("cloud_coverage_pct")
        if cloud_pct is not None and cloud_pct >= 20.0:
            score -= 0.30
            reasons.append(f"Cloud contamination {cloud_pct:.1f}% ≥ 20% threshold (-0.30)")
            break

    # Check if any tool is demo-mode
    any_demo = any(r.get("is_demo", True) for r in tool_results)
    if any_demo:
        score -= 0.20
        reasons.append("Demonstration input/output (-0.20)")

    score = max(0.0, min(1.0, score))
    if not reasons:
        reasons.append("Recorded source provenance; no detected quality penalty. Source authenticity is not verified.")

    return {
        "score": round(score, 3),
        "reason": " | ".join(reasons),
        "weight": WEIGHTS["data_quality"],
    }


def _algorithm_confidence_factor(tool_results: List[Dict]) -> Dict:
    live_confs = [
        r.get("confidence", 0.0)
        for r in tool_results
        if eligible(r)
        and r.get("confidence") is not None
    ]

    if not live_confs:
        return {
            "score": 0.0,
            "reason": "No LIVE_ALGORITHM tool results available — all tools ran in simulated mode.",
            "weight": WEIGHTS["algorithm_confidence"],
        }

    score = round(sum(live_confs) / len(live_confs), 3)
    return {
        "score": score,
        "reason": (
            f"Mean confidence across tool(s): {score:.3f}. "
            f"Excludes low-quality and excluded results."
        ),
        "weight": WEIGHTS["algorithm_confidence"],
    }


def _registration_factor(tool_results: List[Dict]) -> Optional[Dict]:
    """
    Returns None if no registration result exists (weight redistributed).
    """
    for r in tool_results:
        if (r.get("execution_mode") != ExecutionMode.LIVE_ALGORITHM
                or r.get("is_demo", True) or r.get("evidence_excludable", False)
                or r.get("input_provenance") not in (InputProvenance.USER_UPLOAD, InputProvenance.REAL_SATELLITE_DATA, InputProvenance.BENCHMARK_DATA)):
            continue
        reg_quality = r.get("registration_quality")
        if reg_quality is None:
            continue
        if reg_quality == RegistrationQuality.SUCCESS:
            return {
                "score": 1.0,
                "reason": "ECC converged within the photometric residual screening threshold; geometric accuracy is unverified.",
                "weight": WEIGHTS["registration_quality"],
            }
        elif reg_quality == RegistrationQuality.PARTIAL:
            return {
                "score": 0.5,
                "reason": "Registration converged but error exceeded strict threshold — partial quality.",
                "weight": WEIGHTS["registration_quality"],
            }
        elif reg_quality == RegistrationQuality.FAILED:
            return {
                "score": 0.0,
                "reason": "Registration FAILED — change detection result excluded from evidence.",
                "weight": WEIGHTS["registration_quality"],
            }
        elif reg_quality in (RegistrationQuality.NOT_ATTEMPTED, RegistrationQuality.NOT_REQUIRED):
            return {
                "score": None,  # weight redistributed
                "reason": "Registration not applicable for this analysis type.",
                "weight": 0.0,  # excluded from sum
            }
    # No registration tool ran
    return None


def _cross_method_agreement_factor(tool_results: List[Dict]) -> Dict:
    # Absence of a conflict is not an independent comparison. No current
    # pipeline tool implements a validated, independent agreement test.
    return {"score": 0.0, "reason": "No independent same-claim comparison was executed.",
            "weight": WEIGHTS["cross_method_agreement"]}


# ── Main function ─────────────────────────────────────────────────────────────

def compute_evidence_strength(
    tool_results: List[Dict],
    secondary_evidence_available: bool = False,
    secondary_evidence_note: Optional[str] = None,
) -> EvidenceStrengthResult:
    """
    Compute explainable Evidence Strength Score from tool results.

    Args:
        tool_results:  List of ToolResult.model_dump() dicts from the pipeline.
        secondary_evidence_available: True only if a real independent
            evidence source was actually checked.
        secondary_evidence_note: Human-readable description of what secondary
            evidence was checked (or why none was available).

    Returns:
        EvidenceStrengthResult with full breakdown and provenance metadata.
    """
    tool_results = [r for r in tool_results if r.get("tool_name") not in META_TOOLS]
    # ── Compute factors ───────────────────────────────────────────────────────
    data_q    = _data_quality_factor(tool_results)
    algo_conf = _algorithm_confidence_factor(tool_results)
    reg_q     = _registration_factor(tool_results)
    agree_q   = _cross_method_agreement_factor(tool_results)

    # ── Redistribute registration weight if not applicable ────────────────────
    if reg_q is None or reg_q.get("score") is None:
        # Spread the registration weight across remaining three factors
        extra = WEIGHTS["registration_quality"] / 3.0
        w_data  = WEIGHTS["data_quality"]         + extra
        w_algo  = WEIGHTS["algorithm_confidence"] + extra
        w_agree = WEIGHTS["cross_method_agreement"] + extra
        reg_contribution = 0.0
    else:
        w_data  = WEIGHTS["data_quality"]
        w_algo  = WEIGHTS["algorithm_confidence"]
        w_agree = WEIGHTS["cross_method_agreement"]
        reg_contribution = reg_q["score"] * WEIGHTS["registration_quality"]

    # ── Weighted sum ──────────────────────────────────────────────────────────
    evidence_strength = round(
        data_q["score"] * w_data
        + algo_conf["score"] * w_algo
        + reg_contribution
        + agree_q["score"] * w_agree,
        3,
    )
    evidence_strength = max(0.0, min(1.0, evidence_strength))

    if not any(eligible(r) for r in tool_results):
        evidence_strength = 0.0
    data_q["weight"] = w_data
    algo_conf["weight"] = w_algo
    agree_q["weight"] = w_agree
    if reg_q is not None and reg_q["score"] is None:
        reg_q["weight"] = 0.0

    # ── Low evidence check ────────────────────────────────────────────────────
    low_evidence = evidence_strength < LOW_EVIDENCE_THRESHOLD

    if low_evidence:
        if secondary_evidence_available:
            sec_status = SecondaryEvidenceStatus.CONFIRMED
            sec_reason = secondary_evidence_note or "Secondary analysis was performed."
        else:
            sec_status = SecondaryEvidenceStatus.NO_SECONDARY_EVIDENCE_AVAILABLE
            sec_reason = (
                secondary_evidence_note
                or "No genuinely independent secondary evidence source is available for this input. "
                   "A secondary analysis was NOT manufactured to trigger a re-analysis demo."
            )
    else:
        sec_status = None
        sec_reason = None

    # ── Build breakdown dict ──────────────────────────────────────────────────
    breakdown = {
        "data_quality": data_q,
        "algorithm_confidence": algo_conf,
        "cross_method_agreement": agree_q,
    }
    if reg_q is not None:
        breakdown["registration_quality"] = reg_q

    formula = "evidence_strength = " + " + ".join(
        f"{v['weight']:.6f} * {k}({v['score']})" for k, v in breakdown.items()
        if v['score'] is not None
    ) + f" = {evidence_strength:.3f} (zero when no eligible supporting computation)"

    # ── Generate Audit Hash ───────────────────────────────────────────────────
    hash_payload = {"results": tool_results, "breakdown": breakdown, "strength": evidence_strength}
    audit_hash = hashlib.sha256(json.dumps(hash_payload, sort_keys=True).encode("utf-8")).hexdigest()

    return EvidenceStrengthResult(
        evidence_strength=evidence_strength,
        confidence_level=_confidence_level(evidence_strength),
        breakdown=breakdown,
        formula=formula,
        low_evidence=low_evidence,
        secondary_evidence_status=sec_status,
        secondary_evidence_reason=sec_reason,
        interpretation=_interpret(evidence_strength),
        audit_hash=audit_hash,
    )
