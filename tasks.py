import os
import hashlib
import json
import warnings
from pathlib import Path
from typing import Any
from urllib.parse import quote

from dragonbench.hud_runtime_isolation import install_hud_runtime_isolation
from dragonbench.io import load_jsonl
from dragonbench.logging import log_score_event, make_score_event
from dragonbench.prompts import render_prompt
from dragonbench.scoring import ScoreResult, score_answer
from dragonbench.submissions import require_submitted_answer, write_answer_artifact

install_hud_runtime_isolation()

try:
    from hud import Environment, Taskset
except ImportError as exc:  # pragma: no cover - exercised only without hud-python installed.
    raise RuntimeError(
        "HUD SDK is not installed. Install it with `pip install hud-python` or `uv tool install hud-python --python 3.12`."
    ) from exc


DATASET_PATH = Path(__file__).parent / "eval" / "dragonbench_eval_v0.scoreable.jsonl"
PROTEIN_TASKS = {"KomodoProteinFold"}
env = Environment(name="dragonbench-eval-v0")


def answer_digest(answer):
    return hashlib.sha256(str(answer).encode("utf-8", errors="replace")).hexdigest()[:12]


def make_trace_report(card, answer):
    from scripts.build_protein_3d_report import build_single_task_report

    report_dir = Path(os.environ.get("DRAGONBENCH_TRACE_VIZ_DIR", "reports/hud"))
    report_path = report_dir / f"{card['id']}-{answer_digest(answer)}.html"
    build_single_task_report(card, answer, report_path, model_name="HUD Model")
    return report_path


def make_visualization_info(card, answer=None):
    if card.get("task") not in PROTEIN_TASKS:
        return {}
    base_url = os.environ.get("DRAGONBENCH_VIZ_BASE_URL", "").strip()
    if not base_url:
        return {
            "visualization_status": "disabled",
            "visualization_reason": "Set DRAGONBENCH_VIZ_BASE_URL to emit a protein viewer link.",
        }
    try:
        report_path = make_trace_report(card, answer) if answer is not None else None
        source = "hud_model_answer"
    except Exception as exc:
        report_path = None
        source = "static_fallback"
        report_error = str(exc)
    if report_path is None:
        report_path = os.environ.get("DRAGONBENCH_PROTEIN_VIZ_REPORT", "reports/protein_folding_3d.html").strip()
        report_path = report_path or "reports/protein_folding_3d.html"
    report_path_str = str(report_path)
    url = f"{base_url.rstrip('/')}/{report_path_str.lstrip('/')}?task_id={quote(card['id'], safe='')}"
    is_local = base_url.startswith(("http://127.0.0.1", "http://localhost", "http://0.0.0.0"))
    info = {
        "visualization_status": "local_only" if is_local else "public_url",
        "visualization_mode": "single_answer",
        "visualization_source": source,
        "visualization_url": url,
        "visualization": {
            "kind": "protein_single_answer_structure",
            "viewer": "3dmol",
            "mode": "single_answer",
            "task_id": card["id"],
            "url": url,
            "source": source,
            "note": (
                "Localhost URLs only work in a browser on the same machine running the report server."
                if is_local else
                "Public URL should be reachable from the HUD website and other browsers."
            ),
        }
    }
    if source == "static_fallback":
        info["visualization_error"] = report_error
        info["visualization"]["note"] += " Trace-specific report generation failed; this link uses the configured single-answer fallback report."
    return info


def make_result_content(card, result, info):
    lines = [
        f"{card['id']} {card['task']} scored {result.reward:.3f} ({result.status})."
    ]
    if "visualization_url" in info:
        lines.append(f"Protein visualization: {info['visualization_url']}")
        if info.get("visualization_status") == "local_only":
            lines.append("Visualization status: local-only URL; open it from the same machine running the report server.")
    elif info.get("visualization_status") == "disabled":
        lines.append(f"Protein visualization disabled: {info['visualization_reason']}")
    return "\n".join(lines)


def submit_answer(question_id: str, answer_json: str) -> dict[str, Any]:
    """Store a final DragonBench answer and return the small receipt to place in <answer>."""
    cards = {card["id"]: card for card in load_jsonl(DATASET_PATH)}
    if question_id not in cards:
        return {
            "ok": False,
            "error": f"unknown question_id: {question_id}",
            "known_question_ids": sorted(cards),
        }
    try:
        answer = json.loads(answer_json)
    except json.JSONDecodeError as exc:
        return {"ok": False, "error": f"answer_json must be valid JSON: {exc}"}
    if not isinstance(answer, dict):
        return {"ok": False, "error": "answer_json must decode to a JSON object"}

    try:
        receipt = write_answer_artifact(question_id, answer)
    except (OSError, TypeError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}

    final_answer = {
        "answer_ref": receipt["answer_ref"],
        "sha256": receipt["sha256"],
    }
    return {
        "ok": True,
        **receipt,
        "final_answer": final_answer,
        "final_answer_block": f"<answer>{json.dumps(final_answer, separators=(',', ':'))}</answer>",
    }


with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    env.tool(submit_answer)


@env.template()
async def dragonbench_question(question_id: str):
    cards = {card["id"]: card for card in load_jsonl(DATASET_PATH)}
    card = cards[question_id]
    answer = yield render_prompt(card)
    resolved_answer, submission_info, resolve_error = require_submitted_answer(answer)
    if resolve_error:
        result = ScoreResult(
            0.0,
            "invalid_answer_ref",
            {"answer_ref": 0.0},
            {"error": resolve_error},
        )
    else:
        result = score_answer(card, resolved_answer)
    log_score_event(card, result, resolved_answer, emit_stdout=True, include_answer_preview=False)
    event = make_score_event(card, result, include_answer_preview=False)
    info = dict(result.info)
    info.update(submission_info)
    info.update(make_visualization_info(card, resolved_answer))
    yield {
        "score": result.reward,
        "content": make_result_content(card, result, info),
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
