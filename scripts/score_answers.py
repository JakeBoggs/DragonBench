import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dragonbench.io import load_jsonl
from dragonbench.logging import log_score_event
from dragonbench.scoring import score_answer


def main() -> None:
    parser = argparse.ArgumentParser(description="Score DragonBench answer JSONL locally.")
    parser.add_argument("--dataset", default="data/eval/dragonbench_eval_v0.scoreable.jsonl")
    parser.add_argument("--answers", required=True, help="JSONL with fields id and answer.")
    parser.add_argument("--out", default=None)
    parser.add_argument("--no-log", action="store_true", help="Do not append score events to logs/score_events.jsonl.")
    parser.add_argument("--log-answer-preview", action="store_true", help="Include truncated answer previews in score logs.")
    args = parser.parse_args()

    cards = {row["id"]: row for row in load_jsonl(args.dataset)}
    rows = []
    for item in load_jsonl(args.answers):
        card = cards[item["id"]]
        result = score_answer(card, item.get("answer"))
        if not args.no_log:
            log_score_event(card, result, item.get("answer"), include_answer_preview=args.log_answer_preview)
        rows.append({
            "id": item["id"],
            "task": card["task"],
            "reward": result.reward,
            "status": result.status,
            "subscores": result.subscores,
            "info": result.info,
        })

    if args.out:
        target = Path(args.out)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w") as f:
            for row in rows:
                f.write(json.dumps(row, sort_keys=True) + "\n")
    else:
        print(json.dumps({
            "n": len(rows),
            "mean_reward": sum(r["reward"] for r in rows) / len(rows) if rows else 0.0,
            "statuses": {status: sum(1 for r in rows if r["status"] == status) for status in sorted({r["status"] for r in rows})}
        }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
