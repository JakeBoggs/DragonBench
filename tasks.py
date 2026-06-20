from pathlib import Path

from dragonbench.io import load_jsonl
from dragonbench.logging import log_score_event
from dragonbench.prompts import render_prompt
from dragonbench.scoring import score_answer

try:
    from hud import Environment, Taskset
except ImportError as exc:  # pragma: no cover - exercised only without hud-python installed.
    raise RuntimeError(
        "HUD SDK is not installed. Install it with `pip install hud-python` or `uv tool install hud-python --python 3.12`."
    ) from exc


DATASET_PATH = Path(__file__).parent / "eval" / "dragonbench_eval_v0.scoreable.jsonl"
env = Environment(name="dragonbench-eval-v0")


@env.template()
async def dragonbench_question(question_id: str):
    cards = {card["id"]: card for card in load_jsonl(DATASET_PATH)}
    card = cards[question_id]
    answer = yield render_prompt(card)
    result = score_answer(card, answer)
    log_score_event(card, result, answer)
    yield result.reward


tasks = Taskset(
    "dragonbench-eval-v0-seed",
    [
        dragonbench_question(question_id=card["id"])
        for card in load_jsonl(DATASET_PATH)
    ],
)
