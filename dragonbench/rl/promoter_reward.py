"""Reward helpers for promoter-expression RL.

The training target is the same JSON contract as the eval task:

    <answer>{"tissue_ranking": ["liver", ...]}</answer>
"""

from __future__ import annotations

import json
from typing import Any

from dragonbench.scoring import parse_model_json, score_promoter_expression_ranking


def parse_label(label: Any) -> dict[str, Any]:
    """Decode a Training Gym/Slime label into a DragonBench hidden answer."""
    if isinstance(label, dict):
        return label
    if isinstance(label, str):
        parsed = json.loads(label)
        if isinstance(parsed, dict):
            return parsed
    raise ValueError("promoter label must be a JSON object or JSON object string")


def score_promoter_response(response: str, label: Any) -> float:
    """Return the deterministic DragonBench promoter-expression reward."""
    expected = parse_label(label)
    parsed, error = parse_model_json(response)
    if error:
        return 0.0
    result = score_promoter_expression_ranking(parsed or {}, expected)
    return float(result.reward)


def promoter_eval_response_fn(example: dict[str, Any], response: str):
    """Training Gym eval hook for promoter-expression ranking."""
    from modal_training_gym import EvalRowResult

    score = score_promoter_response(response, example["label"])
    return EvalRowResult(
        score=score,
        response=response,
        metadata={
            "question_id": example.get("question_id"),
            "task": "AnolePromoterExpression",
        },
    )


async def promoter_expression_rm(args, sample, **kwargs) -> float:
    """Slime custom reward model function used by Modal Training Gym."""
    return score_promoter_response(sample.response, sample.label)
