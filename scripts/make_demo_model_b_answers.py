import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dragonbench.io import dump_jsonl, load_jsonl


DATASET = Path("eval/dragonbench_eval_v0.scoreable.jsonl")
SMOKE = Path("eval/smoke_answers.jsonl")
OUT = Path("eval/demo_model_b_answers.jsonl")


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
        if isinstance(source_pdb, str) and source_pdb.strip():
            answer = {"pdb": perturb_pdb_coordinates(source_pdb)}
        else:
            coords = []
            for point in hidden["coordinates"]:
                idx = int(point["residue_index"])
                coords.append(perturb_point(idx, point))
            answer = {"pdb": coordinates_to_ca_pdb(coords)}
        rows.append({"id": card["id"], "answer": f"<answer>{json.dumps(answer)}</answer>"})

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
