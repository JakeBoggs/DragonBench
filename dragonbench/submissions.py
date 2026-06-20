import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

from dragonbench.scoring import parse_model_json


ANSWER_ARTIFACT_SCHEMA_VERSION = 1


def answer_artifact_root(root: str | Path | None = None) -> Path:
    configured = root if root is not None else os.environ.get("DRAGONBENCH_ANSWER_ARTIFACT_DIR", "runs/hud_answers")
    return Path(configured)


def safe_question_id(question_id: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "-", str(question_id)).strip(".-")
    return cleaned or "unknown-question"


def canonical_answer_json(answer: Any) -> str:
    return json.dumps(answer, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def answer_sha256(answer: Any) -> str:
    return hashlib.sha256(canonical_answer_json(answer).encode("utf-8")).hexdigest()


def write_answer_artifact(question_id: str, answer: Any, root: str | Path | None = None) -> dict[str, Any]:
    digest = answer_sha256(answer)
    artifact_root = answer_artifact_root(root)
    question_dir = artifact_root / safe_question_id(question_id)
    question_dir.mkdir(parents=True, exist_ok=True)
    path = question_dir / f"{digest[:16]}.json"
    record = {
        "schema_version": ANSWER_ARTIFACT_SCHEMA_VERSION,
        "question_id": question_id,
        "sha256": digest,
        "answer": answer,
    }
    path.write_text(json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2), encoding="utf-8")
    return {
        "answer_ref": str(path),
        "question_id": question_id,
        "sha256": digest,
    }


def require_submitted_answer(answer: Any, root: str | Path | None = None) -> tuple[Any, dict[str, Any], str | None]:
    parsed, error = parse_model_json(answer)
    if error:
        return answer, {"answer_submission_mode": "missing_or_invalid_receipt"}, error
    if not isinstance(parsed, dict) or "answer_ref" not in parsed:
        return answer, {
            "answer_submission_mode": "missing_or_invalid_receipt",
        }, "final answer must be the submit_answer receipt with answer_ref"

    ref = parsed.get("answer_ref")
    try:
        record, path = read_answer_artifact(ref, root=root)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return answer, {"answer_submission_mode": "artifact", "answer_ref": ref}, str(exc)

    expected_sha = parsed.get("sha256") or parsed.get("answer_sha256")
    actual_sha = record.get("sha256")
    if expected_sha and expected_sha != actual_sha:
        return answer, {
            "answer_submission_mode": "artifact",
            "answer_ref": str(path),
            "answer_sha256": actual_sha,
        }, "answer artifact checksum mismatch"

    return record.get("answer"), {
        "answer_submission_mode": "artifact",
        "answer_ref": str(path),
        "answer_sha256": actual_sha,
    }, None


def read_answer_artifact(answer_ref: Any, root: str | Path | None = None) -> tuple[dict[str, Any], Path]:
    if not isinstance(answer_ref, str) or not answer_ref.strip():
        raise ValueError("answer_ref must be a non-empty string")
    if "://" in answer_ref:
        raise ValueError("answer_ref must be a local artifact path")

    artifact_root = answer_artifact_root(root).resolve()
    ref_path = Path(answer_ref)
    path = ref_path.resolve() if ref_path.is_absolute() else (Path.cwd() / ref_path).resolve()
    if artifact_root != path and artifact_root not in path.parents:
        raise ValueError("answer_ref is outside the configured artifact root")

    record = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(record, dict):
        raise ValueError("answer artifact must contain a JSON object")
    if record.get("schema_version") != ANSWER_ARTIFACT_SCHEMA_VERSION:
        raise ValueError("unsupported answer artifact schema version")
    if "answer" not in record:
        raise ValueError("answer artifact is missing answer")

    actual_sha = answer_sha256(record["answer"])
    if record.get("sha256") != actual_sha:
        raise ValueError("answer artifact content checksum mismatch")
    return record, path
