# Prospective experiment protocol

## Dataset and unit of analysis

Use `dmarsili/RSVQA-LR-2k`, revision `35de41f26170edda2ccc4f88c0f62f641bb9e1f1`, validation split. Card attributes the subset to RSVQA-LR validation and declares CC-BY-4.0; retain original RSVQA attribution. Inspect actual columns/counts at runtime. Image SHA-256 includes RGB array shape/dtype/bytes; identical images share a scene. No native question IDs were advertised: use native IDs if available, otherwise preserve revision:split:row index and original row index. Digest grouping cannot detect overlapping but nonidentical geographical patches; absent geospatial metadata limits spatial independence claims.

Split unique image identities 20% development / 80% test, seed 26167. Pilot samples 10 development scenes and 3 uniformly chosen questions per scene, seed 20261021. No category/difficulty filtering. No previous roster was found; this is a new roster. Development majority labels are fitted on all development rows only, with lexical tie-breaking. They are descriptive baselines, not a new model. Test labels never select preprocessing, thresholds, radius or prompts.

Question categories are **answer-form strata**, since no question-type column is supplied: yes/no; strict signed decimal; categorical. They do not necessarily match original RSVQA semantic question types. Preserve all original answers. Flag absolute numerical labels ≥100 for visual review, without exclusion or correction. Low-resolution patch inspection alone cannot establish an object count; annotations may reflect vector-map semantics and scale. Any later exclusion policy must be documented before held-out evaluation.

## Synthetic clouds

Primary: SatelliteCloudGenerator revision `d0787cbdc1b39a7976f89aa085f1430f3207eda6`. Inspected `add_cloud(..., return_cloud=True)` yields image and BCHW continuous opacity. Retain mean RGB opacity and its complement as NPY; threshold opacity ≥0.20 into H×W uint8 0/255 reference masks. Mean-channel conversion is explicit, not a claim of natural segmentation ground truth. Parameters disable channel shifts, offsets and global blur; use max=1, min=0, Perlin noise and published cloud-color mixing. Call `add_cloud` only: shadows are not generated, and no shadow label is invented.

Fit `clear_threshold` over 14 deterministic evaluations, holding the noise seed fixed; retain the closest achieved coverage, without rejecting difficult cases. Targets: 0,.1,.2,.3,.4,.5,.6. Target zero is exactly the original with zero opacity. Thin opacity below 0.20 can contaminate pixels outside the evaluation/repair mask. Original arrays remain unmodified. Full evaluation seeds 101,202,303; pilot uses 101 only. Claims condition on these fixed cloud realizations, not all possible weather. Configurable seeds support sensitivity analysis.

The original historical white-mask generator was not found. `legacy_style_opaque` is an explicitly **new legacy-style sanity baseline**, not reproduction of the earlier generator and not physically realistic. To run it, copy YAML and change only generator.name, preserving a separately hashed output directory. Never pool its results with published-generator runs.

## E0

Reuse unchanged RGB detector: brightness >0.65, whiteness >0.70, morphology opening disk radius 3, closing radius 5. It is not HSV. Operational reconstruction threshold remains20%; runtime evidence0.55 and research evidence0.60 are unrelated to these masks/VQA accuracy and unchanged.

Per condition count TP/FP/FN/TN; precision=TP/(TP+FP), recall=TP/(TP+FN), F1=2TP/(2TP+FP+FN), IoU=TP/(TP+FP+FN). Undefined denominators are null. Both-empty F1/IoU is undefined, explicitly flagged rather than reported as detector failure. False-positive coverage=FP/all pixels; FPR=FP/true negative class pixels. Summaries pool confusion counts across scenes/seeds and retain undefined counts. Clean FP is the target-zero stratum. Figures use achieved coverage; requested coverage is never substituted silently.

## E1/E2

Qwen2.5-VL-3B-Instruct revision `66285546d2b821cf421d4f5eb2576359d3770cd3`; processor same revision, slow mode. Transformers4.51.3 official class, float16, SDPA, one CUDA device, batch1, no quantization assumption. Require10GiB free before loading; T4 16GB is intended but must be measured. Min/max image pixels65536; actual model grid saved (Qwen rounds to patch alignment). Shared short-answer prompt; greedy decoding, beam1, max24 new tokens, cache enabled, seed26167. Exact same settings for every condition. Deterministic decoding does not guarantee bitwise cross-hardware kernels. Record all versions/hardware; no Qwen integration into the application.

Clean predictions computed once/question. Cloudy and four repaired conditions use identical saved cloudy input and matching scene/question/seed/level. Fixed-radius 3 Telea predicted, radius 3 Navier–Stokes predicted, radius 3 Telea reference; additional CPU-provider baseline auto/radius 10 (NS when predicted fraction >.30, otherwise Telea). Reference repair is diagnostic, not deployable or a guaranteed upper bound. Empty masks are explicit no-ops, full masks fail; do not alter unmasked pixels. Inpainted content is estimated, not recovery of true hidden objects.

Primary exact match normalizes NFKC, case, surrounding/collapsed whitespace and terminal .!?. No substring answer extraction, synonym matching, numeric tolerance or number-word conversion. Numeric MAE is secondary on parseable outputs, with denominator/parseability reported. `2.0` versus `2` remains an exact-match error even if numeric error is0.

## Statistical estimand and decision rule

Primary comparison: CPU auto predicted minus cloudy accuracy, across all nonzero levels, on held-out test. Bootstrap whole scenes with replacement, retaining every selected question, level and **all three fixed seeds** inside each sampled scene. Compute micro question-condition accuracy in each resample (unequal question counts retain their original weights). 2,000 replicates, seed314159, percentile95% CI. Seeds are not extra independent scenes; balanced repeated seeds are averaged through their equal record weights. One scene gives no interval; fewer than20 warns of instability.

Prospective evidence of average benefit requires complete matched held-out data, all three configured seeds, and the primary lower CI>0. Positive point estimate alone is insufficient. A dataset subset and synthetic clouds cannot establish operational benefit, scientific verification or natural-cloud generalization. Individual levels, algorithms, answer strata and recovered/damaged counts are secondary/exploratory; their pointwise intervals have no multiple-comparison correction. **No confirmatory crossover is inferred**. Report no supported crossover unless a later preregistered simultaneous interval procedure establishes one. Do not retrofit a selective-answer threshold to the test set.

Failed inferences remain logged; unmatched comparisons are counted, never filled in. Available-pair summaries are exploratory if incomplete. Expected/completed counts are in the manifest. Recovered=cloudy wrong→repaired correct; damaged=cloudy correct→repaired wrong. Clean→cloudy transitions and prediction changes use the same pairing. Image similarity cannot replace VQA performance.

## Reproducibility and operational boundaries

Atomic per-item JSON completion followed by CSV snapshots; interrupted uncheckpointed work can repeat, completed work does not. Source/config/version fingerprints separate incompatible runs. Failed items retry on next invocation; historical errors remain an append-only log. One writer per output directory. No automatic full evaluation. No credentials, production APIs, learned SAR fusion or calibrated evidence claims. Dataset and generator are public research dependencies.
