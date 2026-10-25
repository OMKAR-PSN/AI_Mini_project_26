"""Deterministic pixel-identity scene partition; no question leakage."""
import random

def split_scenes(scene_ids, seed=26167, dev_fraction=0.2):
    ids = sorted(set(scene_ids))
    if len(ids) < 2 or not 0 < dev_fraction < 1:
        raise ValueError("Need at least two scenes and an interior development fraction")
    random.Random(seed).shuffle(ids)
    count = max(1, min(len(ids)-1, round(len(ids)*dev_fraction)))
    dev = set(ids[:count])
    return {scene: "development" if scene in dev else "test" for scene in ids}

def select_roster(rows, partition, max_scenes, questions_per_scene, seed):
    groups = {}
    for row in rows:
        if row["partition"] == partition: groups.setdefault(row["scene_id"], []).append(row)
    ids = sorted(groups)
    random.Random(seed).shuffle(ids)
    ids = ids[:max_scenes] if max_scenes else ids
    selected = []
    for scene in sorted(ids):
        questions = sorted(groups[scene], key=lambda r: r["question_id"])
        random.Random(str(seed)+scene).shuffle(questions)
        # Uniform sampling: never discard counting questions based on difficulty.
        selected.extend(questions[:questions_per_scene] if questions_per_scene else questions)
    return sorted(selected, key=lambda r: (r["scene_id"], r["question_id"]))
