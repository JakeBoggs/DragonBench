import json
import os
import time
from pathlib import Path
from typing import Any

from dragonbench.scoring import ScoreResult


DEFAULT_LOG_PATH = Path("logs/score_events.jsonl")


def score_logging_enabled() -> bool:
    return os.environ.get("DRAGONBENCH_SCORE_LOG", "1").lower() not in {"0", "false", "no", "off"}


def score_log_path() -> Path:
    return Path(os.environ.get("DRAGONBENCH_SCORE_LOG_PATH", str(DEFAULT_LOG_PATH)))


def stdout_score_logging_enabled() -> bool:
    return os.environ.get("DRAGONBENCH_SCORE_STDOUT", "0").lower() in {"1", "true", "yes", "on"}


def make_score_event(card: dict[str, Any], result: ScoreResult, answer: Any | None = None, include_answer_preview: bool = True) -> dict[str, Any]:
    event = {
        "ts": time.time(),
        "id": card.get("id"),
        "task": card.get("task"),
        "lineage": card.get("lineage"),
        "status": result.status,
        "reward": result.reward,
        "primary_scorer": card.get("scoring", {}).get("primary"),
        "secondary_scorers": card.get("scoring", {}).get("secondary", []),
        "subscores": result.subscores,
        "info": result.info,
        "scoring_explanation": explain_scoring(card, result),
        "format_contract": (
            "HUD eval output must end with a final lowercase <answer>...</answer> block containing "
            "the submit_answer receipt JSON: answer_ref and sha256. Direct task answers in the final "
            "block are invalid for HUD grading."
        ),
    }
    if answer is not None and include_answer_preview:
        text = answer if isinstance(answer, str) else json.dumps(answer, sort_keys=True)
        event["answer_preview"] = text[:500]
        event["answer_chars"] = len(text)
    return event


def log_score_event(
    card: dict[str, Any],
    result: ScoreResult,
    answer: Any | None = None,
    include_answer_preview: bool = True,
    emit_stdout: bool = False,
) -> dict[str, Any] | None:
    if not score_logging_enabled():
        return None
    path = score_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    event = make_score_event(card, result, answer, include_answer_preview=include_answer_preview)
    with path.open("a") as f:
        f.write(json.dumps(event, sort_keys=True) + "\n")
    if emit_stdout or stdout_score_logging_enabled():
        print("DRAGONBENCH_SCORE_EVENT " + json.dumps(event, sort_keys=True), flush=True)
    return event


def explain_scoring(card: dict[str, Any], result: ScoreResult) -> str:
    task = card.get("task")
    s = result.subscores
    if result.status != "scored":
        return (
            f"Format/scoring status is {result.status}. Reward is {result.reward:.3f}. "
            f"Details: {json.dumps(result.info, sort_keys=True)}"
        )
    if task == "AnoleGeneParse":
        return (
            "Reward = max(0, 1 - spliced-sequence Levenshtein distance / ground-truth intron length). "
            f"Values: spliced_similarity={s.get('spliced_sequence_levenshtein_similarity', 0):.3f}, "
            f"intron_F1={s.get('intron_interval_f1_at_iou_0_8', 0):.3f}, "
            f"boundary={s.get('intron_boundary_score', 0):.3f}, "
            f"count={s.get('intron_count_accuracy', 0):.3f}, "
            f"reward={result.reward:.3f}."
        )
    if task == "AnolePromoterExpression":
        return (
            "A valid answer must rank every candidate tissue exactly once. "
            "Reward = max(0, Spearman rank correlation). "
            f"Values: spearman={s.get('spearman_rank_correlation', 0):.3f}, "
            f"top1={s.get('top1_tissue_accuracy', 0):.3f}, "
            f"complete={s.get('ranking_completeness', 0):.3f}, "
            f"reward={result.reward:.3f}."
        )
    if task == "KomodoProteinFold":
        return (
            "Reward = coordinate_coverage * local_structure_score. "
            "local_structure_score = 0.90 * distance_matrix_rmsd_score + 0.05 * structure_validity + 0.05 * backbone_atom_completeness. "
            "distance_matrix_rmsd_score = 1 / (1 + dRMSD / 2), where dRMSD compares all pairwise C-alpha distances and is rotation/translation invariant. "
            f"Values: dRMSD_score={s.get('distance_matrix_rmsd_score', 0):.3f}, "
            f"coverage={s.get('coordinate_coverage', 0):.3f}, "
            f"local_structure={s.get('local_structure_score', 0):.3f}, "
            f"validity={s.get('structure_validity', 0):.3f}, "
            f"backbone={s.get('backbone_atom_completeness', 0):.3f}, "
            f"dRMSD={s.get('drmsd_angstrom', 0):.3f}, "
            f"mean_distance_error={s.get('mean_distance_error_angstrom', 0):.3f}, "
            f"reward={result.reward:.3f}."
        )
    if task == "DragonTFBind":
        return (
            "Reward = 0.40 * AUROC + 0.35 * AUPRC + 0.20 * ranking_accuracy + 0.05 * brier_score. "
            f"Values: AUROC={s.get('auroc', 0):.3f}, "
            f"AUPRC={s.get('auprc', 0):.3f}, "
            f"ranking={s.get('ranking_accuracy', 0):.3f}, "
            f"brier={s.get('brier_score', 0):.3f}, "
            f"reward={result.reward:.3f}."
        )
    if task == "RNAFold":
        return (
            "Reward = 0.80 * base_pair_f1 + 0.15 * exact_dot_bracket_match "
            "+ 0.05 * length_validity. "
            f"Values: F1={s.get('base_pair_f1', 0):.3f}, "
            f"precision={s.get('base_pair_precision', 0):.3f}, "
            f"recall={s.get('base_pair_recall', 0):.3f}, "
            f"exact={s.get('exact_dot_bracket_match', 0):.3f}, "
            f"length={s.get('length_validity', 0):.3f}, "
            f"reward={result.reward:.3f}."
        )
    return f"Reward={result.reward:.3f}; subscores={json.dumps(result.subscores, sort_keys=True)}."
