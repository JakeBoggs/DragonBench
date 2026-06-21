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
        "id": card["id"],
        "task": card["task"],
        "lineage": card["lineage"],
        "status": result.status,
        "reward": result.reward,
        "primary_scorer": card["scoring"]["primary"],
        "secondary_scorers": card["scoring"]["secondary"],
        "subscores": result.subscores,
        "info": result.info,
        "scoring_explanation": explain_scoring(card, result),
        "format_contract": (
            "Return one JSON object matching the task's required answer schema. "
            "Markdown fences and explanatory text are not part of the answer."
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
            f"Values: spliced_similarity={s['spliced_sequence_levenshtein_similarity']:.3f}, "
            f"intron_F1={s['intron_interval_f1_at_iou_0_8']:.3f}, "
            f"boundary={s['intron_boundary_score']:.3f}, "
            f"count={s['intron_count_accuracy']:.3f}, "
            f"reward={result.reward:.3f}."
        )
    if task == "AnolePromoterExpression":
        return (
            "A valid answer must rank every candidate tissue exactly once. "
            "Reward = max(0, Spearman rank correlation). "
            f"Values: spearman={s['spearman_rank_correlation']:.3f}, "
            f"complete={s['ranking_completeness']:.3f}, "
            f"reward={result.reward:.3f}."
        )
    if task == "KomodoProteinFold":
        return (
            "Reward = C-alpha lDDT over reference residue pairs within 15 Å; missing predicted residues contribute zero for affected pairs. "
            "Each pair gets fractional credit for distance errors under 0.5, 1, 2, and 4 Å. "
            f"Values: ca_lDDT={s['ca_lddt']:.3f}, "
            f"coverage={s['coordinate_coverage']:.3f}, "
            f"validity={s['structure_validity']:.3f}, "
            f"backbone={s['backbone_atom_completeness']:.3f}, "
            f"contacts={s['lddt_evaluated_contacts']:.0f}/{s['lddt_reference_contacts']:.0f}, "
            f"reward={result.reward:.3f}."
        )
    if task == "DragonTFBind":
        return (
            "A valid answer must provide one probability for every candidate DNA sequence ID. "
            "Reward = max(0, Spearman rank correlation) over predicted and reference binding probabilities. "
            f"Values: spearman={s['spearman_rank_correlation']:.3f}, "
            f"reward={result.reward:.3f}."
        )
    if task == "RNAFold":
        return (
            "A valid answer must be a balanced dot-bracket string with one character per RNA nucleotide. "
            "Reward = base_pair_f1. "
            f"Values: F1={s['base_pair_f1']:.3f}, "
            f"precision={s['base_pair_precision']:.3f}, "
            f"recall={s['base_pair_recall']:.3f}, "
            f"exact={s['exact_dot_bracket_match']:.3f}, "
            f"reward={result.reward:.3f}."
        )
    return f"Reward={result.reward:.3f}; subscores={json.dumps(result.subscores, sort_keys=True)}."
