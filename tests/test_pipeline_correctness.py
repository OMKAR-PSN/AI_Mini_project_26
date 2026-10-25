"""Local scientific contracts: no providers or network services required."""
import asyncio
import base64
import io
import json
from dataclasses import replace
import numpy as np
import pytest
from PIL import Image
from backend.services import analysis_service as service
from backend.schemas.models import ToolResult, ToolStatus
from backend.schemas.provenance import ExecutionMode, InputProvenance, RegistrationQuality
from backend.providers.cpu_provider import CPUInpaintingProvider
from backend.tools.evidence import compute_evidence_strength
from backend.tools.registration import _mean_absolute_intensity_residual
from backend.tools.change_detector import detect_change


def encode(array):
    out = io.BytesIO()
    Image.fromarray(array).save(out, format="PNG")
    return base64.b64encode(out.getvalue()).decode()


def pixels(value=30):
    return encode(np.full((64, 64, 3), value, dtype=np.uint8))


def run(query="Detect clouds", **kwargs):
    async def collect():
        return [e async for e in service.run_analysis(query, **kwargs)]
    return asyncio.run(collect())


@pytest.fixture(autouse=True)
def no_external_network(monkeypatch):
    # asyncio on Windows needs a local socketpair; block HTTP clients instead.
    import requests
    monkeypatch.setattr(requests.sessions.Session, "request", lambda *a, **k: pytest.fail("External request attempted"))
    yield
    service.SESSION_STORE.clear()


def test_submitted_pixels_override_demo(monkeypatch):
    monkeypatch.setattr("backend.services.input_resolution.load_scene", lambda *a: pytest.fail("Demo was loaded"))
    events = run(uploaded_images=[pixels()], demo_scenario="demo1", image_metadata=[{"image_id":"my-image", "acquisition_date":"2025-01-01"}])
    done = events[-1]
    assert done["inputs"][0]["image_id"] == "my-image"
    assert done["inputs"][0]["metadata"]["width_px"] == 64
    assert done["inputs"][0]["metadata"]["acquisition_date"] == "2025-01-01"
    validation = next(e for e in events if e.get("tool_name")=="image_validation" and e["type"]=="tool_done")
    assert validation["result"]["images_received"] == 1
    assert next(e for e in events if e["type"]=="thumbnails")["thumbnails"] == [pixels()]
    assert done["outcome"] == "completed_supported"


def mock_cloud(monkeypatch, fraction, fail=False):
    original = service.get_tool
    mask = np.zeros((64,64), np.uint8)
    mask[20:40,20:40] = 255
    class Cloud:
        def timed_run(self, inputs):
            return ToolResult(tool_name="cloud_detection", status=ToolStatus.SUCCESS, confidence=.8,
                result={"cloud_coverage_pct":fraction*100, "cloud_pixel_count":int(fraction*10000), "total_pixel_count":10000},
                visual_output=encode(mask), visual_type="cloud_mask", execution_mode=ExecutionMode.LIVE_ALGORITHM, is_demo=False)
    class FailedRepair:
        def timed_run(self, inputs):
            return ToolResult(tool_name="cloud_reconstruction", status=ToolStatus.ERROR, message="Controlled repair failure", result={"success":False})
    monkeypatch.setattr(service, "get_tool", lambda name: Cloud() if name=="cloud_detection" else FailedRepair() if fail and name=="cloud_reconstruction" else original(name))


@pytest.mark.parametrize("fraction, expected", [(0.1999,0),(0.20,1),(0.2001,1)])
def test_measured_cloud_boundary_executes_queue(monkeypatch, fraction, expected):
    mock_cloud(monkeypatch, fraction)
    events = run(uploaded_images=[pixels()])
    repairs = [e for e in events if e["type"]=="tool_done" and e["tool_name"]=="cloud_reconstruction"]
    assert len(repairs) == expected
    if expected:
        assert repairs[0]["status"] == "success"
        assert repairs[0]["is_auto_inserted"]
        assert repairs[0]["metadata"]["radius_px"] == 10
    session = service.get_session(events[-1]["analysis_id"])
    assert [t.tool_name for t in session.trace] == [e["tool_name"] for e in events if e["type"]=="tool_done"]
    assert [e["type"] for e in session.events] == [e["type"] for e in events]
    assert session.plan == [t.tool_name for t in session.trace]


def test_both_dates_repaired_and_downstream_consumes_estimates(monkeypatch):
    mock_cloud(monkeypatch, .30)
    actual_get = service.get_tool
    seen = []
    class Change:
        def timed_run(self, inputs):
            seen.extend(inputs["images"])
            assert inputs["loaded_scenes"][0].image_b64 == inputs["images"][0]
            return ToolResult(tool_name="bi_temporal_change_detection", status=ToolStatus.SUCCESS, result={"changed_area_pct":88}, execution_mode=ExecutionMode.LIVE_ALGORITHM)
    monkeypatch.setattr(service,"get_tool", lambda name: Change() if name=="bi_temporal_change_detection" else actual_get(name))
    a=np.full((64,64,3),30,np.uint8); a[20:40,20:40]=255
    b=a.copy(); b[0:5]=90
    original=[encode(a),encode(b)]
    events=run("Measure change",uploaded_images=original)
    assert len(seen)==2 and all(x!=y for x,y in zip(seen,original))
    assert len([e for e in events if e["type"]=="tool_done" and e["tool_name"]=="cloud_reconstruction"])==2
    assert next(e for e in events if e["type"]=="thumbnails")["thumbnails"] == original
    assert "88" not in events[-1]["final_answer"]
    assert events[-1]["outcome"] == "completed_partial"


def test_failed_repair_is_partial(monkeypatch):
    mock_cloud(monkeypatch,.3,fail=True)
    result=run(uploaded_images=[pixels()])[-1]
    assert result["outcome"]=="completed_partial"
    assert "repair failed" in result["final_answer"]
    assert not any(v["type"]=="reconstruction" for v in result["visual_outputs"])


@pytest.mark.parametrize("query,images,expected",[("SAR fusion",[pixels()],"unsupported"),("Measure temporal change",[pixels()],"unsupported"),("Detect clouds",[],"failed")])
def test_missing_requirements(query,images,expected):
    result=run(query,uploaded_images=images)[-1]
    assert result["outcome"]==expected
    assert result["confidence"]==0
    assert result["verified"] is False
    assert "42%" not in result["final_answer"]


def test_registration_failure_abstains_from_change():
    result=run("Measure temporal change",uploaded_images=[pixels(20),pixels(30)])[-1]
    assert "9.2" not in result["final_answer"] and "urban expansion" not in result["final_answer"]
    assert result["confidence"]==0
    assert not any(v["type"]=="change_map" for v in result["visual_outputs"])


@pytest.mark.parametrize("algorithm",["telea","navier_stokes"])
def test_inpainting_preserves_unmasked_pixels_and_provenance(algorithm):
    array=np.random.default_rng(4).integers(0,150,(64,64,3),dtype=np.uint8)
    mask=np.zeros((64,64),np.uint8);mask[20:40,20:40]=255
    result=CPUInpaintingProvider(algorithm=algorithm,radius=3).reconstruct(encode(array),encode(mask),input_provenance=InputProvenance.USER_UPLOAD)
    decoded=np.array(Image.open(io.BytesIO(base64.b64decode(result.output_b64))))
    assert result.success and np.array_equal(decoded[mask==0],array[mask==0])
    assert result.input_provenance==InputProvenance.USER_UPLOAD
    assert result.metadata["radius_px"]==3 and result.metadata["processing_time_ms"]>=0
    assert result.metadata["mask_fraction"]==np.mean(mask>0)


def test_mask_alignment_rejected():
    result=CPUInpaintingProvider().reconstruct(pixels(),encode(np.zeros((12,12),np.uint8)))
    assert not result.success and not result.output_b64


def live(name="bi_temporal_change_detection",**updates):
    return dict(tool_name=name,status="success",confidence=.8,execution_mode=ExecutionMode.LIVE_ALGORITHM,
                input_provenance=InputProvenance.USER_UPLOAD,is_demo=False,result={},**updates)


def test_no_evidence_no_verified_score_and_no_circular_inflation():
    assert compute_evidence_strength([]).evidence_strength==0
    assert compute_evidence_strength([live("image_validation"),live("answer_synthesis")]).evidence_strength==0
    good=live()
    before=compute_evidence_strength([good])
    after=compute_evidence_strength([good,live("confidence_check"),live("evidence_comparison")])
    assert before.evidence_strength==after.evidence_strength
    assert after.breakdown["cross_method_agreement"]["score"]==0
    assert sum(v["weight"] for v in after.breakdown.values())==pytest.approx(1)
    assert sum(v["weight"]*v["score"] for v in after.breakdown.values())==pytest.approx(after.evidence_strength,abs=.001)
    assert compute_evidence_strength([live(evidence_excludable=True)]).evidence_strength==0
    missing=live();missing.pop("input_provenance")
    assert compute_evidence_strength([missing]).evidence_strength==0


def test_photometric_residual_units():
    assert _mean_absolute_intensity_residual(np.zeros((16,16)),np.full((16,16),20))==20


def test_digest_covers_query_pixels_and_answer():
    first=run(uploaded_images=[pixels()])[-1]
    second=run("Detect cloud candidates please",uploaded_images=[pixels(31)])[-1]
    assert first["audit_hash"]!=second["audit_hash"]
    json.dumps(first,allow_nan=False)


def test_live_algorithm_on_demo_is_excluded():
    result=run("Detect clouds",demo_scenario="demo3")[-1]
    assert result["confidence"]==0 and result["outcome"]=="completed_partial"
    assert "Demonstration run" in result["final_answer"]


def test_actual_detector_injects_actual_cpu_repair():
    array=np.full((64,64,3),30,np.uint8);array[:,32:]=240
    events=run(uploaded_images=[encode(array)])
    cloud=next(e for e in events if e["type"]=="tool_done" and e["tool_name"]=="cloud_detection")
    repair=next(e for e in events if e["type"]=="tool_done" and e["tool_name"]=="cloud_reconstruction")
    assert cloud["result"]["cloud_coverage_pct"]>=20
    assert repair["result"]["success"] and repair["algorithm"].startswith("opencv_")
    assert repair["metadata"]["input_pixel_hashes"]==cloud["metadata"]["input_pixel_hashes"]


def test_partial_registration_blocks_numeric_output(monkeypatch):
    from backend.tools.registration import register_images
    array=np.random.default_rng(2).integers(0,150,(64,64,3),dtype=np.uint8)
    result=replace(register_images(array,array),quality=RegistrationQuality.PARTIAL)
    monkeypatch.setattr("backend.tools.change_detector.register_images",lambda *a:result)
    detected=detect_change(encode(array),encode(array))
    assert detected.unreliable_registration and detected.changed_area_pct is None
    assert detected.change_mask_b64 is None


def test_change_mask_is_binary_scientific_pixels(monkeypatch):
    from backend.tools.registration import register_images
    array=np.random.default_rng(3).integers(0,100,(64,64,3),dtype=np.uint8)
    later=array.copy();later[20:40,20:40]=150
    reg=replace(register_images(array,array),registered_image=later)
    monkeypatch.setattr("backend.tools.change_detector.register_images",lambda *a:reg)
    result=detect_change(encode(array),encode(later))
    assert not result.unreliable_registration
    mask=np.array(Image.open(io.BytesIO(base64.b64decode(result.change_mask_b64))))
    assert mask.ndim==2 and set(np.unique(mask)).issubset({0,255})
    assert result.changed_pixel_count==int(np.count_nonzero(mask))
    assert result.changed_area_pct==round(100*np.count_nonzero(mask)/mask.size,2)


def test_demo_pair_preserves_distinct_acquisition_dates():
    from backend.services.input_resolution import resolve_inputs
    _,identities=resolve_inputs(None,"demo1",None,None)
    assert [i.metadata.acquisition_date for i in identities]==["2022-04-21","2022-07-15"]


def test_excluded_registration_cannot_raise_evidence():
    cloud=live("cloud_detection")
    baseline=compute_evidence_strength([cloud])
    excluded=live(evidence_excludable=True,registration_quality=RegistrationQuality.SUCCESS)
    assert compute_evidence_strength([cloud,excluded]).evidence_strength==baseline.evidence_strength


def test_api_sse_retrieval_and_digest_are_consistent():
    import hashlib
    from fastapi.testclient import TestClient
    from backend.main import app
    with TestClient(app) as client:
        response=client.post("/api/analyze",json={"query":"Detect clouds","uploaded_images":[pixels()],"image_metadata":[{"image_id":"local_fixture"}]})
        assert response.status_code==200
        events=[json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
        done=events[-1]
        identity=done["analysis_id"]
        trace=client.get(f"/api/analysis/{identity}/trace").json()
        assert [t["tool_name"] for t in trace["trace"]]==[e["tool_name"] for e in events if e["type"]=="tool_done"]
        assert client.get(f"/api/analysis/{identity}/results").json()==done
        session=client.get(f"/api/analysis/{identity}").json()
        digest=hashlib.sha256(json.dumps(session["audit_manifest"],sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
        assert digest==done["audit_hash"]
        assert done["threshold_policy"]=={"low_evidence":.55,"high_evidence":.75,"research":.60}


def test_cloud_failure_is_failed_not_supported(monkeypatch):
    actual=service.get_tool
    class Failure:
        def timed_run(self,inputs):
            raise ValueError("controlled detector error")
    monkeypatch.setattr(service,"get_tool",lambda name: Failure() if name=="cloud_detection" else actual(name))
    result=run(uploaded_images=[pixels()])[-1]
    assert result["outcome"]=="failed" and result["confidence"]==0
    assert "controlled detector error" in result["final_answer"]


def test_registry_still_has_twelve_tools():
    from backend.tools.specialist_tools import TOOL_REGISTRY
    assert len(TOOL_REGISTRY)==12


def test_semantic_request_cannot_be_fully_answered_by_cloud_check():
    result=run("Detect clouds and classify urban vegetation",uploaded_images=[pixels()])[-1]
    assert result["outcome"]=="completed_partial"
    assert "unsupported" in result["final_answer"]


def test_synthetic_and_simulated_cannot_inflate_live_algorithm_factor():
    candidate=live()
    simulated=live();simulated.update(execution_mode=ExecutionMode.SIMULATED,is_demo=True,confidence=1.0)
    before=compute_evidence_strength([candidate])
    after=compute_evidence_strength([candidate,simulated])
    assert after.breakdown["algorithm_confidence"]["score"]==before.breakdown["algorithm_confidence"]["score"]
    assert after.evidence_strength<=before.evidence_strength


def test_empty_support_summary_abstains():
    from backend.services.grounded_answer import synthesize
    assert synthesize({"task_type":"bi_temporal_change","tool_results":[]})["outcome"]=="abstained"


def test_incompatible_modalities_are_structured():
    result=run("Detect clouds",uploaded_images=[pixels()],image_metadata=[{"image_type":"SAR"}])[-1]
    assert result["outcome"]=="unsupported" and "INCOMPATIBLE_MODALITY" in result["final_answer"]


def test_fully_masked_image_cannot_claim_repair():
    result=CPUInpaintingProvider().reconstruct(pixels(),encode(np.full((64,64),255,np.uint8)))
    assert not result.success and not result.output_b64
    assert "no observed pixels" in result.message
