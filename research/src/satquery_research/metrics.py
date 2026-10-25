"""Exact match remains primary; numeric distance is a separate diagnostic."""
from decimal import Decimal, InvalidOperation
import re
import unicodedata
import numpy as np

def normalize_answer(value):
    # Conservative: no yes/no extraction, synonyms, number-word conversion or tolerance.
    return " ".join(unicodedata.normalize("NFKC", str(value)).casefold().strip().split()).rstrip(".!?").strip()

def numeric_value(value):
    text = normalize_answer(value)
    if not re.fullmatch(r"[+-]?(?:\d+(?:\.\d+)?|\.\d+)", text): return None
    try:
        value = float(Decimal(text))
        return value if np.isfinite(value) else None
    except (InvalidOperation, OverflowError): return None

def answer_category(answer):
    norm = normalize_answer(answer)
    return "yes_no" if norm in ("yes", "no") else "numeric" if numeric_value(answer) is not None else "categorical"

def score_answer(prediction, answer):
    pred, gold = normalize_answer(prediction), normalize_answer(answer)
    p, g = numeric_value(prediction), numeric_value(answer)
    return {"prediction_normalized": pred, "answer_normalized": gold, "correct": int(pred == gold),
            "numeric_absolute_error": abs(p-g) if p is not None and g is not None else None,
            "numeric_parseable": p is not None}

def validate_mask(mask, shape):
    if mask.dtype != np.uint8 or mask.ndim != 2 or mask.shape != tuple(shape):
        raise ValueError("Mask must be shape-aligned HxW binary uint8")
    if not np.isin(mask, [0, 255]).all(): raise ValueError("Mask values must be 0 or 255")
    return mask

def mask_metrics(predicted, reference):
    validate_mask(reference, reference.shape)
    validate_mask(predicted, reference.shape)
    p, r = predicted > 0, reference > 0
    tp, fp, fn, tn = (int(x.sum()) for x in (p&r, p&~r, ~p&r, ~p&~r))
    # Undefined denominators are null, including both-empty F1/IoU; counts remain usable.
    return {"tp":tp,"fp":fp,"fn":fn,"tn":tn,
            "precision":tp/(tp+fp) if tp+fp else None,
            "recall":tp/(tp+fn) if tp+fn else None,
            "f1":2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None,
            "iou":tp/(tp+fp+fn) if tp+fp+fn else None,
            "false_positive_coverage":fp/reference.size,
            "false_positive_rate":fp/(fp+tn) if fp+tn else None,
            "both_empty":not (tp+fp+fn)}

def transitions(before, after):
    b, a = np.asarray(before, dtype=bool), np.asarray(after, dtype=bool)
    if b.shape != a.shape or b.size == 0: raise ValueError("Require nonempty matched arrays")
    return {"recovered":int((~b&a).sum()), "damaged":int((b&~a).sum()),
            "unchanged_correct":int((b&a).sum()), "unchanged_incorrect":int((~b&~a).sum()),
            "accuracy_before":float(b.mean()), "accuracy_after":float(a.mean()),
            "accuracy_difference":float(a.mean()-b.mean())}
