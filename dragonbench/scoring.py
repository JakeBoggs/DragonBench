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
    if re.search(r"</?Answer\b", text):
        return None, "answer tag must be lowercase exactly: <answer>JSON</answer>"
    tag_matches = re.findall(r"<answer>\s*(\{.*?\})\s*</answer>", text, flags=re.DOTALL)
    if tag_matches:
        tagged_json = tag_matches[-1]
        try:
            parsed = json.loads(tagged_json)
            return parsed if isinstance(parsed, dict) else None, None if isinstance(parsed, dict) else "top-level JSON must be an object"
        except json.JSONDecodeError as exc:
            return None, f"answer XML contained invalid JSON: {exc}"
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None, None if isinstance(parsed, dict) else "top-level JSON must be an object"
    except json.JSONDecodeError as exc:
        return None, f"answer must be exact raw JSON or include a final lowercase <answer>JSON</answer> block: {exc}"


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
    if task == "AnoleGeneParse":
        model_input = card.get("question", {}).get("model_input", {})
        sequence = model_input.get("sequence")
        return score_gene_parse_introns(parsed or {}, expected, sequence)
    if task == "AnolePromoterExpression":
        return score_promoter_expression_ranking(parsed or {}, expected)
    if task == "KomodoProteinFold":
        return score_protein_folding(parsed or {}, expected)
    if task == "DragonTFBind":
        return score_tf_bind(parsed or {}, expected)
    if task == "RNAFold":
        return score_rna_folding(parsed or {}, expected)
    return ScoreResult(0.0, "unknown_task", {}, {"task": task})


def score_tf_bind(pred: dict[str, Any], expected: dict[str, Any]) -> ScoreResult:
    true_probs = expected.get("binding_probabilities", {})
    pred_probs = pred.get("binding_probabilities", {})
    if not isinstance(true_probs, dict):
        return ScoreResult(0.0, "unscored_missing_true_probabilities", {}, {})
    if not isinstance(pred_probs, dict):
        pred_probs = {}

    ids = list(true_probs.keys())
    valid_ids = [seq_id for seq_id in ids if is_number(true_probs[seq_id])]
    true_values = [clamp01(float(true_probs[seq_id])) for seq_id in valid_ids]
    y_true = [1 if value >= 0.5 else 0 for value in true_values]
    y_score = [
        clamp01(float(pred_probs.get(seq_id, 0.0))) if is_number(pred_probs.get(seq_id, 0.0)) else 0.0
        for seq_id in valid_ids
    ]
    if not valid_ids:
        return ScoreResult(0.0, "unscored_missing_true_probabilities", {}, {})

    auroc = binary_auroc(y_true, y_score)
    auprc = average_precision(y_true, y_score)
    ranking = pairwise_score_ranking_accuracy(true_values, y_score)
    brier = 1.0 - sum((score - truth) ** 2 for truth, score in zip(true_values, y_score)) / len(valid_ids)
    reward = 0.40 * auroc + 0.35 * auprc + 0.20 * ranking + 0.05 * brier
    return ScoreResult(
        clamp01(reward),
        "scored",
        {
            "auroc": auroc,
            "auprc": auprc,
            "ranking_accuracy": ranking,
            "brier_score": clamp01(brier),
        },
        {"n_pred": len(pred_probs), "n_true": len(valid_ids), "positives": sum(y_true)}
    )


def score_gene_parse_introns(pred: dict[str, Any], expected: dict[str, Any], sequence: Any = None) -> ScoreResult:
    intron = interval_f1(pred.get("introns", []), expected.get("introns", []), iou_threshold=0.8)
    boundary = interval_boundary_score(pred.get("introns", []), expected.get("introns", []))
    count_score = count_accuracy(len(pred.get("introns", [])), len(expected.get("introns", [])))
    splice_score = None
    if isinstance(sequence, str) and sequence:
        pred_spliced = splice_sequence(sequence, pred.get("introns", []))
        true_spliced = expected.get("spliced_sequence") or splice_sequence(sequence, expected.get("introns", []))
        splice_score = levenshtein_similarity(pred_spliced, true_spliced)
    reward = splice_score if splice_score is not None else 0.75 * intron["f1"] + 0.15 * boundary + 0.10 * count_score
    subscores = {
        "spliced_sequence_levenshtein_similarity": splice_score if splice_score is not None else 0.0,
        "intron_interval_f1_at_iou_0_8": intron["f1"],
        "precision": intron["precision"],
        "recall": intron["recall"],
        "intron_boundary_score": boundary,
        "intron_count_accuracy": count_score,
    }
    return ScoreResult(
        clamp01(reward),
        "scored",
        subscores,
        {"matched_introns": intron["matched"], "n_pred": len(pred.get("introns", [])), "n_true": len(expected.get("introns", []))}
    )


def score_promoter_expression_ranking(pred: dict[str, Any], expected: dict[str, Any]) -> ScoreResult:
    true_order = [str(x) for x in expected.get("tissue_ranking", [])]
    pred_order = [str(x) for x in pred.get("tissue_ranking", [])]
    if not true_order:
        return ScoreResult(0.0, "unscored_missing_true_ranking", {}, {})
    ndcg = ndcg_for_order(pred_order, expected.get("expression", {}), true_order)
    top1 = 1.0 if pred_order and pred_order[0] == true_order[0] else 0.0
    spearman = (spearman_order_corr(pred_order, true_order) + 1.0) / 2.0
    completeness = len(set(pred_order).intersection(true_order)) / len(true_order)
    pairwise = pairwise_order_accuracy(pred_order, true_order)
    reward = 0.50 * spearman + 0.20 * top1 + 0.20 * pairwise + 0.10 * completeness
    return ScoreResult(
        clamp01(reward),
        "scored",
        {
            "ndcg_at_all_tissues": ndcg,
            "top1_tissue_accuracy": top1,
            "spearman_rank_scaled": clamp01(spearman),
            "pairwise_ranking_accuracy": pairwise,
            "ranking_completeness": completeness,
        },
        {"n_pred": len(pred_order), "n_true": len(true_order), "true_top1": true_order[0]}
    )


def score_protein_folding(pred: dict[str, Any], expected: dict[str, Any]) -> ScoreResult:
    pred_coords, structure_info = predicted_protein_coordinates(pred)
    true_coords = normalize_coordinates(expected.get("coordinates", []))
    common = sorted(set(pred_coords).intersection(true_coords))
    if len(common) < 2:
        return ScoreResult(
            0.0,
            "unscored_insufficient_coordinate_overlap",
            {
                "coordinate_coverage": len(common) / max(len(true_coords), 1),
                "structure_validity": structure_info["validity"],
                "backbone_atom_completeness": structure_info["backbone_completeness"],
            },
            {"overlap": len(common), "n_true": len(true_coords), "n_pred": len(pred_coords), **structure_info}
        )
    stats = distance_matrix_stats(pred_coords, true_coords, common)
    coverage = len(common) / max(len(true_coords), 1)
    drmsd_score = 1.0 / (1.0 + stats["drmsd"] / 2.0)
    reward = 0.80 * drmsd_score + 0.10 * coverage + 0.05 * structure_info["validity"] + 0.05 * structure_info["backbone_completeness"]
    return ScoreResult(
        clamp01(reward),
        "scored",
        {
            "distance_matrix_rmsd_score": drmsd_score,
            "coordinate_coverage": coverage,
            "structure_validity": structure_info["validity"],
            "backbone_atom_completeness": structure_info["backbone_completeness"],
            "drmsd_angstrom": stats["drmsd"],
            "mean_distance_error_angstrom": stats["mean_abs_distance_error"],
        },
        {"overlap": len(common), "n_pred": len(pred_coords), "n_true": len(true_coords), **structure_info}
    )


def score_rna_folding(pred: dict[str, Any], expected: dict[str, Any]) -> ScoreResult:
    pred_dot = str(pred.get("dot_bracket", ""))
    true_dot = str(expected.get("dot_bracket", ""))
    pred_pairs = dot_bracket_to_pairs(pred_dot)
    true_pairs = normalize_contacts(expected.get("base_pairs", [])) if expected.get("base_pairs") else dot_bracket_to_pairs(true_dot)
    pair = pair_f1(pred_pairs, true_pairs)
    exact = 1.0 if pred_dot == true_dot else 0.0
    length_valid = 1.0 if len(pred_dot) == len(true_dot) else 0.0
    reward = 0.8 * pair["f1"] + 0.15 * exact + 0.05 * length_valid
    return ScoreResult(
        clamp01(reward),
        "scored",
        {
            "base_pair_f1": pair["f1"],
            "base_pair_precision": pair["precision"],
            "base_pair_recall": pair["recall"],
            "exact_dot_bracket_match": exact,
            "length_validity": length_valid,
        },
        {"matched_base_pairs": pair["matched"], "n_pred_pairs": len(pred_pairs), "n_true_pairs": len(true_pairs)}
    )


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


def interval_boundary_score(pred: list[dict[str, Any]], true: list[dict[str, Any]]) -> float:
    pred_clean = [x for x in (normalize_interval(y) for y in pred) if x]
    true_clean = [x for x in (normalize_interval(y) for y in true) if x]
    if not pred_clean and not true_clean:
        return 1.0
    if not pred_clean or not true_clean:
        return 0.0
    errors = []
    for t in true_clean:
        best = min(abs(p["start"] - t["start"]) + abs(p["end"] - t["end"]) for p in pred_clean)
        errors.append(best / 2.0)
    mean_error = sum(errors) / len(errors)
    return 1.0 / (1.0 + mean_error)


def count_accuracy(pred_count: int, true_count: int) -> float:
    if true_count == 0:
        return 1.0 if pred_count == 0 else 0.0
    return clamp01(1.0 - abs(pred_count - true_count) / max(true_count, 1))


def normalize_contacts(items: list[Any]) -> set[tuple[int, int]]:
    pairs: set[tuple[int, int]] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            i = int(item["i"])
            j = int(item["j"])
        except (KeyError, TypeError, ValueError):
            continue
        if i == j:
            continue
        pairs.add((min(i, j), max(i, j)))
    return pairs


def normalize_coordinates(items: list[Any]) -> dict[int, tuple[float, float, float]]:
    coords: dict[int, tuple[float, float, float]] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            idx = int(item["residue_index"])
            x = float(item["x"])
            y = float(item["y"])
            z = float(item["z"])
        except (KeyError, TypeError, ValueError):
            continue
        if math.isfinite(x) and math.isfinite(y) and math.isfinite(z):
            coords[idx] = (x, y, z)
    return coords


def predicted_protein_coordinates(pred: dict[str, Any]) -> tuple[dict[int, tuple[float, float, float]], dict[str, Any]]:
    if isinstance(pred.get("coordinates"), list):
        coords = normalize_coordinates(pred.get("coordinates", []))
        return coords, {
            "structure_format": "coordinate_array",
            "validity": 1.0 if coords else 0.0,
            "backbone_completeness": 1.0 if coords else 0.0,
        }

    structure = pred.get("pdb", pred.get("mmcif", pred.get("structure", pred.get("structure_file", ""))))
    if not isinstance(structure, str) or not structure.strip():
        return {}, {"structure_format": "missing", "validity": 0.0, "backbone_completeness": 0.0}

    coords, atom_stats = parse_pdb_like_ca_coordinates(structure)
    if not coords and "_atom_site." in structure:
        coords, atom_stats = parse_mmcif_like_ca_coordinates(structure)
    validity = 1.0 if coords else 0.0
    backbone_completeness = backbone_atom_completeness(atom_stats)
    return coords, {
        "structure_format": "pdb_or_mmcif_string",
        "validity": validity,
        "backbone_completeness": backbone_completeness,
    }


def parse_pdb_like_ca_coordinates(text: str) -> tuple[dict[int, tuple[float, float, float]], dict[tuple[str, str, str], set[str]]]:
    coords: dict[int, tuple[float, float, float]] = {}
    atom_stats: dict[tuple[str, str, str], set[str]] = {}
    residue_to_index: dict[tuple[str, str, str], int] = {}
    for line in text.splitlines():
        if not line.startswith(("ATOM", "HETATM")):
            continue
        if len(line) < 54:
            continue
        atom = line[12:16].strip()
        altloc = line[16].strip()
        chain = line[21].strip()
        resseq = line[22:26].strip()
        icode = line[26].strip()
        if altloc not in {"", "A", "1"}:
            continue
        key = (chain, resseq, icode)
        atom_stats.setdefault(key, set()).add(atom)
        if atom != "CA":
            continue
        try:
            xyz = (float(line[30:38]), float(line[38:46]), float(line[46:54]))
        except ValueError:
            continue
        idx = residue_to_index.setdefault(key, len(residue_to_index))
        coords[idx] = xyz
    return coords, atom_stats


def parse_mmcif_like_ca_coordinates(text: str) -> tuple[dict[int, tuple[float, float, float]], dict[tuple[str, str, str], set[str]]]:
    coords: dict[int, tuple[float, float, float]] = {}
    atom_stats: dict[tuple[str, str, str], set[str]] = {}
    residue_to_index: dict[tuple[str, str, str], int] = {}
    for line in text.splitlines():
        tokens = line.split()
        if len(tokens) < 12 or tokens[0] not in {"ATOM", "HETATM"}:
            continue
        atom = tokens[3] if len(tokens) > 3 else ""
        chain = tokens[6] if len(tokens) > 6 else ""
        resseq = tokens[8] if len(tokens) > 8 else tokens[6]
        key = (chain, resseq, "")
        atom_stats.setdefault(key, set()).add(atom)
        if atom != "CA":
            continue
        xyz = first_float_triple(tokens[9:])
        if xyz is None:
            continue
        idx = residue_to_index.setdefault(key, len(residue_to_index))
        coords[idx] = xyz
    return coords, atom_stats


def first_float_triple(tokens: list[str]) -> tuple[float, float, float] | None:
    for idx in range(0, max(0, len(tokens) - 2)):
        try:
            xyz = (float(tokens[idx]), float(tokens[idx + 1]), float(tokens[idx + 2]))
        except ValueError:
            continue
        if all(math.isfinite(x) for x in xyz):
            return xyz
    return None


def backbone_atom_completeness(atom_stats: dict[tuple[str, str, str], set[str]]) -> float:
    if not atom_stats:
        return 0.0
    required = {"N", "CA", "C", "O"}
    return sum(len(required.intersection(atoms)) / len(required) for atoms in atom_stats.values()) / len(atom_stats)


def distance_matrix_stats(
    pred: dict[int, tuple[float, float, float]],
    true: dict[int, tuple[float, float, float]],
    indices: list[int],
) -> dict[str, float]:
    squared_errors = []
    abs_errors = []
    for a_pos, i in enumerate(indices):
        for j in indices[a_pos + 1:]:
            pred_d = euclidean(pred[i], pred[j])
            true_d = euclidean(true[i], true[j])
            error = pred_d - true_d
            squared_errors.append(error * error)
            abs_errors.append(abs(error))
    if not squared_errors:
        return {"drmsd": 0.0, "mean_abs_distance_error": 0.0}
    return {
        "drmsd": math.sqrt(sum(squared_errors) / len(squared_errors)),
        "mean_abs_distance_error": sum(abs_errors) / len(abs_errors),
    }


def euclidean(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)


def pair_f1(pred: set[tuple[int, int]], true: set[tuple[int, int]]) -> dict[str, float]:
    matched = len(pred.intersection(true))
    precision = matched / len(pred) if pred else (1.0 if not true else 0.0)
    recall = matched / len(true) if true else (1.0 if not pred else 0.0)
    return {"precision": precision, "recall": recall, "f1": f1(precision, recall), "matched": matched}


def splice_sequence(sequence: str, introns: list[Any]) -> str:
    clean = [x for x in (normalize_interval(y) for y in introns) if x]
    clean.sort(key=lambda item: (item["start"], item["end"]))
    pieces = []
    cursor = 0
    for intron in clean:
        start = max(0, min(len(sequence), intron["start"]))
        end = max(0, min(len(sequence), intron["end"]))
        if start < cursor or end <= start:
            continue
        pieces.append(sequence[cursor:start])
        cursor = end
    pieces.append(sequence[cursor:])
    return "".join(pieces)


def levenshtein_similarity(a: str, b: str) -> float:
    if a == b:
        return 1.0
    denom = max(len(a), len(b), 1)
    return clamp01(1.0 - levenshtein_distance(a, b) / denom)


def levenshtein_distance(a: str, b: str) -> int:
    if len(a) < len(b):
        a, b = b, a
    previous = list(range(len(b) + 1))
    for i, char_a in enumerate(a, start=1):
        current = [i]
        for j, char_b in enumerate(b, start=1):
            current.append(min(
                previous[j] + 1,
                current[j - 1] + 1,
                previous[j - 1] + (0 if char_a == char_b else 1),
            ))
        previous = current
    return previous[-1]


def dot_bracket_to_pairs(dot: str) -> set[tuple[int, int]]:
    stack: list[int] = []
    pairs: set[tuple[int, int]] = set()
    for idx, char in enumerate(dot):
        if char == "(":
            stack.append(idx)
        elif char == ")" and stack:
            pairs.add((stack.pop(), idx))
    return pairs


def ndcg_for_order(pred_order: list[str], relevance: dict[str, Any], true_order: list[str]) -> float:
    rel = {}
    for rank, label in enumerate(true_order):
        fallback = len(true_order) - rank
        rel[label] = float(relevance.get(label, fallback)) if is_number(relevance.get(label, fallback)) else float(fallback)
    dcg = dcg_for_labels(pred_order, rel)
    ideal = dcg_for_labels(sorted(true_order, key=lambda label: rel[label], reverse=True), rel)
    return dcg / ideal if ideal else 0.0


def dcg_for_labels(labels: list[str], rel: dict[str, float]) -> float:
    total = 0.0
    seen: set[str] = set()
    for rank, label in enumerate(labels, start=1):
        if label in seen:
            continue
        seen.add(label)
        gain = rel.get(label, 0.0)
        total += gain / math.log2(rank + 1)
    return total


def spearman_order_corr(pred_order: list[str], true_order: list[str]) -> float:
    labels = list(dict.fromkeys(true_order))
    n = len(labels)
    if n < 2:
        return 1.0
    missing_rank = n + 1
    true_ranks = {label: idx + 1 for idx, label in enumerate(true_order)}
    pred_ranks = {label: idx + 1 for idx, label in enumerate(pred_order)}
    a = [float(pred_ranks.get(label, missing_rank)) for label in labels]
    b = [float(true_ranks[label]) for label in labels]
    return pearson_corr(a, b)


def pairwise_order_accuracy(pred_order: list[str], true_order: list[str]) -> float:
    labels = list(dict.fromkeys(true_order))
    if len(labels) < 2:
        return 1.0
    missing_rank = len(labels) + 1
    true_ranks = {label: idx for idx, label in enumerate(true_order)}
    pred_ranks = {label: idx for idx, label in enumerate(pred_order)}
    total = 0
    correct = 0
    for i, a in enumerate(labels):
        for b in labels[i + 1:]:
            total += 1
            true_cmp = true_ranks[a] < true_ranks[b]
            pred_cmp = pred_ranks.get(a, missing_rank) < pred_ranks.get(b, missing_rank)
            correct += 1 if true_cmp == pred_cmp else 0
    return correct / total if total else 1.0


def pairwise_score_ranking_accuracy(true_scores: list[float], pred_scores: list[float]) -> float:
    total = 0
    correct = 0.0
    for i in range(len(true_scores)):
        for j in range(i + 1, len(true_scores)):
            if true_scores[i] == true_scores[j]:
                continue
            total += 1
            true_cmp = true_scores[i] > true_scores[j]
            if pred_scores[i] == pred_scores[j]:
                correct += 0.5
            elif (pred_scores[i] > pred_scores[j]) == true_cmp:
                correct += 1.0
    return correct / total if total else 1.0


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


def binary_auroc(y_true: list[int], y_score: list[float]) -> float:
    positives = [score for label, score in zip(y_true, y_score) if label == 1]
    negatives = [score for label, score in zip(y_true, y_score) if label == 0]
    if not positives or not negatives:
        return 1.0
    total = 0
    wins = 0.0
    for pos in positives:
        for neg in negatives:
            total += 1
            if pos > neg:
                wins += 1.0
            elif pos == neg:
                wins += 0.5
    return wins / total if total else 0.0


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


def f1(precision: float, recall: float) -> float:
    return 0.0 if precision + recall == 0.0 else 2.0 * precision * recall / (precision + recall)


def is_number(value: Any) -> bool:
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))
