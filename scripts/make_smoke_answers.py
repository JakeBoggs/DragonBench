import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dragonbench.io import load_jsonl


DATASET = Path("data/eval/dragonbench_eval_v0.scoreable.jsonl")
OUT = Path("data/generated/smoke_answers.jsonl")


def protein_answer_from_hidden(card):
    hidden = card["hidden_answer"]["answer"]
    if isinstance(hidden.get("pdb"), str) and hidden["pdb"].strip():
        return {"pdb": hidden["pdb"]}
    if isinstance(hidden.get("mmcif"), str) and hidden["mmcif"].strip():
        return {"mmcif": hidden["mmcif"]}
    raw_path = hidden.get("raw_pdb_path")
    if isinstance(raw_path, str) and Path(raw_path).exists():
        return {"pdb": Path(raw_path).read_text(errors="ignore")}
    raise RuntimeError(f"{card['id']} has no canonical PDB/mmCIF oracle structure")


def main() -> None:
    rows = []
    for card in load_jsonl(DATASET):
        answer = {}
        hidden = card["hidden_answer"]["answer"]
        task = card["task"]
        if task == "AnoleGeneParse":
            answer = {
                "introns": hidden["introns"],
            }
        elif task == "AnolePromoterExpression":
            answer = {
                "tissue_ranking": hidden["tissue_ranking"],
            }
        elif task == "KomodoProteinFold":
            answer = protein_answer_from_hidden(card)
        elif task == "RNAFold":
            answer = {
                "dot_bracket": hidden["dot_bracket"],
            }
        elif task == "DragonTFBind":
            answer = {"binding_probabilities": hidden["binding_probabilities"]}
        else:
            raise ValueError(f"unsupported task: {task}")
        rows.append({"id": card["id"], "answer": answer})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
