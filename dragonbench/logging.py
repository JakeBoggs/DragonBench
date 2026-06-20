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
        "format_contract": "Model output is parsed from the last lowercase <answer>...</answer> block containing valid JSON. Exact raw JSON is also accepted by local tooling.",
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
    if task == "DragonGeneParseIntrons":
        return (
            "Reward = 0.75 * intron_interval_f1_at_iou_0_8 "
            "+ 0.15 * intron_boundary_score + 0.10 * intron_count_accuracy. "
            f"Values: F1={s.get('intron_interval_f1_at_iou_0_8', 0):.3f}, "
            f"boundary={s.get('intron_boundary_score', 0):.3f}, "
            f"count={s.get('intron_count_accuracy', 0):.3f}, "
            f"reward={result.reward:.3f}."
        )
    if task == "DragonAnolePromoterExpression":
        return (
            "Reward = 0.55 * ndcg_at_all_tissues + 0.20 * top1_tissue_accuracy "
            "+ 0.20 * spearman_rank_scaled + 0.05 * ranking_completeness. "
            f"Values: NDCG={s.get('ndcg_at_all_tissues', 0):.3f}, "
            f"top1={s.get('top1_tissue_accuracy', 0):.3f}, "
            f"spearman_scaled={s.get('spearman_rank_scaled', 0):.3f}, "
            f"complete={s.get('ranking_completeness', 0):.3f}, "
            f"reward={result.reward:.3f}."
        )
    if task == "DragonProteinFolding":
        return (
            "Reward = 0.90 * contact_f1_long_range_tolerance_0 + 0.10 * contact_count_accuracy. "
            f"Values: F1={s.get('contact_f1_long_range_tolerance_0', 0):.3f}, "
            f"precision={s.get('contact_precision', 0):.3f}, "
            f"recall={s.get('contact_recall', 0):.3f}, "
            f"count={s.get('contact_count_accuracy', 0):.3f}, "
            f"reward={result.reward:.3f}."
        )
    if task == "DragonTFBind":
        return (
            "Reward = 0.80 * interval_f1_at_iou_0_5 + 0.15 * center_distance_score "
            "+ 0.05 * confidence_presence. "
            f"Values: F1={s.get('interval_f1_at_iou_0_5', 0):.3f}, "
            f"precision={s.get('precision', 0):.3f}, "
            f"recall={s.get('recall', 0):.3f}, "
            f"center={s.get('center_distance_score', 0):.3f}, "
            f"confidence={s.get('confidence_presence', 0):.3f}, "
            f"reward={result.reward:.3f}."
        )
    if task == "DragonRNAFolding":
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
