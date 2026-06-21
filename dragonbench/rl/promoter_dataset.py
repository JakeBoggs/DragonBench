"""Training Gym dataset for DragonBench promoter-expression RL."""

from __future__ import annotations

import json
import random
import uuid
from pathlib import Path
from typing import Any, Literal

try:
    from modal_training_gym.common.dataset import DatasetConfig
except ImportError:  # pragma: no cover - local dataset export path.
    class DatasetConfig:  # type: ignore[no-redef]
        """Small local fallback so dataset export does not require Training Gym."""

        input_key = ""
        label_key = ""
        apply_chat_template = True

        def __init__(self, **kwargs: Any) -> None:
            for key, value in kwargs.items():
                setattr(self, key, value)


SYSTEM_PROMPT = (
    "You are a computational genomics model. Given a 2000 bp Anolis promoter "
    "sequence and candidate tissues, rank every candidate tissue from highest "
    "to lowest predicted expression. End with exactly one lowercase "
    '<answer>{"tissue_ranking":[...]}</answer> block containing valid JSON.'
)


def _render_user_prompt(card: dict[str, Any]) -> str:
    question = card["question"]
    model_input = question["model_input"]
    tissues = model_input["candidate_tissues"]
    sequence = model_input["promoter_sequence"]
    return (
        f"{question['prompt']}\n\n"
        f"Candidate tissues: {json.dumps(tissues, separators=(',', ':'))}\n\n"
        f"Promoter sequence:\n{sequence}\n\n"
        "Return every candidate tissue exactly once in descending expression order.\n"
        'Final answer format: <answer>{"tissue_ranking":["tissue_a","tissue_b"]}</answer>'
    )


def card_to_training_row(card: dict[str, Any]) -> dict[str, Any]:
    return {
        "question_id": card["id"],
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _render_user_prompt(card)},
        ],
        "label": json.dumps(card["hidden_answer"]["answer"], separators=(",", ":")),
    }


def card_to_sft_row(card: dict[str, Any]) -> dict[str, Any]:
    """Return an MS-SWIFT/TRL-style supervised chat row."""
    answer = card["hidden_answer"]["answer"]
    ranking = answer["tissue_ranking"]
    final = {"tissue_ranking": ranking}
    row = card_to_training_row(card)
    return {
        "question_id": row["question_id"],
        "messages": [
            *row["messages"],
            {
                "role": "assistant",
                "content": f"<answer>{json.dumps(final, separators=(',', ':'))}</answer>",
            },
        ],
    }


class DragonBenchPromoterDataset(DatasetConfig):
    """Materialize promoter-expression rows for Slime GRPO.

    The dataset stores rows in memory when constructed so Modal can serialize the
    config without depending on a local repo checkout inside remote workers.
    """

    input_key = "messages"
    label_key = "label"
    apply_chat_template = True
    output_format = "jsonl"
    always_prepare = True

    def __init__(
        self,
        dataset_path: str = "data/eval/dragonbench_eval_v0.scoreable.jsonl",
        *,
        n_train: int = 20,
        n_eval: int = 20,
        seed: int = 17,
        dataset_id: str | None = None,
    ) -> None:
        self.dataset_path = dataset_path
        self.n_train = n_train
        self.n_eval = n_eval
        self.seed = seed
        self.dataset_id = dataset_id or f"dragonbench-promoter-{uuid.uuid4()}"
        self._train_rows, self._eval_rows = self._load_rows()
        super().__init__()

    @property
    def name(self) -> str:
        return "dragonbench-promoter-expression"

    def _load_rows(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        cards = []
        with Path(self.dataset_path).open() as handle:
            for line in handle:
                card = json.loads(line)
                if card.get("task") == "AnolePromoterExpression":
                    cards.append(card)
        if not cards:
            raise ValueError(f"no AnolePromoterExpression cards found in {self.dataset_path}")

        rng = random.Random(self.seed)
        shuffled = list(cards)
        rng.shuffle(shuffled)
        train_cards = shuffled[: min(self.n_train, len(shuffled))]
        eval_cards = shuffled[-min(self.n_eval, len(shuffled)) :]
        return (
            [card_to_training_row(card) for card in train_cards],
            [card_to_training_row(card) for card in eval_cards],
        )

    def load(self, split: Literal["all", "train", "eval"] = "all") -> list[dict[str, Any]]:
        if split == "train":
            return list(self._train_rows)
        if split == "eval":
            return list(self._eval_rows)
        return list(self._train_rows)

    @staticmethod
    def _write_jsonl(path: str, rows: list[dict[str, Any]]) -> None:
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w") as handle:
            for row in rows:
                handle.write(json.dumps(row, separators=(",", ":")) + "\n")

    def prepare(self, path: str, eval_paths: dict[str, str] | None = None) -> None:
        self._write_jsonl(path, self._train_rows)
        if eval_paths:
            for eval_path in eval_paths.values():
                self._write_jsonl(eval_path, self._eval_rows)
