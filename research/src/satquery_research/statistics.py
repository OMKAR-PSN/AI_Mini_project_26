"""Cluster bootstrap: resample scenes, retaining all questions and fixed cloud seeds."""
import numpy as np

def scene_bootstrap(scene_ids, differences, seed=314159, iterations=2000):
    scenes = np.asarray(scene_ids)
    values = np.asarray(differences, dtype=float)
    if len(scenes) != len(values) or not len(values) or not np.isfinite(values).all():
        raise ValueError("Require finite matched scene records")
    ids = sorted(set(scenes))
    totals = np.array([values[scenes == s].sum() for s in ids])
    counts = np.array([(scenes == s).sum() for s in ids])
    result = {"estimate":float(values.mean()),"n_scenes":len(ids),"n_records":len(values),
              "ci_low":None,"ci_high":None,"bootstrap_seed":seed,"bootstrap_iterations":iterations,
              "limitation":"Fewer than 20 scenes; intervals may be unstable" if len(ids)<20 else ""}
    if len(ids)<2: return result
    if iterations < 100: raise ValueError("Use at least 100 bootstrap replicates")
    rng = np.random.default_rng(seed)
    estimates = []
    for _ in range(iterations):
        sample = rng.integers(0,len(ids),len(ids))
        estimates.append(totals[sample].sum()/counts[sample].sum())
    result.update(ci_low=float(np.quantile(estimates,.025)),ci_high=float(np.quantile(estimates,.975)))
    return result
