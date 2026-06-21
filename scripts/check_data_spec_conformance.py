import argparse
import json
from collections import Counter
from pathlib import Path


EXPECTED_COUNTS = {
    "AnoleGeneParse": 20,
    "AnolePromoterExpression": 20,
    "KomodoProteinFold": 20,
    "DragonTFBind": 20,
    "RNAFold": 20,
}

BOOTSTRAP_MARKERS = ("bootstrap", "synthetic", "control")


def load_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def main():
    parser = argparse.ArgumentParser(description="Check DragonBench eval records against data-spec.md structural/source requirements.")
    parser.add_argument("--dataset", default="eval/dragonbench_eval_v0.scoreable.jsonl")
    args = parser.parse_args()

    rows = load_jsonl(args.dataset)
    failures = []
    counts = Counter(row["task"] for row in rows)
    if counts != EXPECTED_COUNTS:
        failures.append(f"task counts differ: {dict(counts)}")

    for row in rows:
        task = row["task"]
        mid = row["question"]["model_input"]
        out = row["expected_output_schema"]
        hidden = row["hidden_answer"]["answer"]
        source_text = " ".join(str(v).lower() for v in row["source"].values() if v is not None)
        if any(marker in source_text for marker in BOOTSTRAP_MARKERS):
            failures.append(f"{row['id']} {task}: source still marked bootstrap/synthetic/control")

        if task == "AnoleGeneParse":
            check("sequence" in mid and set(mid["sequence"]) <= set("ACGT"), row, failures, "sequence must be unambiguous DNA")
            check(1000 <= len(mid["sequence"]) <= 5000, row, failures, "gene span must be 1000-5000 bp")
            check(1 <= len(hidden["introns"]) <= 5, row, failures, "must have 1-5 introns")
            check("introns" in out, row, failures, "output schema must request introns")
        elif task == "AnolePromoterExpression":
            check(len(mid["promoter_sequence"]) == 2000, row, failures, "promoter must be 2000 bp")
            check(
                len(mid["candidate_tissues"]) == 9,
                row,
                failures,
                "must provide exactly nine candidate tissues",
            )
            check("tissue_ranking" in out, row, failures, "output schema must request tissue_ranking")
            check(
                sorted(hidden["tissue_ranking"]) == sorted(mid["candidate_tissues"])
                and len(hidden["tissue_ranking"]) == len(mid["candidate_tissues"]),
                row,
                failures,
                "hidden tissue_ranking must be a permutation of candidate_tissues",
            )
            check(
                sorted(hidden["expression"]) == sorted(mid["candidate_tissues"]),
                row,
                failures,
                "hidden expression must cover every candidate tissue",
            )
        elif task == "KomodoProteinFold":
            check(80 <= len(mid["protein_sequence"]) <= 100, row, failures, "protein length must be 80-100 aa")
            check(hidden["sequence_length"] == len(mid["protein_sequence"]), row, failures, "hidden sequence length mismatch")
            check(0 < hidden["answer_json_chars"] < 60_000, row, failures, "reference PDB task-answer JSON must be under 60000 characters")
            check("pdb" in out or "mmcif" in out, row, failures, "output schema must request PDB/mmCIF")
            check("uniprot_accession" in hidden and "raw_pdb_path" in hidden, row, failures, "hidden source structure metadata missing")
        elif task == "DragonTFBind":
            check("tf_sequence" in mid, row, failures, "tf_sequence missing")
            check(len(mid["dna_candidates"]) == 10, row, failures, "must provide exactly 10 DNA candidates")
            candidate_ids = [candidate["id"] for candidate in mid["dna_candidates"]]
            check(candidate_ids == [f"seq_{index:02d}" for index in range(1, 11)], row, failures, "candidate IDs must be seq_01 through seq_10")
            check(len({candidate["sequence"] for candidate in mid["dna_candidates"]}) == 10, row, failures, "DNA candidate sequences must be unique")
            check(sorted(hidden["binding_probabilities"]) == sorted(candidate_ids), row, failures, "hidden binding probabilities must cover exactly the candidate IDs")
            check("binding_probabilities" in out, row, failures, "output schema must request binding_probabilities")
        elif task == "RNAFold":
            check(50 <= len(mid["sequence"]) <= 250, row, failures, "RNA length must be 50-250 nt")
            check(set(mid["sequence"]) <= set("ACGU"), row, failures, "RNA sequence must contain only A/C/G/U")
            check("dot_bracket" in out, row, failures, "output schema must request dot_bracket")

    if failures:
        print(json.dumps({"conforms": False, "failures": failures[:200], "n_failures": len(failures)}, indent=2))
        raise SystemExit(1)
    print(json.dumps({"conforms": True, "n": len(rows), "counts": dict(counts)}, indent=2, sort_keys=True))


def check(condition, row, failures, message):
    if not condition:
        failures.append(f"{row['id']} {row['task']}: {message}")


if __name__ == "__main__":
    main()
