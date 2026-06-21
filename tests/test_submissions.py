import json

from dragonbench.submissions import require_submitted_answer, write_answer_artifact


def test_require_submitted_answer_resolves_receipt(tmp_path):
    payload = {"dot_bracket": "((..))"}
    receipt = write_answer_artifact("DBEVAL-V0-091", payload, root=tmp_path)
    answer = "<answer>" + json.dumps({
        "answer_ref": receipt["answer_ref"],
        "sha256": receipt["sha256"],
    }) + "</answer>"

    resolved, info, error = require_submitted_answer(answer, root=tmp_path)

    assert error is None
    assert resolved == payload
    assert info["answer_submission_mode"] == "artifact"
    assert info["answer_sha256"] == receipt["sha256"]


def test_require_submitted_answer_rejects_direct_answer(tmp_path):
    resolved, info, error = require_submitted_answer('<answer>{"dot_bracket":"((..))"}</answer>', root=tmp_path)

    assert resolved == '<answer>{"dot_bracket":"((..))"}</answer>'
    assert info["answer_submission_mode"] == "missing_or_invalid_receipt"
    assert error == "final answer must be the submit_answer receipt with answer_ref"


def test_require_submitted_answer_rejects_checksum_mismatch(tmp_path):
    receipt = write_answer_artifact("DBEVAL-V0-091", {"dot_bracket": "((..))"}, root=tmp_path)
    answer = "<answer>" + json.dumps({
        "answer_ref": receipt["answer_ref"],
        "sha256": "bad",
    }) + "</answer>"

    _, info, error = require_submitted_answer(answer, root=tmp_path)

    assert info["answer_submission_mode"] == "artifact"
    assert error == "answer artifact checksum mismatch"


def test_large_answer_uses_small_receipt(tmp_path):
    payload = {"pdb": "ATOM      1  CA  GLY A   1       0.000   0.000   0.000\n" * 2000}
    receipt = write_answer_artifact("DBEVAL-V0-041", payload, root=tmp_path)
    answer = "<answer>" + json.dumps({
        "answer_ref": receipt["answer_ref"],
        "sha256": receipt["sha256"],
    }) + "</answer>"

    resolved, _, error = require_submitted_answer(answer, root=tmp_path)

    assert error is None
    assert resolved == payload
    assert len(answer) < 500
