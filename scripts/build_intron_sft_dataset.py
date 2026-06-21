#!/usr/bin/env python3
"""Write DragonBench intron SFT JSONL splits locally."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dragonbench.rl.intron_dataset import (
    DragonBenchIntronDataset,
    card_to_sft_row,
    source_record_to_card,
)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, separators=(",", ":")) + "\n")


def _cards_by_id(dataset_path: str) -> dict[str, dict]:
    out = {}
    with Path(dataset_path).open() as handle:
        for line in handle:
            card = source_record_to_card(json.loads(line))
            out[card["id"]] = card
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="data/source/anole_refseq/gene_parse_training_records.jsonl")
    parser.add_argument("--out-dir", default="runs/intron_sft_dataset")
    parser.add_argument("--n-train", type=int, default=20)
    parser.add_argument("--n-eval", type=int, default=5)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument(
        "--messages-only",
        action="store_true",
        help="Drop local question_id metadata for strict Fireworks/OpenAI chat JSONL.",
    )
    args = parser.parse_args()

    dataset = DragonBenchIntronDataset(
        dataset_path=args.dataset,
        n_train=args.n_train,
        n_eval=args.n_eval,
        seed=args.seed,
    )
    cards = _cards_by_id(args.dataset)
    train_rows = [card_to_sft_row(cards[row["question_id"]]) for row in dataset.load("train")]
    eval_rows = [card_to_sft_row(cards[row["question_id"]]) for row in dataset.load("eval")]
    if args.messages_only:
        train_rows = [{"messages": row["messages"]} for row in train_rows]
        eval_rows = [{"messages": row["messages"]} for row in eval_rows]

    out_dir = Path(args.out_dir)
    _write_jsonl(out_dir / "train.jsonl", train_rows)
    _write_jsonl(out_dir / "eval.jsonl", eval_rows)
    metadata = {
        "dataset": args.dataset,
        "n_train": len(train_rows),
        "n_eval": len(eval_rows),
        "format": "messages-jsonl",
        "target": "AnoleGeneParse",
        "messages_only": args.messages_only,
    }
    (out_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
