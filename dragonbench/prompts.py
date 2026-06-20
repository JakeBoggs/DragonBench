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
    }
    return (
        "Solve the task. Submit your final JSON answer by calling the submit_answer tool.\n"
        "The submit_answer tool arguments are question_id and answer. The answer argument must be the JSON object matching expected_output_schema.\n"
        "After the tool call succeeds, your final answer must be the last thing in your response.\n"
        "You may reason before the answer. If you revise your answer, only the last answer block will be scored.\n"
        "The block tag must be lowercase exactly as <answer>...</answer>.\n"
        "Inside <answer>, write only the JSON receipt returned by submit_answer: answer_ref and sha256.\n"
        "Direct answers inside <answer> are invalid and score 0. Do not place the task answer JSON directly in the final block.\n"
        "The scorer parses the last lowercase <answer> block. Zero lowercase blocks, uppercase tags, or malformed JSON in the final block score 0.\n\n"
        "Required final format:\n"
        "<answer>{\"answer_ref\":\"runs/hud_answers/DBEVAL-V0-001/abc123.json\",\"sha256\":\"...\"}</answer>\n\n"
        f"{json.dumps(public_card, indent=2, sort_keys=True)}\n\n"
        "FINAL REMINDER: call submit_answer, then end with a lowercase final receipt block: <answer>{\"answer_ref\":\"...\",\"sha256\":\"...\"}</answer>"
    )
