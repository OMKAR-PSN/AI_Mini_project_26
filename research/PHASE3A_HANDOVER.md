# Phase 3A handover — 22 October 2026

## Delivery status

Implemented an isolated E0–E2 research harness and executed the ten-scene **CPU** pilot. E0 detection and all classical repair outputs are complete. **Qwen inference, E1 accuracy and E2 answer-recovery results have not been executed on a GPU.** The final run is correctly marked partial when requested with `--stage all`, because CUDA is unavailable in the local CPU research environment. No model weights were downloaded, and the expensive full evaluation was not launched.

No React source, FastAPI endpoints, detector thresholds or provider behavior were edited. A SHA-256 comparison against the pre-work snapshot preserved all 62 monitored backend/frontend source files. Existing user changes remain. No commit, push or deployment was made. Root `.gitignore` gained research-specific exclusions; all experimental implementation is under `research/`.

## Implemented components and inventory

| Area | Files | Behavior |
|---|---|---|
| Dataset | `src/satquery_research/datasets.py`, `scene_split.py` | Pinned HF Datasets ingestion, image digests, stable question IDs, scene-disjoint split, saved rosters and numeric review list |
| Clouds | `cloud_generation.py`, `cloud_detection.py` | Pinned published generator, saved opacity/transparency and reference masks; unchanged RGB detector adapter; separate new legacy-style diagnostic |
| Repair | `repair.py` | Provider-backed fixed-radius Telea/NS, oracle Telea and operational CPU auto/radius 10 baseline; exact outside-mask check |
| Inference | `vlm.py` | Shared optional official Qwen loader, float16/SDPA, fixed prompt/preprocessing/greedy decoding, CUDA/memory guard and recorded failures |
| Evaluation | `metrics.py`, `statistics.py`, `analysis.py` | Exact match, answer-form categories, numeric diagnostics, matched transitions, development majority baseline, scene-cluster bootstrap and observed-data-only figures |
| Execution | `manifests.py`, `runner.py`, `__init__.py` | Atomic per-item checkpoints, stable identities, configuration/source/version isolation, frequent CSV export, truthful completion counts |
| Entry points | `scripts/run_pilot.py`, `run_full.py`, `analyze_results.py` | Prepare/CPU/all stages and independent result summarization |
| Configuration | `configs/pilot.yaml`, `full_experiment.yaml` | Ten development scenes/30 questions/one seed; held-out test/all questions/three seeds |
| Colab | `notebooks/SatQuery_E0_E1_E2_Colab.ipynb`, `requirements-colab.txt` | Setup, optional Drive, roster/sanity check, CPU pilot, opt-in GPU pilot, restart instructions and ZIP export |
| Tests | `tests/conftest.py`, `test_masks.py`, `test_repair.py`, `test_split.py`, `test_metrics.py`, `test_reproducibility.py`, `test_runner.py` | 32 tests, including a clearly synthetic test-only end-to-end fixture |
| Documentation | `README.md`, `EXPERIMENT_PROTOCOL.md`, this file, `provenance/ANNOTATION_REVIEW.md`, `real_cloud_annotations/README.md` | Commands, preregistered comparison policy, annotation limitations and separate real-label intake |

Generated assets, downloaded provenance inspection files, datasets and environments are ignored. The saved dataset card is retained in `provenance/dataset_card.md`. No real-cloud labels were fabricated.

## Provenance and inspected contracts

- Dataset: `dmarsili/RSVQA-LR-2k`, revision `35de41f26170edda2ccc4f88c0f62f641bb9e1f1`. Actual split `validation`; actual columns `image, question, answer`; 2,000 rows,100 unique RGB images, all 256×256. The card attributes this subset to RSVQA-LR validation and declares CC-BY-4.0. Original RSVQA attribution and upstream links are in README.
- Dataset contains no native question-ID column. Saved IDs use pinned revision:split:row index; native IDs explicitly remain absent. New roster; no historical pilot CSV was found. No claim of reproducing the previous sample.
- Development/test split:20/80 scenes,426/1,574 questions. Fixed seeds are in YAML. Pilot:10 development scenes,30 questions;20 yes/no and10 numeric, no categorical examples. Entire subset:1,368 yes/no,603 numeric,29 categorical. Categories are answer-form strata, not recovered semantic question types.
- Generator: SatelliteCloudGenerator `d0787cbdc1b39a7976f89aa085f1430f3207eda6`. Inspected source and usage notebook before using `add_cloud(..., return_cloud=True)`. Mean RGB opacity≥0.20 defines the binary reference, with14-step approximate coverage search. Shadows disabled and explicitly unavailable. Thin contamination below the reference threshold is possible. The same fixed noise seed is reused across scenes/levels; this pilot does not measure broad cloud-shape variability.
- Detector: unchanged brightness>0.65, whiteness>0.70, opening radius 3, closing radius 5. RGB, not HSV. Runtime/research evidence thresholds0.55/0.60 remain separate and untouched.
- Repair: radius 3 for fixed Telea predicted, NS predicted and Telea reference; CPU baseline radius 10 with NS above predicted fraction0.30. Reference repair is diagnostic, not an operational upper bound.
- Model/processor: `Qwen/Qwen2.5-VL-3B-Instruct`, revision `66285546d2b821cf421d4f5eb2576359d3770cd3`. Official Transformers4.51.3 API; slow processor, float16, SDPA, batch1,65536 min/max pixels (actual rounded grid saved), greedy decoding,24 max new tokens. Same prompt and preprocessing for all conditions. This is research-only, not integrated into FastAPI.

## Verified pilot outputs

Final source/version identity: **`d3b55fc1b59f7eb2a3f3`**.

Local directory: `research/outputs/d3b55fc1b59f7eb2a3f3/`.
Older preparation/development-run folders are retained separately and are not the final source identity.

- 70/70 scene-seed-level conditions completed:10 scenes ×7 target levels ×1 seed.
- 280/280 repairs completed across four variants.
- 0 model predictions;1,080 would be expected for the full configured GPU pilot.
- No CPU processing failures. Missing CUDA produces an explicit model-loading error; retry attempts remain in the historical error log.
- Verified **all 70** opacity/reference conversions and transparency complements, plus **all 280** repair identities, common cloudy inputs, mask digests and exact outside-mask pixel preservation. See `artifact_verification.json`.
- Online resumption preserved all 350 E0/repair checkpoint records byte-for-byte (44.69s including dataset preparation and plotting); see `resumption_verification.json`. Separate end-to-end test also confirms that completed predictions are not duplicated.

Pooled pixel metrics from the final pilot:

| Target cloud coverage | Precision | Recall | F1 |
|---:|---:|---:|---:|
| 0% | Undefined | Undefined | Undefined |
| 10% | 0.9994 | 0.4950 | 0.6621 |
| 20% | 1.0000 | 0.5397 | 0.7011 |
| 30% | 0.9996 | 0.5707 | 0.7265 |
| 40% | 0.9991 | 0.6165 | 0.7625 |
| 50% | 0.9997 | 0.6138 | 0.7606 |
| 60% | 0.9998 | 0.5946 | 0.7457 |

The ten clean conditions have zero false-positive coverage and both masks empty; undefined F1 is not a detector failure. Achieved coverage differs from target by at most about 0.000074 in fraction in these conditions. Precision is high but the detector misses substantial reference-mask area. These are descriptive measurements under one synthetic opacity policy and one fixed cloud seed, **not final natural-cloud validity evidence**.

## Output schemas and figures

| Output | Essential fields/content |
|---|---|
| `experiment_manifest.json`, `identity.json` | Run/config hash, source hashes, Git commit/dirty status, pins, versions, hardware, prompt/processor/generation policies, seeds, timing, expected/completed counts, errors and file list |
| `roster_all.csv`, `roster_selected.csv`, `dataset_audit.json` | Full/selected scene/question IDs, original row index, original answer, category, partition, image identity/path and actual dataset schema |
| `e0_detector_metrics.csv` | Scene/seed/partition/generator, target/achieved/measured fraction, TP/FP/FN/TN, precision/recall/F1/IoU, FP coverage/FPR, both-empty flag, mask/image/opacity paths and digests, timings |
| `e0_summary.csv` | Pooled confusion counts and metrics by target stratum, achieved coverage, undefined counts, number of scenes/conditions |
| `repair_outputs.csv` | Variant, actual algorithm, radius, mask source/digest/fraction, common cloudy digest, output identity/path, empty-mask flag and repair latency |
| `predictions.csv` (only with real inference) | Scene/question/seed/level/condition, raw/normalized prediction, original/normalized answer, exact match, numeric error/parseability, preprocessing grid, timing and peak allocated/reserved GPU memory |
| VQA summaries (only with real inference) | Category accuracy/CIs, numeric MAE/parseability, paired comparisons, recovered/damaged counts, explicit clean→cloudy transitions, prediction changes, unmatched counts and development majority baseline |
| `execution_errors.csv`, `records/` | Error history plus atomic completed-item JSON checkpoints; failed items may retry |
| `annotation_review.csv` |135 flagged large numeric labels, all retained; visual review notes separately documented |

Five actual pilot PDFs and PNG previews were generated: detection quality, coverage scatter, representative image gallery, false-positive case and false-negative case. PDFs were rendered with Poppler and visually inspected; labels are readable, aspect ratios are preserved and synthetic/estimated images are distinguished. VQA accuracy, repair-difference and recovered/damaged plotting paths are implemented and exercised by synthetic unit-test fixtures **only**; no experimental VQA figures are fabricated.

## Validation

- Research suite: **32 passed** (final full-suite invocation16.67s).
- Existing backend suite: **80 passed** (3.70s).
- Python compilation: passed for source/scripts/tests.
- Notebook: nbformat schema and every Python code cell compile successfully.
- `git diff --check`: passed; existing frontend files emitted only Git line-ending notices.
- Preservation: all 62 monitored application source files unchanged from the pre-work hash snapshot.
- Real-pilot scientific-array verification:70 cloud/reference pairs and280 repair outputs checked.
- Final figure rendering/visual review: five PDFs.

The first test invocation encountered sandbox temporary-directory permissions; using a workspace-local pytest base directory resolved it. This was not an algorithm test failure. Colab installation and actual T4/Qwen inference have **not** been executed here. The pinned Colab stack differs from the locally measured CPU stack; each run records its true package versions and gets its own identity.

## Resource assessment

Local hardware inventory: NVIDIA GeForce RTX4050 Laptop GPU,6141MiB VRAM. The isolated local research environment deliberately uses PyTorch2.7.1+cpu/torchvision0.22.1+cpu; no CUDA inference occurred. Model metadata reports3,754,622,976 parameters: two-byte weights alone need about 7.51GB decimal, exceeding this laptop GPU before activations/KV cache. The loader requires10GiB free; a16GB T4 is the intended target, but actual fit and latency remain unmeasured. No unsupported quantization fallback was introduced.

Final pilot first-pass elapsed time:70.10s including preparation, file writes and plots. Measured generation/detection total16.76s; measured repairs18.90s. Approximately85.8MB of local outputs, including all 100 original images and70 generated conditions; generated image arrays account for about 71.4MB. These timings use one CPU thread and exclude model inference.

Full CPU schedule:80 scenes ×3 seeds ×7 levels=1,680 conditions and6,720 repairs. Linear scaling of measured computational work suggests about 14 minutes, plus I/O/plots/setup; this is an estimate, not a full-run measurement. Similar image storage is roughly1.7GB before prediction checkpoints and other overhead. Full model schedule:1,574 questions ×(1 clean +3×7×5 conditions)=**166,844 model calls**. No defensible GPU time estimate is available before a real measured pilot; use observed mean/p95 latency and peak memory, not guessed throughput. Do not launch the full model evaluation automatically.

## Known limitations and remaining verification

1. Real Qwen predictions, real GPU latency/memory and clean-session Colab dependency execution are unverified. The harness is implemented; E1/E2 scientific execution remains pending.
2. The pilot has only 10 development scenes, one cloud seed and no categorical-answer examples. It cannot establish final accuracy or a repair crossover.
3. Generated masks describe an explicit opacity policy, not independently annotated natural clouds. Shadows and realistic multispectral radiometry are not evaluated.
4. Large numerical labels cannot be verified visually at this resolution. All labels are retained; see annotation review. No spatial-overlap metadata is available to prove geographic independence beyond identical-image grouping.
5. Fixed-radius 3 versus auto/radius 10 compares different radius policies; the radius 3 Telea/NS pair isolates algorithm differences. Oracle masks do not guarantee higher VQA accuracy.
6. Bootstrap intervals retain all fixed seeds inside scene clusters. Per-level/method intervals are exploratory, pointwise and unadjusted for multiplicity. No statistically supported crossover is claimed.
7. Completed items resume atomically; an interrupted uncheckpointed item may repeat. Only one process should write a given run directory. Missing/corrupt artifacts raise errors rather than being silently accepted.
8. The original legacy opaque generator was unavailable. The separate replacement is explicitly legacy-style, not reproduction of an old implementation.
9. Numerical GPU reproducibility across hardware/kernels is not guaranteed by greedy decoding. All versions/hardware must accompany comparisons.
10. Dataset preparation currently reopens the pinned HF dataset on resume and may require Hub metadata access even with cached image data. An offline-only resume attempt failed before processing; completed checkpoints were preserved and online resume was used. Offline dataset rehydration is not implemented.

No known failing CPU tests remain. These limitations must stay visible in any manuscript or demo.

## Claims currently supported and unsupported

Supported: the existing RGB detector and CPU provider can be evaluated reproducibly against this declared synthetic protocol; ten-scene CPU results, input pairing, mask conversion and pixel-preservation checks are recorded. The detector underestimates the selected reference opacity coverage in this pilot.

Unsupported: repair improves VQA; calibrated uncertainty or a safe abstention threshold; a statistically supported crossover; true reconstruction of hidden objects; natural-cloud generalization; trained SAR fusion; Qwen integrated into the operational app; production readiness or scientific validation.

## Exact next commands

From the repository root, the already-created local environment:

```powershell
research/.venv/Scripts/python.exe -m pytest research/tests -q --basetemp=research/.cache/pytest-team-check
research/.venv/Scripts/python.exe research/scripts/analyze_results.py research/outputs/d3b55fc1b59f7eb2a3f3
research/.venv/Scripts/python.exe research/scripts/run_pilot.py --stage cpu
```

For Colab: upload `notebooks/SatQuery_E0_E1_E2_Colab.ipynb`. Upload/access a repository checkout containing these uncommitted files, or set its repository URL and exact revision after the team independently publishes them. No push was performed here. Choose a T4 runtime, optionally mount Drive, and follow the notebook in order. Installation and execution commands are:

```bash
python -m pip install -r research/requirements-colab.txt
python -m pytest research/tests -q
python research/scripts/run_pilot.py --stage prepare
python research/scripts/run_pilot.py --stage cpu
# Review masks/roster, then explicitly enable a GPU pilot:
python research/scripts/run_pilot.py --stage all --output-root /content/drive/MyDrive/SatQuery-research
```

After pilot review and explicit authorization only:

```bash
python research/scripts/run_full.py --stage all --output-root /content/drive/MyDrive/SatQuery-research
```

Use the same output root/config/source/package versions when resuming. After a Colab restart rerun repository-access, Drive and configuration cells; reinstall if necessary before imports. The notebook exports the selected run directory as ZIP. Do not tune on the held-out test results.

## Proposed E3/E4 extensions

**E3 — Natural-cloud external validity:** collect licensed observations with independent cloud/shadow annotations, double-review ambiguous masks, record geographic/acquisition metadata, and define a geographically held-out test. Evaluate detector failure modes and radiometric domain shift before integrating learned cloud removal. Keep synthetic and real-label results separate.

**E4 — Selective answering and learned repair:** after actual E1/E2 inference, fit an abstention/repair policy on development data only; preregister a held-out risk–coverage evaluation, simultaneous per-level intervals and multiplicity policy. Compare frozen learned reconstruction/model checkpoints with classical baselines using identical questions and inputs. Investigate label provenance, model pretraining contamination and alternative VLMs. Treat any future SAR/diffusion integration as a new, separately validated experiment.
