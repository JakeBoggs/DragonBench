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
    }
    if answer is not None and include_answer_preview:
        text = answer if isinstance(answer, str) else json.dumps(answer, sort_keys=True)
        event["answer_preview"] = text[:500]
        event["answer_chars"] = len(text)
    return event


def log_score_event(card: dict[str, Any], result: ScoreResult, answer: Any | None = None, include_answer_preview: bool = True) -> None:
    if not score_logging_enabled():
        return
    path = score_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    event = make_score_event(card, result, answer, include_answer_preview=include_answer_preview)
    with path.open("a") as f:
        f.write(json.dumps(event, sort_keys=True) + "\n")
