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
    if card["task"] == "KomodoProteinFold":
        public_card["hud_transport_constraint"] = (
            "Keep the final <answer> JSON under 60000 characters. HUD grading transport can reject larger answers. "
            "If a complete PDB/mmCIF would exceed this limit, emit compact coordinates instead: "
            "{\"coordinates\":[{\"residue_index\":0,\"x\":0.0,\"y\":0.0,\"z\":0.0},...]}. "
            "The scorer accepts either PDB/mmCIF text or this compact coordinate array."
        )
    return (
        "Solve the task. Your final answer must be the last thing in your response.\n"
        "You may reason before the answer. If you revise your answer, only the last answer block will be scored.\n"
        "The block tag must be lowercase exactly as <answer>...</answer>.\n"
        "Inside <answer>, write only valid JSON matching expected_output_schema.\n"
        "If a task includes hud_transport_constraint, follow it even when it offers a compact scorer-supported alternative to the displayed schema.\n"
        "The scorer parses the last lowercase <answer> block. Zero lowercase blocks, uppercase tags, or malformed JSON in the final block score 0.\n\n"
        "Required final format:\n"
        "<answer>{\"field\": \"value\"}</answer>\n\n"
        f"{json.dumps(public_card, indent=2, sort_keys=True)}\n\n"
        "FINAL REMINDER: end with a lowercase final block: <answer>{...}</answer>"
    )
