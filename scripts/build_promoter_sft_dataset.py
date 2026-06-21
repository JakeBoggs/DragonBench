#!/usr/bin/env python3
"""Write DragonBench promoter-expression SFT JSONL splits locally."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dragonbench.rl.promoter_dataset import DragonBenchPromoterDataset, card_to_sft_row


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, separators=(",", ":")) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="eval/dragonbench_eval_v0.scoreable.jsonl")
    parser.add_argument("--out-dir", default="runs/promoter_sft_dataset")
    parser.add_argument("--n-train", type=int, default=20)
    parser.add_argument("--n-eval", type=int, default=20)
    parser.add_argument("--seed", type=int, default=17)
    args = parser.parse_args()

    dataset = DragonBenchPromoterDataset(
        dataset_path=args.dataset,
        n_train=args.n_train,
        n_eval=args.n_eval,
        seed=args.seed,
    )
    out_dir = Path(args.out_dir)
    train_rows = []
    eval_rows = []
    cards_by_id = {}
    with Path(args.dataset).open() as handle:
        for line in handle:
            card = json.loads(line)
            cards_by_id[card["id"]] = card
    for row in dataset.load("train"):
        train_rows.append(card_to_sft_row(cards_by_id[row["question_id"]]))
    for row in dataset.load("eval"):
        eval_rows.append(card_to_sft_row(cards_by_id[row["question_id"]]))

    _write_jsonl(out_dir / "train.jsonl", train_rows)
    _write_jsonl(out_dir / "eval.jsonl", eval_rows)
    metadata = {
        "dataset": args.dataset,
        "n_train": len(train_rows),
        "n_eval": len(eval_rows),
        "format": "messages-jsonl",
        "target": "AnolePromoterExpression",
    }
    (out_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
