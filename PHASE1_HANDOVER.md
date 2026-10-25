# SatQuery AI — Phase 1 handover

## 1. Summary

Repaired the existing React/FastAPI pipeline without adding models, dependencies, or external service calls. No commit, push, deployment, reset, or checkout was performed. Existing unrelated changes were retained.

Baseline reproduced: 48 tests passed, two provenance-penalty tests failed; 12 tools remain registered. The original dynamic repair loop reassigned a list without changing its active iterator. Canned synthesis and disabled provenance penalties were present.

## 2. Before and after

| Area | Before | After |
|---|---|---|
| Inputs | A single upload could be replaced by default demo pixels | Explicit input resolution; actual image count, dimensions, identity, source metadata and pixel digest; uploads override demo selection |
| Missing inputs | Implicit demonstration fallback | Structured failed/unsupported completion with limitations |
| Temporal metadata | First acquisition date reused for both dates | Separate registry dates retained; missing declared demo files fail instead of generating replacements |
| Cloud repair | Announced insertion could fail to execute; first image only | Deterministic per-image queue; both dates assessed; exact measured fraction >= 0.20 triggers one repair per image |
| Reconstruction | Annotation changed scientific pixels; output unused downstream | Raw output preserved, original retained, correct mask passed, reconstructed pixels consumed downstream |
| Provider | Environment could select remote/precomputed reconstruction | Phase 1 pipeline explicitly uses local CPU inpainting |
| Failed repair | Could still imply completed reconstruction | Failure recorded; original retained; partial/failed outcome; no reconstruction output claimed |
| Answers | Canned urban/vegetation/distance/SAR statistics | Deterministic summaries of actual computations plus missing capabilities and failure reasons |
| Scoring | Missing provenance, bookkeeping and absence of disagreement inflated score | Penalties restored; bookkeeping excluded; eligibility gates; no independent agreement credit; absent supporting evidence forces zero |
| Registration | Intensity residual labelled spatial pixel error | Renamed intensity residual (0–255 levels), conservative screening only; partial/failed registration blocks numerical change |
| Change after repair | Estimated pixels could be interpreted as observations | Diagnostic execution allowed, but change percentage withheld whenever repair was required |
| Audit | Empty retrieved trace, narrow hash | Executed trace and SSE event records; canonical audit manifest and SHA-256 digest covering inputs, masks/results, plan, policy and outcome |
| UI | Hardcoded cross-modal scores, verified/tamper-proof labels, inert review action | Outcome and limitations displayed; heuristic score language; no verification/authenticity claim or fake review action |

Telea and Navier–Stokes are configurable through `CPUInpaintingProvider(algorithm=..., radius=...)`. The existing automatic choice and default radius 10 remain. Both preserve unmasked pixels. Shape-mismatched masks and fully masked images fail honestly. Reconstruction metadata records algorithm, radius, fraction and duration. Scientific change masks are binary and unannotated.

## 3. Exact files changed in this phase

The list below excludes pre-existing changes in other files. New source files are the two service helpers and regression-test module; this handover is also new. The production build generated ignored `satquery-ai/dist` assets and normal TypeScript build cache files.

- [backend/controller/central_controller.py](C:/Users/Omkar/Desktop/SIH_26/backend/controller/central_controller.py)
- [backend/main.py](C:/Users/Omkar/Desktop/SIH_26/backend/main.py)
- [backend/providers/base.py](C:/Users/Omkar/Desktop/SIH_26/backend/providers/base.py)
- [backend/providers/cpu_provider.py](C:/Users/Omkar/Desktop/SIH_26/backend/providers/cpu_provider.py)
- [backend/schemas/models.py](C:/Users/Omkar/Desktop/SIH_26/backend/schemas/models.py)
- [backend/services/analysis_service.py](C:/Users/Omkar/Desktop/SIH_26/backend/services/analysis_service.py)
- [backend/services/input_resolution.py](C:/Users/Omkar/Desktop/SIH_26/backend/services/input_resolution.py)
- [backend/services/grounded_answer.py](C:/Users/Omkar/Desktop/SIH_26/backend/services/grounded_answer.py)
- [backend/solution_space/strategy_registry.py](C:/Users/Omkar/Desktop/SIH_26/backend/solution_space/strategy_registry.py)
- [backend/tools/base_tool.py](C:/Users/Omkar/Desktop/SIH_26/backend/tools/base_tool.py)
- [backend/tools/change_detector.py](C:/Users/Omkar/Desktop/SIH_26/backend/tools/change_detector.py)
- [backend/tools/cloud_detector.py](C:/Users/Omkar/Desktop/SIH_26/backend/tools/cloud_detector.py)
- [backend/tools/evidence.py](C:/Users/Omkar/Desktop/SIH_26/backend/tools/evidence.py)
- [backend/tools/registration.py](C:/Users/Omkar/Desktop/SIH_26/backend/tools/registration.py)
- [backend/tools/scene_loader.py](C:/Users/Omkar/Desktop/SIH_26/backend/tools/scene_loader.py)
- [backend/tools/specialist_tools.py](C:/Users/Omkar/Desktop/SIH_26/backend/tools/specialist_tools.py)
- [satquery-ai/src/api/client.ts](C:/Users/Omkar/Desktop/SIH_26/satquery-ai/src/api/client.ts)
- [satquery-ai/src/types/index.ts](C:/Users/Omkar/Desktop/SIH_26/satquery-ai/src/types/index.ts)
- [satquery-ai/src/pages/AnalysisPage.tsx](C:/Users/Omkar/Desktop/SIH_26/satquery-ai/src/pages/AnalysisPage.tsx)
- [satquery-ai/src/components/analysis/FinalAnswerCard.tsx](C:/Users/Omkar/Desktop/SIH_26/satquery-ai/src/components/analysis/FinalAnswerCard.tsx)
- [satquery-ai/src/components/evidence/EvidencePanel.tsx](C:/Users/Omkar/Desktop/SIH_26/satquery-ai/src/components/evidence/EvidencePanel.tsx)
- [satquery-ai/src/components/evidence/EvidenceTrailModal.tsx](C:/Users/Omkar/Desktop/SIH_26/satquery-ai/src/components/evidence/EvidenceTrailModal.tsx)
- [satquery-ai/src/components/trace/TracePanel.tsx](C:/Users/Omkar/Desktop/SIH_26/satquery-ai/src/components/trace/TracePanel.tsx)
- [satquery-ai/src/components/query/SceneSelector.tsx](C:/Users/Omkar/Desktop/SIH_26/satquery-ai/src/components/query/SceneSelector.tsx)
- [satquery-ai/src/components/visualization/VisualOutputs.tsx](C:/Users/Omkar/Desktop/SIH_26/satquery-ai/src/components/visualization/VisualOutputs.tsx)
- [satquery-ai/src/utils/reportGenerator.ts](C:/Users/Omkar/Desktop/SIH_26/satquery-ai/src/utils/reportGenerator.ts)
- [tests/test_pipeline_correctness.py](C:/Users/Omkar/Desktop/SIH_26/tests/test_pipeline_correctness.py)
- [PHASE1_HANDOVER.md](C:/Users/Omkar/Desktop/SIH_26/PHASE1_HANDOVER.md)

## 4. Tests added

`tests/test_pipeline_correctness.py` adds 30 collected test cases. Existing test files were not rewritten to relax expectations.

Coverage includes upload-over-demo identity, missing/incompatible inputs, original-image preservation, below/at/above 20% thresholds, actual detector/CPU execution, both-date repair, downstream repaired pixels, repair failure, fully masked inputs, both inpainting algorithms, mask shape and unchanged unmasked pixels, missing SAR, invalid/partial registration, raw binary change masks, correct acquisition dates, demo/simulated exclusion, missing evidence, circular scoring, excluded registration, actual weight arithmetic, semantic-request limitations, abstention, tool-registry preservation, SSE/retrieval parity and digest recomputation.

External HTTP requests are blocked in the new test fixture. Controlled local tools/fixtures exercise failure and boundary cases. No production imagery, paid GPU, or remote provider was invoked.

## 5. Commands and results

From repository root:

- `python -B -m pytest tests/ -q -p no:cacheprovider` — **80 passed** (baseline: 48 passed, 2 failed).
- `git diff --check` — passed; Git printed existing CRLF conversion notices only.

From `satquery-ai`:

- `node node_modules/typescript/bin/tsc -p tsconfig.app.json --noEmit --incremental false` — passed during development.
- `npm run build` — passed, including TypeScript project checks and Vite production bundling. Vite warns about a minified chunk larger than 500 kB.
- `npm run lint` — exit 0, **13 warnings**, down from the prior audit's 15. Remaining warnings concern unused symbols and existing React effect dependencies/state handling.

Browser interactions and the exported PDF were not manually rendered/visually reviewed. PDF text now uses honest evidence labels and paginates answer limitations; TypeScript/build checks cover compilation, not visual layout.

## 6. Scientific limitations

- RGB cloud detection uses brightness and whiteness plus morphology, not HSV or a learned detector. Bright terrain/roofs can be false positives; thin clouds and shadows may be missed.
- CPU inpainting estimates pixels. It does not recover measured ground truth or implement EMRDM, diffusion, SAR-assisted or temporal reconstruction.
- Registration screening retains the existing 5/15 intensity-level thresholds. These are not spatial accuracy guarantees. Genuine changes and illumination differences can raise the residual.
- Change output is a raster intensity-change diagnostic, not land-cover change, geographic area, flood mapping or distance. The legacy `changed_area_pct` field remains for compatibility; final answers explicitly state raster-pixel semantics.
- Georeferencing, valid-overlap/nodata/cloud exclusion and a validated clear-pixel comparison protocol remain incomplete. Quantitative change is withheld for repaired/repair-failed pairs rather than counting estimated pixels as observations.
- Submitted metadata is recorded, not independently authenticated. Unknown date/resolution/cloud values remain unknown until available/computed. Existing catalogue-preview cropping and geospatial accuracy limitations are not repaired in this phase.
- Evidence is heuristic, not calibrated probability. No independent same-claim verification exists; `verified` remains false and independent evidence is insufficient.
- Demo runs can execute actual algorithms but remain explicitly demonstrations and excluded from scientific evaluation.

## 7. Compatibility and operational risks

- Session `status`/completion `outcome` now use `completed_supported`, `completed_partial`, `abstained`, `unsupported`, or `failed`; callers expecting only `completed` must adapt. SSE still terminates with an event whose `type` is `completed`.
- Input is required; missing input no longer silently runs demo1. `image_ids` alone cannot resolve pixels because upload persistence does not exist.
- `/api/analyze` accepts aligned `image_metadata` entries alongside `uploaded_images`. Actual processed image metadata is returned in completion `inputs`.
- Registration fields renamed: `mean_alignment_error_px` to `mean_absolute_intensity_residual`, and `registration_error_px` to `registration_intensity_residual`.
- Metadata resolution/cloud fields may be null. The UI handles unknown values.
- A tool may execute once per image. Clients must key trace rows by `step_index`, not tool name.
- `/results` returns the saved completion payload; `/trace` returns actual trace steps plus recorded events. Full session retrieval includes the canonical `audit_manifest`.
- Hashes are tamper-evident digests of stored records, not digital signatures, authentication or tamper-proof storage. Runtime durations are covered, so identical reruns need not have identical digests.
- The session store remains in-process/in-memory, with no restart persistence or multi-worker sharing. Existing authentication, upload resource limits and durable background-job concerns remain outside these repairs.
- Frontend history replay now loads the saved query/scenario for explicit resubmission instead of executing against stale selected state. Scenario changes during a run are ignored; selecting a demo clears fetched imagery.

## 8. Still simulated or unsupported

The registry still contains legacy simulated scene understanding, object detection, land-cover classification and spatial reasoning tools; the corrected analysis pipeline does not execute those simulations as scientific analysis. SAR fusion is unsupported even if SAR-labelled pixels are supplied. No learned VQA, LLM, generative reconstruction, analyst-review service, calibrated confidence or independent secondary analysis was added. Remote/precomputed providers remain in the codebase but are not selected by this Phase 1 analysis workflow. Legacy Home/System marketing/static demonstration content was not broadly redesigned.

## 9. Phase 2 contract

Phase 2 can use completion `outcome`, `limitations`, `inputs`, `threshold_policy`, `score_kind`, `verified`, and `audit_hash`, plus actual `step_index` trace identity and per-tool provenance/status/warnings. Do not infer success, reconstruction or verification merely from a completed SSE stream or a high score.

The runtime low-evidence threshold remains **0.55**; high category begins at **0.75**. The research threshold remains separately reported as **0.60**. No thresholds were tuned against experimental outcomes. Main result labels use backend categories/policy.

Phase 2 should make partial/unsupported/failed states prominent, distinguish original/estimated/display assets, present missing metadata honestly, and use the actual executed chain and evidence breakdown. Existing static capability copy and accessibility/browser/PDF visual validation still need attention.

## 10. Decisions requiring approval

None block these Phase 1 repairs. Future scientific work needs an approved geospatial/clear-pixel comparison protocol, independent validation data and calibration policy before enabling stronger change or verification claims. Remote provider re-enablement, learned models, persistence infrastructure and broader UI redesign are separate work.
