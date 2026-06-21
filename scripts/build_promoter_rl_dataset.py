#!/usr/bin/env python3
"""Write DragonBench promoter-expression RL JSONL splits locally."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dragonbench.rl.promoter_dataset import DragonBenchPromoterDataset


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="eval/dragonbench_eval_v0.scoreable.jsonl")
    parser.add_argument("--out-dir", default="runs/promoter_rl_dataset")
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
    out_dir.mkdir(parents=True, exist_ok=True)
    train_path = out_dir / "train.jsonl"
    eval_path = out_dir / "eval.jsonl"
    dataset.prepare(str(train_path), {"eval": str(eval_path)})
    metadata = {
        "dataset": args.dataset,
        "n_train": len(dataset.load("train")),
        "n_eval": len(dataset.load("eval")),
        "input_key": dataset.input_key,
        "label_key": dataset.label_key,
    }
    (out_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
