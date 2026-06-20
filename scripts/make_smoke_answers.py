import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dragonbench.io import load_jsonl


DATASET = Path("eval/dragonbench_eval_v0.scoreable.jsonl")
OUT = Path("eval/smoke_answers.jsonl")


def main() -> None:
    rows = []
    for card in load_jsonl(DATASET):
        answer = {}
        hidden = card["hidden_answer"]["answer"]
        task = card["task"]
        if task == "DragonGeneParse":
            answer = {
                "exons": hidden["exons"],
                "splice_donors": hidden["splice_donors"],
                "splice_acceptors": hidden["splice_acceptors"],
                "cds_intervals": hidden["cds_intervals"],
            }
        elif task == "DragonTFBind":
            answer = {
                "predictions": [
                    {**item, "confidence": 0.95}
                    for item in hidden["binding_intervals"]
                ]
            }
        elif task == "DragonEnhancerTissue":
            answer = {
                "active": hidden["active"],
                "tissues": hidden["tissues"],
            }
        elif task == "DragonVariantEffect":
            answer = {
                "variant_scores": [
                    {"variant": item["variant"], "predicted_score": item["score"]}
                    for item in hidden["variant_scores"]
                ]
            }
        elif task == "DragonPhenotypeGene":
            answer = {
                "phenotypes": hidden["phenotypes"],
            }
        rows.append({"id": card["id"], "answer": json.dumps(answer)})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
