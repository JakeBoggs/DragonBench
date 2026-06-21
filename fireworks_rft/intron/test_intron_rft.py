"""Fireworks Eval Protocol evaluator for DragonBench intron RFT."""

import json
from pathlib import Path
from typing import Any

from eval_protocol.models import (
    EvaluateResult,
    EvaluationRow,
    InputMetadata,
    Message,
    MetricResult,
    StepOutput,
)
from eval_protocol.pytest.evaluation_test import evaluation_test

from dragonbench.rl.intron_reward import parse_intron_response, parse_label
from dragonbench.scoring import score_gene_parse_introns


DATA_DIR = Path(__file__).resolve().parent / "data"
TRAIN_DATASET = DATA_DIR / "rl_non_eval" / "train.jsonl"


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
            else:
                parts.append(getattr(item, "text", ""))
        return "".join(parts)
    return "" if content is None else str(content)


def intron_dataset_adapter(rows: list[dict[str, Any]]) -> list[EvaluationRow]:
    """Convert DragonBench intron RL rows into Eval Protocol rows."""
    eval_rows: list[EvaluationRow] = []
    for row in rows:
        if "label" in row:
            label = json.loads(row["label"]) if isinstance(row.get("label"), str) else row["label"]
        elif "ground_truth" in row:
            label = json.loads(row["ground_truth"]) if isinstance(row.get("ground_truth"), str) else row["ground_truth"]
        else:
            raise KeyError("intron dataset row requires either 'label' or 'ground_truth'")

        _expected, sequence = parse_label(label)
        metadata = row.get("input_metadata") or {}
        dataset_info = metadata.get("dataset_info") or {}
        question_id = row.get("question_id") or metadata.get("row_id") or dataset_info.get("question_id") or "unknown"
        messages = [message if isinstance(message, Message) else Message(**message) for message in row["messages"]]
        eval_rows.append(
            EvaluationRow(
                messages=messages,
                ground_truth=label,
                input_metadata=InputMetadata(
                    row_id=str(question_id),
                    dataset_info={
                        "task": "AnoleGeneParse",
                        "question_id": question_id,
                        "sequence_length": len(sequence),
                        "n_true_introns": len(label["answer"].get("introns", [])),
                    },
                ),
            )
        )
    return eval_rows


@evaluation_test(
    input_dataset=[str(TRAIN_DATASET)],
    dataset_adapter=intron_dataset_adapter,
    completion_params=[
        {
            "model": "fireworks_ai/accounts/fireworks/models/gpt-oss-120b",
            "temperature": 0.8,
            "max_tokens": 4096,
            "extra_body": {"reasoning_effort": "low"},
        }
    ],
    aggregation_method="mean",
    passed_threshold=0.0,
    max_dataset_rows=1,
    max_concurrent_rollouts=1,
    max_concurrent_evaluations=1,
    mode="pointwise",
)
def test_dragonbench_intron_rft(row: EvaluationRow) -> EvaluationRow:
    """Score the last assistant message with the production intron reward."""
    assistant = row.last_assistant_message()
    response = _content_to_text(assistant.content if assistant else "")
    expected, sequence = parse_label(row.ground_truth)
    parsed, parse_error = parse_intron_response(response)

    if parse_error:
        row.evaluation_result = EvaluateResult(
            score=0.0,
            reason=f"Invalid answer format: {parse_error}",
            is_score_valid=True,
            metrics={
                "parse_valid": MetricResult(
                    score=0.0,
                    reason=parse_error,
                    data={"response_prefix": response[:500]},
                )
            },
            step_outputs=[
                StepOutput(
                    step_index=0,
                    base_reward=0.0,
                    terminated=True,
                    reason=f"Invalid answer format: {parse_error}",
                )
            ],
        )
        return row

    result = score_gene_parse_introns(parsed or {}, expected, sequence)
    metrics = {
        name: MetricResult(score=float(value), reason=name, data={})
        for name, value in result.subscores.items()
    }
    metrics["parse_valid"] = MetricResult(score=1.0, reason="Parsed final answer block", data={})

    row.evaluation_result = EvaluateResult(
        score=float(result.reward),
        reason=result.status,
        is_score_valid=True,
        metrics=metrics,
        step_outputs=[
            StepOutput(
                step_index=0,
                base_reward=float(result.reward),
                terminated=True,
                control_plane_info={
                    "task": "AnoleGeneParse",
                    "status": result.status,
                    **result.info,
                },
                metrics={name: float(value) for name, value in result.subscores.items()},
                reason=(
                    "Reward is spliced-sequence Levenshtein similarity when the "
                    "sequence is available; interval F1, boundary score, and count "
                    "accuracy are diagnostics."
                ),
            )
        ],
    )
    return row
