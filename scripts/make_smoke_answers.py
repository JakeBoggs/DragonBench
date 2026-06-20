import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dragonbench.io import load_jsonl


DATASET = Path("eval/dragonbench_eval_v0.scoreable.jsonl")
OUT = Path("eval/smoke_answers.jsonl")


def coordinates_to_ca_pdb(coordinates):
    lines = []
    serial = 1
    for point in coordinates:
        residue = int(point["residue_index"]) + 1
        x = float(point["x"])
        y = float(point["y"])
        z = float(point["z"])
        atoms = [
            ("N", x - 0.500, y, z, "N"),
            ("CA", x, y, z, "C"),
            ("C", x + 0.500, y, z, "C"),
            ("O", x + 0.750, y, z, "O"),
        ]
        for atom, ax, ay, az, element in atoms:
            lines.append(
                f"ATOM  {serial:5d} {atom:>3s}  GLY A{residue:4d}    "
                f"{ax:8.3f}{ay:8.3f}{az:8.3f}"
                f"  1.00  0.00           {element}"
            )
            serial += 1
    lines.append("END")
    return "\n".join(lines)


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
            if isinstance(hidden.get("pdb"), str):
                answer = {"pdb": hidden["pdb"]}
            elif isinstance(hidden.get("mmcif"), str):
                answer = {"mmcif": hidden["mmcif"]}
            elif hidden.get("raw_pdb_path") and Path(hidden["raw_pdb_path"]).exists():
                answer = {"pdb": Path(hidden["raw_pdb_path"]).read_text(errors="ignore")}
            else:
                answer = {"pdb": coordinates_to_ca_pdb(hidden["coordinates"])}
        elif task == "RNAFold":
            answer = {
                "dot_bracket": hidden["dot_bracket"],
            }
        elif task == "DragonTFBind":
            answer = {"binding_probabilities": hidden["binding_probabilities"]}
        else:
            raise ValueError(f"unsupported task: {task}")
        rows.append({"id": card["id"], "answer": f"<answer>{json.dumps(answer)}</answer>"})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
