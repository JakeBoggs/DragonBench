import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dragonbench.io import dump_jsonl, load_jsonl


DATASET = Path("eval/dragonbench_eval_v0.scoreable.jsonl")
SMOKE = Path("eval/smoke_answers.jsonl")
OUT = Path("eval/demo_model_b_answers.jsonl")


def main() -> None:
    smoke_by_id = {row["id"]: row for row in load_jsonl(SMOKE)}
    rows = []
    for card in load_jsonl(DATASET):
        if card["task"] != "KomodoProteinFold":
            rows.append(smoke_by_id[card["id"]])
            continue

        hidden = card["hidden_answer"]["answer"]
        source_pdb = hidden.get("pdb")
        if not source_pdb and hidden.get("raw_pdb_path") and Path(hidden["raw_pdb_path"]).exists():
            source_pdb = Path(hidden["raw_pdb_path"]).read_text(errors="ignore")
        if not isinstance(source_pdb, str) or not source_pdb.strip():
            raise RuntimeError(f"{card['id']} has no canonical PDB oracle structure")
        answer = {"pdb": perturb_pdb_coordinates(source_pdb)}
        rows.append({"id": card["id"], "answer": answer})

    dump_jsonl(OUT, rows)
    print(OUT)


def perturb_pdb_coordinates(text):
    lines = []
    residue_to_index = {}
    for line in text.splitlines():
        if line.startswith(("ATOM", "HETATM")) and len(line) >= 54:
            chain = line[21].strip()
            residue = line[22:26].strip()
            icode = line[26].strip()
            key = (chain, residue, icode)
            idx = residue_to_index.setdefault(key, len(residue_to_index))
            try:
                point = {
                    "residue_index": idx,
                    "x": float(line[30:38]),
                    "y": float(line[38:46]),
                    "z": float(line[46:54]),
                }
            except ValueError:
                lines.append(line)
                continue
            shifted = perturb_point(idx, point)
            lines.append(
                f"{line[:30]}{shifted['x']:8.3f}{shifted['y']:8.3f}{shifted['z']:8.3f}{line[54:]}"
            )
        else:
            lines.append(line)
    return "\n".join(lines)


def perturb_point(idx, point):
    return {
        "residue_index": idx,
        "x": round(float(point["x"]) + 1.8 * math.sin(idx * 0.57), 3),
        "y": round(float(point["y"]) + 1.2 * math.cos(idx * 0.41), 3),
        "z": round(float(point["z"]) + 1.5 * math.sin(idx * 0.29 + 0.8), 3),
    }


if __name__ == "__main__":
    main()
