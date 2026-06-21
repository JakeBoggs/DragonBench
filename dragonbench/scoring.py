import json
import math
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ScoreResult:
    reward: float
    status: str
    subscores: dict[str, float]
    info: dict[str, Any]


LDDT_DISTANCE_CUTOFF_ANGSTROM = 15.0
LDDT_ERROR_THRESHOLDS_ANGSTROM = (0.5, 1.0, 2.0, 4.0)


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
    except json.JSONDecodeError as exc:
        return None, f"answer must be exactly one JSON object: {exc}"


def score_answer(card: dict[str, Any], answer: Any) -> ScoreResult:
    hidden = card["hidden_answer"]
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
        sequence = card["question"]["model_input"]["sequence"]
        return score_gene_parse_introns(parsed, expected, sequence)
    if task == "AnolePromoterExpression":
        return score_promoter_expression_ranking(parsed, expected)
    if task == "KomodoProteinFold":
        return score_protein_folding(parsed, expected)
    if task == "DragonTFBind":
        return score_tf_bind(parsed, expected)
    if task == "RNAFold":
        return score_rna_folding(parsed, expected)
    return ScoreResult(0.0, "unknown_task", {}, {"task": task})


def invalid_answer(reason: str, subscores: dict[str, float] | None = None, **info: Any) -> ScoreResult:
    return ScoreResult(0.0, "invalid_answer", {} if subscores is None else subscores, {"reason": reason, **info})


def invalid_hidden_answer(reason: str, **info: Any) -> ScoreResult:
    return ScoreResult(0.0, "unscored_invalid_hidden_answer", {}, {"reason": reason, **info})


def score_tf_bind(pred: dict[str, Any], expected: dict[str, Any]) -> ScoreResult:
    true_probs = expected.get("binding_probabilities")
    if not isinstance(true_probs, dict) or not true_probs:
        return invalid_hidden_answer("hidden answer must contain binding_probabilities")

    ids = list(true_probs.keys())
    true_values = []
    for seq_id in ids:
        value = true_probs[seq_id]
        if not is_probability(value):
            return invalid_hidden_answer("hidden binding probability must be a number from 0 through 1", sequence_id=seq_id)
        true_values.append(float(value))
    if len(set(true_values)) < 2:
        return invalid_hidden_answer("TF binding hidden probabilities must not all be identical")

    pred_probs = pred.get("binding_probabilities")
    if not isinstance(pred_probs, dict):
        return invalid_answer("answer must contain a binding_probabilities object")
    if set(pred_probs.keys()) != set(ids):
        return invalid_answer(
            "binding_probabilities must contain exactly the supplied candidate IDs",
            missing_ids=sorted(set(ids) - set(pred_probs.keys())),
            extra_ids=sorted(set(pred_probs.keys()) - set(ids)),
            n_pred=len(pred_probs),
            n_true=len(ids),
        )

    y_score = []
    for seq_id in ids:
        value = pred_probs[seq_id]
        if not is_probability(value):
            return invalid_answer("each binding probability must be a number from 0 through 1", sequence_id=seq_id)
        y_score.append(float(value))

    spearman = spearman_score_corr(y_score, true_values)
    reward = max(0.0, spearman)
    return ScoreResult(
        clamp01(reward),
        "scored",
        {
            "spearman_rank_correlation": spearman,
        },
        {"n_pred": len(pred_probs), "n_true": len(ids)}
    )


def score_gene_parse_introns(pred: dict[str, Any], expected: dict[str, Any], sequence: Any = None) -> ScoreResult:
    if not isinstance(sequence, str) or not sequence:
        return invalid_hidden_answer("AnoleGeneParse card must include the genomic sequence")
    if not isinstance(expected.get("spliced_sequence"), str):
        return invalid_hidden_answer("AnoleGeneParse hidden answer must include spliced_sequence")
    if not isinstance(expected.get("introns"), list):
        return invalid_hidden_answer("AnoleGeneParse hidden answer must include introns")
    if not isinstance(pred.get("introns"), list):
        return invalid_answer("answer must contain an introns array")

    true_introns, true_error = parse_intervals(expected["introns"], sequence_length=len(sequence))
    if true_error:
        return invalid_hidden_answer(true_error)
    if not true_introns:
        return invalid_hidden_answer("AnoleGeneParse hidden answer must contain at least one intron")
    pred_introns, pred_error = parse_intervals(pred["introns"], sequence_length=len(sequence))
    if pred_error:
        return invalid_answer(pred_error)

    pred_spliced = splice_sequence(sequence, pred_introns)
    true_spliced = expected["spliced_sequence"]
    splice_distance = levenshtein_distance(pred_spliced, true_spliced)
    splice_normalization_length = len(sequence) - len(true_spliced)
    if splice_normalization_length <= 0:
        return invalid_hidden_answer("ground-truth intron length must be positive")
    reward = intron_levenshtein_similarity(
        pred_spliced,
        true_spliced,
        original_length=len(sequence),
        distance=splice_distance,
    )
    intron = interval_f1(pred_introns, true_introns, iou_threshold=0.8)
    boundary = interval_boundary_score(pred_introns, true_introns)
    count_score = count_accuracy(len(pred_introns), len(true_introns))
    subscores = {
        "spliced_sequence_levenshtein_similarity": reward,
        "intron_interval_f1_at_iou_0_8": intron["f1"],
        "precision": intron["precision"],
        "recall": intron["recall"],
        "intron_boundary_score": boundary,
        "intron_count_accuracy": count_score,
    }
    info = {
        "matched_introns": intron["matched"],
        "n_pred": len(pred_introns),
        "n_true": len(true_introns),
        "spliced_sequence_levenshtein_distance": splice_distance,
        "spliced_sequence_normalization_length": splice_normalization_length,
    }
    return ScoreResult(
        clamp01(reward),
        "scored",
        subscores,
        info,
    )


def score_promoter_expression_ranking(pred: dict[str, Any], expected: dict[str, Any]) -> ScoreResult:
    true_order = expected.get("tissue_ranking")
    pred_order = pred.get("tissue_ranking")
    if not isinstance(true_order, list) or not true_order or not all(isinstance(tissue, str) for tissue in true_order):
        return invalid_hidden_answer("hidden answer must contain a non-empty tissue_ranking string array")
    if len(true_order) < 2:
        return invalid_hidden_answer("hidden tissue_ranking must contain at least two tissues")
    if len(set(true_order)) != len(true_order):
        return invalid_hidden_answer("hidden tissue_ranking must not contain duplicates")
    if not isinstance(pred_order, list) or not all(isinstance(tissue, str) for tissue in pred_order):
        return invalid_answer("answer must contain a tissue_ranking string array")

    completeness = len(set(pred_order).intersection(true_order)) / len(true_order)
    if len(pred_order) != len(true_order) or set(pred_order) != set(true_order):
        return invalid_answer(
            "tissue_ranking must contain every candidate tissue exactly once",
            {
                "ranking_completeness": completeness,
            },
            n_pred=len(pred_order),
            n_true=len(true_order),
            missing_tissues=sorted(set(true_order) - set(pred_order)),
            extra_tissues=sorted(set(pred_order) - set(true_order)),
        )
    spearman = spearman_order_corr(pred_order, true_order)
    reward = max(0.0, spearman)
    return ScoreResult(
        clamp01(reward),
        "scored",
        {
            "spearman_rank_correlation": spearman,
            "ranking_completeness": completeness,
        },
        {"n_pred": len(pred_order), "n_true": len(true_order)}
    )


def score_protein_folding(pred: dict[str, Any], expected: dict[str, Any]) -> ScoreResult:
    pred_coords, structure_info, error = predicted_protein_coordinates(pred)
    if error:
        return invalid_answer(error)
    true_coords, true_error = reference_protein_coordinates(expected)
    if true_error:
        return invalid_hidden_answer(true_error)
    common = sorted(set(pred_coords).intersection(true_coords))
    if len(common) < 2:
        return invalid_answer(
            "submitted structure has fewer than two residues overlapping the reference",
            {
                "coordinate_coverage": len(common) / len(true_coords),
                "structure_validity": structure_info["validity"],
                "backbone_atom_completeness": structure_info["backbone_completeness"],
            },
            overlap=len(common),
            n_true=len(true_coords),
            n_pred=len(pred_coords),
            **structure_info,
        )
    lddt_stats, lddt_error = ca_lddt_stats(pred_coords, true_coords)
    if lddt_error:
        return invalid_hidden_answer(lddt_error)
    coverage = len(common) / len(true_coords)
    reward = lddt_stats["ca_lddt"]
    return ScoreResult(
        clamp01(reward),
        "scored",
        {
            "ca_lddt": lddt_stats["ca_lddt"],
            "coordinate_coverage": coverage,
            "structure_validity": structure_info["validity"],
            "backbone_atom_completeness": structure_info["backbone_completeness"],
            "lddt_reference_contacts": lddt_stats["reference_contacts"],
            "lddt_evaluated_contacts": lddt_stats["evaluated_contacts"],
            "lddt_missing_contacts": lddt_stats["missing_contacts"],
            "lddt_distance_cutoff_angstrom": LDDT_DISTANCE_CUTOFF_ANGSTROM,
        },
        {
            "overlap": len(common),
            "n_pred": len(pred_coords),
            "n_true": len(true_coords),
            "lddt_thresholds_angstrom": list(LDDT_ERROR_THRESHOLDS_ANGSTROM),
            **structure_info,
        }
    )


def score_rna_folding(pred: dict[str, Any], expected: dict[str, Any]) -> ScoreResult:
    pred_dot = pred.get("dot_bracket")
    true_dot = expected.get("dot_bracket")
    if not isinstance(true_dot, str) or not true_dot:
        return invalid_hidden_answer("RNAFold hidden answer must contain dot_bracket")
    if not isinstance(expected.get("base_pairs"), list):
        return invalid_hidden_answer("RNAFold hidden answer must contain base_pairs")
    if not isinstance(pred_dot, str):
        return invalid_answer("answer must contain a dot_bracket string")
    dot_error = validate_dot_bracket(pred_dot, expected_length=len(true_dot))
    if dot_error:
        return invalid_answer(dot_error)
    pred_pairs = dot_bracket_to_pairs(pred_dot)
    true_pairs, true_pair_error = parse_contacts(expected["base_pairs"], sequence_length=len(true_dot))
    if true_pair_error:
        return invalid_hidden_answer(true_pair_error)
    if not true_pairs:
        return invalid_hidden_answer("RNAFold hidden answer must contain at least one base pair")
    pair = pair_f1(pred_pairs, true_pairs)
    exact = 1.0 if pred_dot == true_dot else 0.0
    reward = pair["f1"]
    return ScoreResult(
        clamp01(reward),
        "scored",
        {
            "base_pair_f1": pair["f1"],
            "base_pair_precision": pair["precision"],
            "base_pair_recall": pair["recall"],
            "exact_dot_bracket_match": exact,
        },
        {"matched_base_pairs": pair["matched"], "n_pred_pairs": len(pred_pairs), "n_true_pairs": len(true_pairs)}
    )


def parse_intervals(items: Any, sequence_length: int) -> tuple[list[dict[str, int]], str | None]:
    if not isinstance(items, list):
        return [], "introns must be an array"
    intervals = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            return [], f"introns[{index}] must be an object"
        if not isinstance(item.get("start"), int) or isinstance(item.get("start"), bool):
            return [], f"introns[{index}].start must be an integer"
        if not isinstance(item.get("end"), int) or isinstance(item.get("end"), bool):
            return [], f"introns[{index}].end must be an integer"
        start = item["start"]
        end = item["end"]
        if start < 0 or end > sequence_length or end <= start:
            return [], f"introns[{index}] must satisfy 0 <= start < end <= sequence length"
        intervals.append({"start": start, "end": end})
    intervals.sort(key=lambda item: (item["start"], item["end"]))
    for prev, current in zip(intervals, intervals[1:]):
        if current["start"] < prev["end"]:
            return [], "introns must not overlap"
    return intervals, None


def interval_f1(pred: list[dict[str, Any]], true: list[dict[str, Any]], iou_threshold: float) -> dict[str, Any]:
    used_true: set[int] = set()
    matched = 0
    for p in pred:
        best_idx = None
        best_iou = 0.0
        for idx, t in enumerate(true):
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
    precision = matched / len(pred) if pred else (1.0 if not true else 0.0)
    recall = matched / len(true) if true else (1.0 if not pred else 0.0)
    return {"precision": precision, "recall": recall, "f1": f1(precision, recall), "matched": matched}


def iou(a_start: int, a_end: int, b_start: int, b_end: int) -> float:
    inter = max(0, min(a_end, b_end) - max(a_start, b_start))
    union = max(a_end, b_end) - min(a_start, b_start)
    return inter / union if union else 0.0


def interval_boundary_score(pred: list[dict[str, Any]], true: list[dict[str, Any]]) -> float:
    if not pred and not true:
        return 1.0
    if not pred or not true:
        return 0.0
    errors = []
    for t in true:
        best = min(abs(p["start"] - t["start"]) + abs(p["end"] - t["end"]) for p in pred)
        errors.append(best / 2.0)
    mean_error = sum(errors) / len(errors)
    return 1.0 / (1.0 + mean_error)


def count_accuracy(pred_count: int, true_count: int) -> float:
    return clamp01(1.0 - abs(pred_count - true_count) / true_count)


def parse_contacts(items: list[Any], sequence_length: int) -> tuple[set[tuple[int, int]], str | None]:
    pairs: set[tuple[int, int]] = set()
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            return set(), f"base_pairs[{index}] must be an object"
        if not isinstance(item.get("i"), int) or isinstance(item.get("i"), bool):
            return set(), f"base_pairs[{index}].i must be an integer"
        if not isinstance(item.get("j"), int) or isinstance(item.get("j"), bool):
            return set(), f"base_pairs[{index}].j must be an integer"
        i = item["i"]
        j = item["j"]
        if i == j:
            return set(), f"base_pairs[{index}] must connect two distinct positions"
        if i < 0 or j < 0 or i >= sequence_length or j >= sequence_length:
            return set(), f"base_pairs[{index}] must use indices inside the dot-bracket length"
        pairs.add((min(i, j), max(i, j)))
    return pairs, None


def reference_protein_coordinates(expected: dict[str, Any]) -> tuple[dict[int, tuple[float, float, float]], str | None]:
    if not isinstance(expected.get("coordinates"), list):
        return {}, "KomodoProteinFold hidden answer must contain coordinates"
    coords: dict[int, tuple[float, float, float]] = {}
    for index, item in enumerate(expected["coordinates"]):
        if not isinstance(item, dict):
            return {}, f"coordinates[{index}] must be an object"
        if not isinstance(item.get("residue_index"), int) or isinstance(item.get("residue_index"), bool):
            return {}, f"coordinates[{index}].residue_index must be an integer"
        idx = item["residue_index"]
        values = []
        for axis in ("x", "y", "z"):
            if isinstance(item.get(axis), bool):
                return {}, f"coordinates[{index}].{axis} must be a finite number"
            try:
                value = float(item[axis])
            except (KeyError, TypeError, ValueError):
                return {}, f"coordinates[{index}].{axis} must be a finite number"
            if not math.isfinite(value):
                return {}, f"coordinates[{index}].{axis} must be a finite number"
            values.append(value)
        if idx in coords:
            return {}, f"coordinates[{index}].residue_index must be unique"
        coords[idx] = (values[0], values[1], values[2])
    if not coords:
        return {}, "KomodoProteinFold hidden coordinates must not be empty"
    return coords, None


def predicted_protein_coordinates(pred: dict[str, Any]) -> tuple[dict[int, tuple[float, float, float]], dict[str, Any], str | None]:
    has_pdb = "pdb" in pred
    has_mmcif = "mmcif" in pred
    if has_pdb == has_mmcif:
        return {}, {}, "answer must contain exactly one of pdb or mmcif"

    structure_format = "pdb" if has_pdb else "mmcif"
    structure = pred[structure_format]
    if not isinstance(structure, str) or not structure.strip():
        return {}, {}, f"{structure_format} must be a non-empty string"

    if structure_format == "pdb":
        coords, atom_stats = parse_pdb_like_ca_coordinates(structure)
    else:
        coords, atom_stats = parse_mmcif_like_ca_coordinates(structure)
    if not coords:
        return {}, {}, f"{structure_format} does not contain parseable CA coordinates"
    backbone_completeness = backbone_atom_completeness(atom_stats)
    return coords, {
        "structure_format": structure_format,
        "validity": 1.0,
        "backbone_completeness": backbone_completeness,
    }, None


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


def ca_lddt_stats(
    pred: dict[int, tuple[float, float, float]],
    true: dict[int, tuple[float, float, float]],
) -> tuple[dict[str, float], str | None]:
    reference_contacts = 0
    evaluated_contacts = 0
    score_sum = 0.0
    indices = sorted(true)
    for a_pos, i in enumerate(indices):
        for j in indices[a_pos + 1:]:
            true_d = euclidean(true[i], true[j])
            if true_d > LDDT_DISTANCE_CUTOFF_ANGSTROM:
                continue
            reference_contacts += 1
            if i not in pred or j not in pred:
                continue
            evaluated_contacts += 1
            pred_d = euclidean(pred[i], pred[j])
            distance_error = abs(pred_d - true_d)
            score_sum += sum(
                1.0
                for threshold in LDDT_ERROR_THRESHOLDS_ANGSTROM
                if distance_error <= threshold
            ) / len(LDDT_ERROR_THRESHOLDS_ANGSTROM)
    if reference_contacts == 0:
        return {}, "KomodoProteinFold reference coordinates contain no C-alpha contacts within the lDDT cutoff"
    return {
        "ca_lddt": score_sum / reference_contacts,
        "reference_contacts": reference_contacts,
        "evaluated_contacts": evaluated_contacts,
        "missing_contacts": reference_contacts - evaluated_contacts,
    }, None


def euclidean(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)


def pair_f1(pred: set[tuple[int, int]], true: set[tuple[int, int]]) -> dict[str, float]:
    matched = len(pred.intersection(true))
    precision = matched / len(pred) if pred else (1.0 if not true else 0.0)
    recall = matched / len(true) if true else (1.0 if not pred else 0.0)
    return {"precision": precision, "recall": recall, "f1": f1(precision, recall), "matched": matched}


def splice_sequence(sequence: str, introns: list[Any]) -> str:
    pieces = []
    cursor = 0
    for intron in introns:
        start = intron["start"]
        end = intron["end"]
        pieces.append(sequence[cursor:start])
        cursor = end
    pieces.append(sequence[cursor:])
    return "".join(pieces)


def intron_levenshtein_similarity(
    predicted_spliced: str,
    ground_truth_spliced: str,
    original_length: int,
    distance: int | None = None,
) -> float:
    if distance is None:
        distance = levenshtein_distance(predicted_spliced, ground_truth_spliced)
    removed_length = original_length - len(ground_truth_spliced)
    return max(0.0, 1.0 - distance / removed_length)


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


def validate_dot_bracket(dot: str, expected_length: int) -> str | None:
    if len(dot) != expected_length:
        return "dot_bracket length must match the RNA sequence length"
    stack = []
    for index, char in enumerate(dot):
        if char == "(":
            stack.append(index)
        elif char == ")":
            if not stack:
                return "dot_bracket parentheses must be balanced and properly nested"
            stack.pop()
        elif char != ".":
            return "dot_bracket may contain only '.', '(', and ')'"
    if stack:
        return "dot_bracket parentheses must be balanced and properly nested"
    return None


def spearman_order_corr(pred_order: list[str], true_order: list[str]) -> float:
    labels = list(dict.fromkeys(true_order))
    n = len(labels)
    if n < 2:
        return 1.0
    true_ranks = {label: idx + 1 for idx, label in enumerate(true_order)}
    pred_ranks = {label: idx + 1 for idx, label in enumerate(pred_order)}
    a = [float(pred_ranks[label]) for label in labels]
    b = [float(true_ranks[label]) for label in labels]
    return pearson_corr(a, b)


def spearman_score_corr(pred_scores: list[float], true_scores: list[float]) -> float:
    return pearson_corr(average_ranks(pred_scores), average_ranks(true_scores))


def average_ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda idx: values[idx])
    ranks = [0.0] * len(values)
    cursor = 0
    while cursor < len(order):
        end = cursor + 1
        while end < len(order) and values[order[end]] == values[order[cursor]]:
            end += 1
        rank = (cursor + 1 + end) / 2.0
        for pos in range(cursor, end):
            ranks[order[pos]] = rank
        cursor = end
    return ranks


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


def is_probability(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(number) and 0.0 <= number <= 1.0


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))
