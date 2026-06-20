import json
from typing import Any


def render_prompt(card: dict[str, Any]) -> str:
    public_card = {
        "id": card["id"],
        "task": card["task"],
        "source_dataset": card["source"]["primary_dataset"],
        "lineage": card["lineage"],
        "prompt": card["question"]["prompt"],
        "model_input": card["question"]["model_input"],
        "expected_output_schema": card["expected_output_schema"],
        "scoring_primary": card["scoring"]["primary"],
        "dragon_relevance": card["question"]["dragon_relevance"],
    }
    return (
        "You are solving one DragonBench genetics evaluation task.\n"
        "Return only valid JSON matching expected_output_schema. Do not include markdown.\n\n"
        f"{json.dumps(public_card, indent=2, sort_keys=True)}"
    )

