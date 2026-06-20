import json
import ssl
import sys
import urllib.request
from pathlib import Path


RAW_DIR = Path("data/protein_structures/raw_pdb")
OUT = Path("data/protein_structures/ca_structures.jsonl")


TARGETS = [
    ("1CRN", "A"),
    ("1UBQ", "A"),
    ("1L2Y", "A"),
    ("1VII", "A"),
    ("1BBA", "A"),
    ("1PRB", "A"),
    ("1ENH", "A"),
    ("2CI2", "I"),
    ("1PGB", "A"),
    ("1SHF", "A"),
    ("1FSD", "A"),
    ("2K39", "A"),
    ("1TEN", "A"),
    ("1CSP", "A"),
    ("1AIL", "A"),
    ("1BDD", "A"),
    ("1ROP", "A"),
    ("1GAB", "A"),
    ("2GB1", "A"),
    ("1ZDD", "A"),
    ("1MJC", "A"),
    ("1E0L", "A"),
    ("1NYF", "A"),
    ("1HZ6", "A"),
]


AA3_TO_1 = {
    "ALA": "A",
    "ARG": "R",
    "ASN": "N",
    "ASP": "D",
    "CYS": "C",
    "GLN": "Q",
    "GLU": "E",
    "GLY": "G",
    "HIS": "H",
    "ILE": "I",
    "LEU": "L",
    "LYS": "K",
    "MET": "M",
    "PHE": "F",
    "PRO": "P",
    "SER": "S",
    "THR": "T",
    "TRP": "W",
    "TYR": "Y",
    "VAL": "V",
    "SEC": "U",
    "PYL": "O",
}


def download_pdb(pdb_id: str) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / f"{pdb_id.lower()}.pdb"
    if path.exists() and path.stat().st_size > 0:
        return path
    url = f"https://files.rcsb.org/download/{pdb_id.upper()}.pdb"
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            path.write_bytes(response.read())
    except ssl.SSLCertVerificationError:
        context = ssl._create_unverified_context()
        with urllib.request.urlopen(url, timeout=30, context=context) as response:
            path.write_bytes(response.read())
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", None)
        if isinstance(reason, ssl.SSLCertVerificationError):
            context = ssl._create_unverified_context()
            with urllib.request.urlopen(url, timeout=30, context=context) as response:
                path.write_bytes(response.read())
        else:
            raise
    return path


def extract_ca(path: Path, pdb_id: str, chain_id: str) -> dict | None:
    residues = []
    seen = set()
    for line in path.read_text(errors="ignore").splitlines():
        if not line.startswith("ATOM"):
            continue
        atom = line[12:16].strip()
        altloc = line[16].strip()
        resname = line[17:20].strip()
        chain = line[21].strip()
        resseq = line[22:26].strip()
        icode = line[26].strip()
        if atom != "CA" or chain != chain_id or altloc not in {"", "A"}:
            continue
        key = (chain, resseq, icode)
        if key in seen:
            continue
        aa = AA3_TO_1.get(resname)
        if aa is None:
            continue
        seen.add(key)
        residues.append({
            "pdb_residue": resseq + (icode if icode else ""),
            "aa": aa,
            "x": round(float(line[30:38]), 3),
            "y": round(float(line[38:46]), 3),
            "z": round(float(line[46:54]), 3),
        })
    if len(residues) < 20:
        return None
    return {
        "pdb_id": pdb_id.upper(),
        "chain_id": chain_id,
        "source_url": f"https://files.rcsb.org/download/{pdb_id.upper()}.pdb",
        "protein_sequence": "".join(r["aa"] for r in residues),
        "sequence_length": len(residues),
        "coordinates": [
            {
                "residue_index": idx,
                "pdb_residue": residue["pdb_residue"],
                "x": residue["x"],
                "y": residue["y"],
                "z": residue["z"],
            }
            for idx, residue in enumerate(residues)
        ],
    }


def main() -> None:
    records = []
    errors = []
    for pdb_id, chain_id in TARGETS:
        try:
            path = download_pdb(pdb_id)
            record = extract_ca(path, pdb_id, chain_id)
            if record is None:
                errors.append(f"{pdb_id}:{chain_id} had too few extractable CA residues")
                continue
            records.append(record)
        except Exception as exc:
            errors.append(f"{pdb_id}:{chain_id} failed: {exc}")
    if len(records) < 20:
        print("\n".join(errors), file=sys.stderr)
        raise SystemExit(f"Need at least 20 structures, extracted {len(records)}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as f:
        for record in records[:20]:
            f.write(json.dumps(record, sort_keys=True) + "\n")
    print(f"Wrote {OUT} with {min(len(records), 20)} structures")
    if errors:
        print("Skipped:", *errors, sep="\n- ", file=sys.stderr)


if __name__ == "__main__":
    main()
