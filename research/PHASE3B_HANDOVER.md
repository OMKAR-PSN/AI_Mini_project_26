# Phase 3B handover — 26 October 2026

Analyzed the supplied Colab ZIP read-only, without downloading datasets/weights or running Qwen. Run b95a0ad533d1b941d95e contains 10 development scenes, 30 questions, one cloud seed, 70 conditions, 280 repairs and 1,080 predictions. Configuration, source identity (allowing documented CRLF/LF differences), complete pairing, checkpoints, image/mask digests, unmasked pixels and recomputed summaries passed integrity checks.

## Findings

Clean exact match is 43.33%. Across nonzero cloud levels (180 repeated question-conditions), direct cloudy inference reaches 49.44%. Predicted-mask Telea: 47.22%; predicted-mask NS: 47.78%; reference-mask Telea: 43.89%; CPU auto: 44.44%. CPU auto recovered 3 answers and damaged 12: −5.00 percentage points, nominal scene-bootstrap 95% interval [−11.11, −0.56]. These are exploratory development results, not held-out confirmation. Two questions account for 8 of the 12 damage events. Reference masks do not form a guaranteed performance upper bound. Radius effects are confounded with the auto algorithm switch.

The ten numeric questions have zero exact matches across conditions; secondary standalone number-word/decimal normalization recovers none. Original labels are retained. A reference count of 409 buildings cannot be independently validated from this low-resolution RGB patch. Audit original annotation semantics and geographic extent before any exclusion. Answer-form categories are reporting strata, not operational decision features.

## Policies and uncertainty

P0 directly answers; P1 always uses CPU auto. P2 selects from detector-fraction thresholds 0.10–0.50 using leave-one-scene-out development validation. P3 selects direct/Telea/NS per fixed measured-fraction bins, also leave-one-scene-out. P4 answers only on direct/auto agreement. P5 answers directly below/equal measured fraction0.20 and checks agreement above it. No oracle masks or ground-truth correctness enter decision functions.

| Policy | Coverage | Selective accuracy | VQA calls per decision |
|---|---:|---:|---:|
| P0 | 100% | 49.44% | 1 |
| P1 | 100% | 44.44% | 1 |
| P2 | 100% | 48.33% | 1 |
| P3 | 100% | 48.33% | 1 |
| P4 | 81.11% | 52.74% | 2 |
| P5 | 90.00% | 51.85% | 1.5 |

P4 has 69 wrong agreements among146 agreements. It withholds12 previously correct and22 incorrect direct answers. P5 withholds5 correct and13 incorrect answers. Neither establishes reliably safe answering. Estimated serial latency is approximately220,474,301,251,694 and503ms for P0–P5 respectively, using recorded detector/repair/inference durations without amortizing shared image work; these are estimates, not measured policy executions.

Scene bootstrap retains all questions/levels/seeds in each resampled scene. OOF intervals condition on fold-selected rules and omit full selection-process uncertainty. With only10 scenes, conclusions are unstable. P2 chooses0.30 in7 folds and0.50 in3 folds. No selective-repair policy beats direct inference here. P5 sensitivity has partial risk–coverage area0.09170 over observed coverage[0.81111,1.0]; this is not full-domain AURC. No observed gate attains risk≤0.40; no assessed gate has an upper95% risk bound≤0.50.

## Recommendation and manuscript

Retain P0 as the research baseline. Freeze P5's existing0.20 rule only as an exploratory comparator for future held-out evaluation; do not deploy it or select a new rule from test results. Disagreement may justify deferring an answer, but agreement is not correctness and no low-risk guarantee is established. Real clouds, annotation review, multiple seeds and more scenes are required. Repeated cloud exposures are not independent observations. No causal claim about repair radius, missed task-critical pixels or beneficial clouds is supported.

Suggested paper assets: repair-comparison table; policy coverage/risk/cost table; scene performance, paired differences, recovered/damaged, false-negative association and risk–coverage figures; six qualitative cases including recovery and stable-answer counterexamples. The concise E1/E2 Results draft is analysis/phase3b/E1_E2_PRELIMINARY_RESULTS.md. Established numbering remains E0 cloud detection, E1 cloud-affected VQA, E2 repair comparison, E3 bi-temporal change, E4 abstention/risk–coverage, E5 tool-injection ablation.

## Reproduction and validation

From the repository root:

```powershell
research/.venv/Scripts/python.exe research/scripts/analyze_phase3b.py --results "C:\Users\Omkar\Downloads\b95a0ad533d1b941d95e-20261025T181807Z-1-001.zip" --output research/analysis/phase3b
research/.venv/Scripts/python.exe -m pytest research/tests -q --basetemp=research/.cache/pytest-phase3b-check
```

The CLI also accepts an extracted run directory and --integrity-only. Integrity failure blocks policy selection. Generated CSVs, individual PDF/PNG figures and the combined phase3b_figures.pdf remain local and can be regenerated from the input ZIP. The source archive is not committed. All56 research tests passed during this analysis. No operational controller policy, original prediction or label was changed. Final source-code review and updated frontend validation are separate from these scientific results.
