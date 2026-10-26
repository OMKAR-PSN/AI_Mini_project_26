# Phase 3B exploratory analysis

Run `python research/scripts/analyze_phase3b.py --results PATH_TO_ZIP_OR_RUN_DIRECTORY --output research/analysis/phase3b` from repository root. No model weights, GPU or dataset download is used. The input is read only. Integrity failure returns exit code2 and blocks policy selection. Use `--integrity-only` for validation alone.

Primary policy comparison uses nonzero cloud levels (180 repeated question-conditions from10 scenes and30 distinct questions); the complete failure table also includes target zero. P2/P3 choices use leave-one-scene-out development folds, not random question splits. All results remain exploratory. CIs cluster by scene and retain repeated conditions, and condition on selected fold actions. No method is deployed.

Read policy_configuration.json before interpreting cost or risk. P4/P5 agreement may be confidently wrong: inspect false agreement in analysis_summary.json. Zero coverage has undefined selective risk. Risk–coverage integration is limited to the observed attainable interval of the nested P5 gate family; it is not full AURC and must not be compared to a full-domain AURC. Separate policies are plotted as points, never connected into an invented ranking curve.

Images and predictions retain the original run's relative paths; resolve them inside the supplied ZIP/run, not against this output folder. source_file_hashes.json records every input file. CSV rows and figure selection are deterministic. Figure metadata timestamps are omitted; rendering may vary across Matplotlib versions.

E0 cloud detection; E1 cloud-affected VQA; E2 reconstruction versus no reconstruction; E3 bi-temporal change; E4 abstention/risk–coverage; E5 dynamic tool-injection ablation. Phase3B prepares E4 and does not replace E3.
