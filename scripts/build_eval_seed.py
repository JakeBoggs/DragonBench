import copy
import json
from pathlib import Path

from build_scoreable_eval import (
    build_anole_gene_parse,
    build_anole_promoter_expression,
    build_komodo_protein_fold,
    build_rna_folding,
    build_tf_binding,
)


VERSION = "dragonbench_eval_v0"
OUT = Path("eval/dragonbench_eval_v0.seed.jsonl")


def review_notes():
    return {
        "review_status": "not_started",
        "acceptance_checks": [
            "source record verified",
            "model-facing input finalized",
            "hidden answer extracted",
            "scorer run on answer",
            "leakage and ambiguity checked",
        ],
        "notes": "Candidate card for human review before promotion to locked eval.",
    }


def seed_card(row):
    card = copy.deepcopy(row)
    card["version"] = VERSION
    card["status"] = "candidate_needs_human_review"
    card["hidden_answer"] = {"status": "needs_source_extraction", "answer": None}
    card["human_review"] = review_notes()
    return card


def main():
    records = []
    records.extend(build_anole_gene_parse(1))
    records.extend(build_anole_promoter_expression(21))
    records.extend(build_komodo_protein_fold(41))
    records.extend(build_tf_binding(61))
    records.extend(build_rna_folding(81))
    if len(records) != 100:
        raise RuntimeError(f"expected 100 records, got {len(records)}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as f:
        for record in records:
            f.write(json.dumps(seed_card(record), sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
