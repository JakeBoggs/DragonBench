"""Reward helpers for AnoleGeneParse intron-span RL."""

from __future__ import annotations

import json
import re
from typing import Any

from dragonbench.scoring import parse_model_json, score_gene_parse_introns

ANSWER_RE = re.compile(r"<answer>\s*(.*?)\s*</answer>", re.DOTALL)


def parse_label(label: Any) -> tuple[dict[str, Any], str]:
    """Decode a Training Gym/Slime label into expected answer and sequence."""
    if isinstance(label, str):
        label = json.loads(label)
    if not isinstance(label, dict):
        raise ValueError("intron label must be a JSON object or JSON object string")
    answer = label.get("answer")
    sequence = label.get("sequence")
    if not isinstance(answer, dict) or not isinstance(sequence, str):
        raise ValueError("intron label requires answer object and sequence string")
    return answer, sequence


def parse_intron_response(response: str) -> tuple[dict[str, Any] | None, str | None]:
    """Parse the last explicit answer block, then fall back to exact JSON."""
    matches = ANSWER_RE.findall(str(response))
    if matches:
        return parse_model_json(matches[-1])
    return parse_model_json(response)


def score_intron_response(response: str, label: Any) -> float:
    """Return the deterministic DragonBench intron reward."""
    expected, sequence = parse_label(label)
    parsed, error = parse_intron_response(response)
    if error:
        return 0.0
    result = score_gene_parse_introns(parsed or {}, expected, sequence)
    return float(result.reward)


def intron_eval_response_fn(example: dict[str, Any], response: str):
    """Training Gym eval hook for intron-span prediction."""
    from modal_training_gym import EvalRowResult

    score = score_intron_response(response, example["label"])
    return EvalRowResult(
        score=score,
        response=response,
        metadata={
            "question_id": example.get("question_id"),
            "task": "AnoleGeneParse",
        },
    )


async def intron_rm(args, sample, **kwargs) -> float:
    """Slime custom reward model function used by Modal Training Gym."""
    return score_intron_response(sample.response, sample.label)
