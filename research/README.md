# SatQuery research experiments E0–E2

Isolated research package; does not integrate Qwen into FastAPI or change operational science/UI.
See `EXPERIMENT_PROTOCOL.md` for the frozen comparison policy and `PHASE3A_HANDOVER.md` for executed validation and limitations.

## Installation and execution

Run from the repository root using Python 3.11/3.12 in a fresh environment. The checked-in requirements target Colab; the local CPU verification environment records its own exact versions in each manifest.

```bash
python -m venv research/.venv
# Linux/Colab:
source research/.venv/bin/activate
# Windows PowerShell instead:
# research/.venv/Scripts/Activate.ps1
python -m pip install -r research/requirements-colab.txt
python -m pytest research/tests -q
python research/scripts/run_pilot.py --stage prepare
python research/scripts/run_pilot.py --stage cpu
```

After reviewing masks and resource requirements, on a suitable CUDA GPU:

```bash
python research/scripts/run_pilot.py --stage all
python research/scripts/analyze_results.py research/outputs/RUN_ID
```

Only after explicit team authorization, run the held-out evaluation:

```bash
python research/scripts/run_full.py --stage all
```

No model is loaded by `prepare` or `cpu`. `all` first completes/resumes CPU outputs, then loads one shared model. A missing GPU or loading failure is recorded as partial, never replaced by fake answers. Re-run the same command to retry failed items and skip completed ones. Use one process per run directory.

## Colab

Upload `notebooks/SatQuery_E0_E1_E2_Colab.ipynb` through Colab's File → Upload notebook. Supply a checkout containing the **uncommitted** research directory, or fill in a repository URL and commit after your team separately publishes it. The notebook deliberately has no invented public revision for these changes. Optional Drive storage preserves checkpoints; after restart rerun access, mount, config and execution cells. Restart after installing changed binary libraries, before importing them.

## Layout and outputs

- `src/satquery_research/`: dataset ingestion, scene split, cloud/detector/repair adapters, shared VLM loader, metrics, bootstrap, checkpoints, runner and plotting.
- `configs/`: ten-scene development pilot; held-out test evaluation with three seeds.
- `scripts/`: pilot, full and results-analysis entry points.
- `tests/`: CPU-only validation; no model weights required.
- `real_cloud_annotations/`: separate annotation intake; no fabricated real labels.
- `outputs/<identity>/`: manifests, rosters, per-item JSON checkpoints, original/scientific image arrays, CSVs and figures. Ignored by Git.

Run IDs hash config, source fingerprints and relevant runtime versions. Different identities cannot share a directory. Completed image digests are checked before reuse. SHA-256 detects changes; it does not authenticate the author. Datasets/model caches, environments and generated results are ignored.

E0 CSVs contain scene/partition/seed/generator, target/achieved/detector coverage, confusion counts, precision/recall/F1/IoU, empty flags, latencies and image/mask provenance. `repair_outputs.csv` adds variant, actual algorithm, radius, mask source/digest, common cloudy digest, output identity and timing. `predictions.csv` adds question/answer/category, condition, raw/normalized prediction, exact match, numeric diagnostic, model-grid size, latency and peak GPU memory. Summaries include category accuracy, paired transitions, scene-bootstrap intervals, development-majority baseline and unmatched-pair counts.

## Sources

- [Pinned RSVQA subset](https://huggingface.co/datasets/dmarsili/RSVQA-LR-2k/tree/35de41f26170edda2ccc4f88c0f62f641bb9e1f1), [original RSVQA attribution](https://rsvqa.sylvainlobry.com/#dataset), [original paper](https://doi.org/10.1109/TGRS.2020.2988782).
- [Pinned SatelliteCloudGenerator source](https://github.com/strath-ai/SatelliteCloudGenerator/tree/d0787cbdc1b39a7976f89aa085f1430f3207eda6), [publication](https://doi.org/10.3390/rs15174138).
- [Pinned Qwen model](https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct/tree/66285546d2b821cf421d4f5eb2576359d3770cd3), [supported Transformers 4.51.3 implementation](https://huggingface.co/docs/transformers/v4.51.3/en/model_doc/qwen2_5_vl).
