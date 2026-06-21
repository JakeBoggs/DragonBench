import json
from pathlib import Path

from dragonbench.scoring import score_answer


EVAL_PATH = Path("eval/dragonbench_eval_v0.scoreable.jsonl")


def test_tf_binding_candidate_ids_do_not_encode_binding_rank():
    rows = [json.loads(line) for line in EVAL_PATH.read_text().splitlines()]
    tf_rows = [row for row in rows if row["task"] == "DragonTFBind"]
    answer = {
        "binding_probabilities": {
            f"seq_{index:02d}": round(0.9 - 0.8 * (index - 1) / 9, 2)
            for index in range(1, 11)
        }
    }
    rewards = [score_answer(row, answer).reward for row in tf_rows]

    assert len(tf_rows) == 20
    assert sum(rewards) / len(rewards) < 0.5
    assert max(rewards) < 0.75
