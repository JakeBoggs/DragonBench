import os
from pathlib import Path
from urllib.parse import quote

from dragonbench.io import load_jsonl
from dragonbench.logging import log_score_event, make_score_event
from dragonbench.prompts import render_prompt
from dragonbench.scoring import score_answer

try:
    from hud import Environment, Taskset
except ImportError as exc:  # pragma: no cover - exercised only without hud-python installed.
    raise RuntimeError(
        "HUD SDK is not installed. Install it with `pip install hud-python` or `uv tool install hud-python --python 3.12`."
    ) from exc


DATASET_PATH = Path(__file__).parent / "eval" / "dragonbench_eval_v0.scoreable.jsonl"
PROTEIN_TASKS = {"KomodoProteinFold"}
env = Environment(name="dragonbench-eval-v0")


def make_visualization_info(card):
    if card.get("task") not in PROTEIN_TASKS:
        return {}
    base_url = os.environ.get("DRAGONBENCH_VIZ_BASE_URL", "").strip()
    if not base_url:
        return {}
    report_path = os.environ.get("DRAGONBENCH_PROTEIN_VIZ_REPORT", "reports/protein_folding_compare.html").strip()
    report_path = report_path or "reports/protein_folding_compare.html"
    url = f"{base_url.rstrip('/')}/{report_path.lstrip('/')}?task_id={quote(card['id'], safe='')}"
    return {
        "visualization_url": url,
        "visualization": {
            "kind": "protein_structure_comparison",
            "viewer": "3dmol",
            "task_id": card["id"],
            "url": url,
        }
    }


@env.template()
async def dragonbench_question(question_id: str):
    cards = {card["id"]: card for card in load_jsonl(DATASET_PATH)}
    card = cards[question_id]
    answer = yield render_prompt(card)
    result = score_answer(card, answer)
    log_score_event(card, result, answer, emit_stdout=True)
    event = make_score_event(card, result, include_answer_preview=False)
    info = dict(result.info)
    info.update(make_visualization_info(card))
    yield {
        "score": result.reward,
        "status": result.status,
        "subscores": result.subscores,
        "info": info,
        "scoring_explanation": event["scoring_explanation"],
        "format_contract": event["format_contract"],
    }


tasks = Taskset(
    "dragonbench-eval-v0-seed",
    [
        dragonbench_question(question_id=card["id"])
        for card in load_jsonl(DATASET_PATH)
    ],
)
