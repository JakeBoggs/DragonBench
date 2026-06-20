import json
import math
import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ScoreResult:
    reward: float
    status: str
    subscores: dict[str, float]
    info: dict[str, Any]


def parse_model_json(answer: Any) -> tuple[dict[str, Any] | None, str | None]:
    if isinstance(answer, dict):
        return answer, None
    if answer is None:
        return None, "empty answer"
    text = str(answer).strip()
    if not text:
        return None, "empty answer"
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None, None if isinstance(parsed, dict) else "top-level JSON must be an object"
    except json.JSONDecodeError:
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
        if not match:
            return None, "answer is not valid JSON"
        try:
            return json.loads(match.group(1)), None
        except json.JSONDecodeError as exc:
            return None, f"fenced JSON parse failed: {exc}"


def score_answer(card: dict[str, Any], answer: Any) -> ScoreResult:
    hidden = card.get("hidden_answer", {})
    if hidden.get("status") not in {"extracted", "verified"} or hidden.get("answer") is None:
        return ScoreResult(
            reward=0.0,
            status="unscored_missing_hidden_answer",
            subscores={},
            info={"reason": "hidden answer has not been extracted from the source dataset"}
        )

    parsed, error = parse_model_json(answer)
    if error:
        return ScoreResult(0.0, "invalid_answer", {"json_parse": 0.0}, {"error": error})

    task = card.get("task")
    expected = hidden["answer"]
    if task == "DragonGeneParse":
        return score_gene_parse(parsed or {}, expected)
    if task == "DragonTFBind":
        return score_tf_bind(parsed or {}, expected)
    if task == "DragonEnhancerTissue":
        return score_enhancer_tissue(parsed or {}, expected)
    if task == "DragonVariantEffect":
        return score_variant_effect(parsed or {}, expected)
    if task == "DragonPhenotypeGene":
        return score_phenotype_gene(parsed or {}, expected)
    return ScoreResult(0.0, "unknown_task", {}, {"task": task})


def score_tf_bind(pred: dict[str, Any], expected: dict[str, Any]) -> ScoreResult:
    pred_intervals = pred.get("predictions", pred.get("binding_intervals", []))
    true_intervals = expected.get("binding_intervals", [])
    interval = interval_f1(pred_intervals, true_intervals, iou_threshold=0.5)
    center = center_distance_score(pred_intervals, true_intervals)
    confidence = mean_confidence_score(pred_intervals)
    reward = 0.8 * interval["f1"] + 0.15 * center + 0.05 * confidence
    return ScoreResult(
        reward=clamp01(reward),
        status="scored",
        subscores={
            "interval_f1_at_iou_0_5": interval["f1"],
            "precision": interval["precision"],
            "recall": interval["recall"],
            "center_distance_score": center,
            "confidence_presence": confidence
        },
        info={"matched": interval["matched"], "n_pred": len(pred_intervals), "n_true": len(true_intervals)}
    )


def score_gene_parse(pred: dict[str, Any], expected: dict[str, Any]) -> ScoreResult:
    exon = interval_f1(pred.get("exons", []), expected.get("exons", []), iou_threshold=0.95)
    donors = set_int_f1(pred.get("splice_donors", []), expected.get("splice_donors", []), tolerance=2)
    acceptors = set_int_f1(pred.get("splice_acceptors", []), expected.get("splice_acceptors", []), tolerance=2)
    cds = interval_f1(pred.get("cds_intervals", []), expected.get("cds_intervals", []), iou_threshold=0.95)
    cds_weight = 0.1 if expected.get("cds_intervals") else 0.0
    reward = 0.45 * exon["f1"] + 0.225 * donors["f1"] + 0.225 * acceptors["f1"] + cds_weight * cds["f1"]
    if cds_weight == 0.0:
        reward /= 0.9
    return ScoreResult(
        clamp01(reward),
        "scored",
        {
            "exon_interval_f1": exon["f1"],
            "splice_donor_f1": donors["f1"],
            "splice_acceptor_f1": acceptors["f1"],
            "cds_interval_f1": cds["f1"]
        },
        {"exon_matches": exon["matched"]}
    )


def score_enhancer_tissue(pred: dict[str, Any], expected: dict[str, Any]) -> ScoreResult:
    pred_tissues = pred.get("tissues", {})
    true_tissues = expected.get("tissues", {})
    label_score = multilabel_probability_score(pred_tissues, true_tissues)
    active_score = binary_probability_score(pred.get("active"), expected.get("active")) if "active" in expected else 1.0
    reward = 0.8 * label_score["reward"] + 0.2 * active_score
    return ScoreResult(
        clamp01(reward),
        "scored",
        {
            "tissue_probability_score": label_score["reward"],
            "average_precision": label_score["average_precision"],
            "active_score": active_score
        },
        {}
    )


def score_variant_effect(pred: dict[str, Any], expected: dict[str, Any]) -> ScoreResult:
    pred_scores = {x.get("variant"): x.get("predicted_score") for x in pred.get("variant_scores", [])}
    true_scores = {x.get("variant"): x.get("score") for x in expected.get("variant_scores", [])}
    variants = [v for v in true_scores if v in pred_scores and is_number(pred_scores[v]) and is_number(true_scores[v])]
    if len(variants) < 2:
        return ScoreResult(0.0, "unscored_insufficient_variant_overlap", {}, {"overlap": len(variants)})
    y_pred = [float(pred_scores[v]) for v in variants]
    y_true = [float(true_scores[v]) for v in variants]
    spearman = (spearman_corr(y_pred, y_true) + 1.0) / 2.0
    pearson = (pearson_corr(y_pred, y_true) + 1.0) / 2.0
    reward = 0.75 * spearman + 0.25 * pearson
    return ScoreResult(clamp01(reward), "scored", {"spearman_scaled": clamp01(spearman), "pearson_scaled": clamp01(pearson)}, {"overlap": len(variants)})


def score_phenotype_gene(pred: dict[str, Any], expected: dict[str, Any]) -> ScoreResult:
    return score_label_probability_map(pred.get("phenotypes", {}), expected.get("phenotypes", {}))


def score_label_probability_map(pred: dict[str, Any], expected: dict[str, Any]) -> ScoreResult:
    scores = multilabel_probability_score(pred, expected)
    return ScoreResult(scores["reward"], "scored", {"label_probability_score": scores["reward"], "average_precision": scores["average_precision"]}, {})


def interval_f1(pred: list[dict[str, Any]], true: list[dict[str, Any]], iou_threshold: float) -> dict[str, Any]:
    pred_clean = [normalize_interval(x) for x in pred]
    true_clean = [normalize_interval(x) for x in true]
    pred_clean = [x for x in pred_clean if x is not None]
    true_clean = [x for x in true_clean if x is not None]
    used_true: set[int] = set()
    matched = 0
    for p in pred_clean:
        best_idx = None
        best_iou = 0.0
        for idx, t in enumerate(true_clean):
            if idx in used_true:
                continue
            if p.get("sequence_id") and t.get("sequence_id") and p["sequence_id"] != t["sequence_id"]:
                continue
            score = iou(p["start"], p["end"], t["start"], t["end"])
            if score > best_iou:
                best_iou = score
                best_idx = idx
        if best_idx is not None and best_iou >= iou_threshold:
            used_true.add(best_idx)
            matched += 1
    precision = matched / len(pred_clean) if pred_clean else (1.0 if not true_clean else 0.0)
    recall = matched / len(true_clean) if true_clean else (1.0 if not pred_clean else 0.0)
    return {"precision": precision, "recall": recall, "f1": f1(precision, recall), "matched": matched}


def normalize_interval(item: Any) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    try:
        start = int(item["start"])
        end = int(item["end"])
    except (KeyError, TypeError, ValueError):
        return None
    if end <= start:
        return None
    out = {"start": start, "end": end}
    if item.get("sequence_id") is not None:
        out["sequence_id"] = str(item["sequence_id"])
    return out


def iou(a_start: int, a_end: int, b_start: int, b_end: int) -> float:
    inter = max(0, min(a_end, b_end) - max(a_start, b_start))
    union = max(a_end, b_end) - min(a_start, b_start)
    return inter / union if union else 0.0


def set_int_f1(pred: list[Any], true: list[Any], tolerance: int = 0) -> dict[str, float]:
    pred_ints = [int(x) for x in pred if is_int_like(x)]
    true_ints = [int(x) for x in true if is_int_like(x)]
    used_true: set[int] = set()
    matched = 0
    for p in pred_ints:
        candidates = [(idx, abs(p - t)) for idx, t in enumerate(true_ints) if idx not in used_true and abs(p - t) <= tolerance]
        if candidates:
            idx, _ = min(candidates, key=lambda x: x[1])
            used_true.add(idx)
            matched += 1
    precision = matched / len(pred_ints) if pred_ints else (1.0 if not true_ints else 0.0)
    recall = matched / len(true_ints) if true_ints else (1.0 if not pred_ints else 0.0)
    return {"precision": precision, "recall": recall, "f1": f1(precision, recall)}


def center_distance_score(pred: list[dict[str, Any]], true: list[dict[str, Any]]) -> float:
    pred_clean = [x for x in (normalize_interval(y) for y in pred) if x]
    true_clean = [x for x in (normalize_interval(y) for y in true) if x]
    if not pred_clean and not true_clean:
        return 1.0
    if not pred_clean or not true_clean:
        return 0.0
    distances = []
    for t in true_clean:
        t_center = (t["start"] + t["end"]) / 2.0
        best = min(abs(((p["start"] + p["end"]) / 2.0) - t_center) for p in pred_clean)
        distances.append(best)
    mean_distance = sum(distances) / len(distances)
    return 1.0 / (1.0 + mean_distance)


def mean_confidence_score(pred: list[dict[str, Any]]) -> float:
    if not pred:
        return 0.0
    valid = [x.get("confidence") for x in pred if is_number(x.get("confidence"))]
    if not valid:
        return 0.0
    return clamp01(sum(float(x) for x in valid) / len(valid))


def multilabel_probability_score(pred: dict[str, Any], expected: dict[str, Any]) -> dict[str, float]:
    labels = list(expected.keys())
    if not labels:
        return {"reward": 0.0, "average_precision": 0.0}
    y_true = [truthy_label(expected[label]) for label in labels]
    y_pred = [clamp01(float(pred.get(label, 0.0))) if is_number(pred.get(label, 0.0)) else 0.0 for label in labels]
    brier = sum((p - y) ** 2 for p, y in zip(y_pred, y_true)) / len(labels)
    brier_score = 1.0 - brier
    ap = average_precision(y_true, y_pred)
    return {"reward": clamp01(0.55 * brier_score + 0.45 * ap), "average_precision": ap}


def binary_probability_score(pred: Any, expected: Any) -> float:
    y = truthy_label(expected)
    p = clamp01(float(pred)) if is_number(pred) else (1.0 if pred is True else 0.0)
    return clamp01(1.0 - (p - y) ** 2)


def average_precision(y_true: list[int], y_score: list[float]) -> float:
    positives = sum(y_true)
    if positives == 0:
        return 1.0 if all(score <= 0.5 for score in y_score) else 0.0
    order = sorted(range(len(y_score)), key=lambda i: y_score[i], reverse=True)
    hits = 0
    total = 0.0
    for rank, idx in enumerate(order, start=1):
        if y_true[idx]:
            hits += 1
            total += hits / rank
    return total / positives


def spearman_corr(a: list[float], b: list[float]) -> float:
    return pearson_corr(ranks(a), ranks(b))


def pearson_corr(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or len(a) < 2:
        return 0.0
    mean_a = sum(a) / len(a)
    mean_b = sum(b) / len(b)
    num = sum((x - mean_a) * (y - mean_b) for x, y in zip(a, b))
    den_a = math.sqrt(sum((x - mean_a) ** 2 for x in a))
    den_b = math.sqrt(sum((y - mean_b) ** 2 for y in b))
    if den_a == 0.0 or den_b == 0.0:
        return 0.0
    return max(-1.0, min(1.0, num / (den_a * den_b)))


def ranks(values: list[float]) -> list[float]:
    order = sorted(enumerate(values), key=lambda x: x[1])
    result = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and order[j + 1][1] == order[i][1]:
            j += 1
        avg_rank = (i + j + 2) / 2.0
        for k in range(i, j + 1):
            result[order[k][0]] = avg_rank
        i = j + 1
    return result


def f1(precision: float, recall: float) -> float:
    return 0.0 if precision + recall == 0.0 else 2.0 * precision * recall / (precision + recall)


def truthy_label(value: Any) -> int:
    if isinstance(value, bool):
        return 1 if value else 0
    if is_number(value):
        return 1 if float(value) >= 0.5 else 0
    return 1 if str(value).lower() in {"true", "yes", "positive", "active", "1"} else 0


def is_number(value: Any) -> bool:
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def is_int_like(value: Any) -> bool:
    try:
        int(value)
        return True
    except (TypeError, ValueError):
        return False


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))

