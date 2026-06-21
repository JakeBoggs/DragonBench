"""Training Gym dataset for DragonBench AnoleGeneParse RL."""

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
    "You are a computational genomics model. Given a green anole genomic DNA "
    "sequence, identify every intron span. Use zero-based half-open coordinates "
    "relative to the supplied sequence. End with exactly one lowercase "
    "<answer>...</answer> block. The block contents must be valid JSON with "
    "one key named introns, whose value is an array of objects with integer "
    "start and end fields."
)


def _normalize_introns(introns: list[dict[str, Any]]) -> list[dict[str, int]]:
    return [
        {"start": int(intron["start"]), "end": int(intron["end"])}
        for intron in sorted(introns, key=lambda item: (item["start"], item["end"]))
    ]


def source_record_to_card(record: dict[str, Any]) -> dict[str, Any]:
    """Convert a local source record into the scoreable card shape."""
    sequence = record["sequence"]
    answer = {
        "introns": _normalize_introns(record["introns"]),
        "spliced_sequence": record.get("spliced_sequence"),
    }
    return {
        "id": record["id"],
        "task": "AnoleGeneParse",
        "question": {
            "model_input": {"sequence": sequence},
            "prompt": "Given the genomic DNA sequence of one green anole gene region, identify all intron spans.",
        },
        "hidden_answer": {"status": "verified", "answer": answer},
        "source": {
            "gene": record.get("gene"),
            "seqid": record.get("seqid"),
            "strand": record.get("strand"),
            "source_url": record.get("source_url"),
        },
    }


def _render_user_prompt(card: dict[str, Any]) -> str:
    sequence = card["question"]["model_input"]["sequence"]
    return (
        f"{card['question']['prompt']}\n\n"
        "Coordinate rules:\n"
        "- Use zero-based, half-open intervals: start is included and end is excluded.\n"
        "- Coordinates refer directly to the supplied sequence.\n"
        f"- Every interval must satisfy 0 <= start < end <= {len(sequence)}.\n"
        "- Return introns in ascending genomic order.\n"
        "- Do not return exons, a spliced sequence, commentary, or confidence values.\n\n"
        f"Genomic sequence ({len(sequence)} bases):\n{sequence}\n\n"
        "This training sequence contains at least one intron. Do not return an empty introns list.\n"
        "Use biological splice-site priors when uncertain: eukaryotic introns often start near donor motifs such as GT and end near acceptor motifs such as AG.\n"
        "Predict the best non-empty intron spans even if uncertain.\n\n"
        'Final answer format: <answer>{"introns":[...]}</answer>\n'
        "Inside introns, each item must be a JSON object with integer start and end fields.\n"
        "Return exactly one final lowercase <answer>...</answer> block."
    )


def card_to_training_row(card: dict[str, Any]) -> dict[str, Any]:
    label = {
        "answer": card["hidden_answer"]["answer"],
        "sequence": card["question"]["model_input"]["sequence"],
    }
    return {
        "question_id": card["id"],
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _render_user_prompt(card)},
        ],
        "label": json.dumps(label, separators=(",", ":")),
    }


def card_to_sft_row(card: dict[str, Any]) -> dict[str, Any]:
    """Return an MS-SWIFT/TRL-style supervised chat row."""
    introns = card["hidden_answer"]["answer"]["introns"]
    final = {"introns": introns}
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


class DragonBenchIntronDataset(DatasetConfig):
    """Materialize AnoleGeneParse rows for Slime GRPO."""

    input_key = "messages"
    label_key = "label"
    apply_chat_template = True
    output_format = "jsonl"
    always_prepare = True

    def __init__(
        self,
        dataset_path: str = "data/source/anole_refseq/gene_parse_training_records.jsonl",
        *,
        n_train: int = 20,
        n_eval: int = 5,
        seed: int = 17,
        dataset_id: str | None = None,
    ) -> None:
        self.dataset_path = dataset_path
        self.n_train = n_train
        self.n_eval = n_eval
        self.seed = seed
        self.dataset_id = dataset_id or f"dragonbench-intron-{uuid.uuid4()}"
        self._train_rows, self._eval_rows = self._load_rows()
        super().__init__()

    @property
    def name(self) -> str:
        return "dragonbench-anole-gene-parse"

    def _load_cards(self) -> list[dict[str, Any]]:
        cards = []
        with Path(self.dataset_path).open() as handle:
            for line in handle:
                record = json.loads(line)
                if record.get("sequence") and record.get("introns"):
                    cards.append(source_record_to_card(record))
        if not cards:
            raise ValueError(f"no intron records found in {self.dataset_path}")
        return cards

    def _load_rows(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        cards = self._load_cards()
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
