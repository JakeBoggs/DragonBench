import json
import statistics
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen


MIN_PROTEIN_LENGTH = 80
MAX_PROTEIN_LENGTH = 100
MIN_MEAN_PLDDT = 80.0
MAX_ANSWER_CHARS = 60_000
RECORD_COUNT = 20
WORKERS = 8

OUT = Path("data/source/komodo_alphafold/komodo_alphafold_structures.jsonl")
PDB_DIR = OUT.parent / "pdb"
UNIPROT_QUERY = (
    f"(organism_id:61221) AND "
    f"(length:[{MIN_PROTEIN_LENGTH} TO {MAX_PROTEIN_LENGTH}])"
)


def fetch_bytes(url):
    request = Request(url, headers={"User-Agent": "DragonBench fixture builder"})
    with urlopen(request, timeout=60) as response:
        return response.read()


def fetch_json(url):
    return json.loads(fetch_bytes(url))


def protein_name(entry):
    description = entry.get("proteinDescription", {})
    recommended = description.get("recommendedName", {})
    full_name = recommended.get("fullName", {})
    if full_name.get("value"):
        return full_name["value"]
    submissions = description.get("submissionNames", [])
    if submissions:
        return submissions[0].get("fullName", {}).get("value", "Uncharacterized protein")
    return "Uncharacterized protein"


def parse_ca_coordinates(pdb_text):
    coordinates = []
    plddt_values = []
    for line in pdb_text.splitlines():
        if not line.startswith("ATOM") or line[12:16].strip() != "CA":
            continue
        coordinates.append(
            {
                "pdb_residue": line[22:26].strip() + line[26:27].strip(),
                "residue_index": len(coordinates),
                "x": float(line[30:38]),
                "y": float(line[38:46]),
                "z": float(line[46:54]),
            }
        )
        plddt_values.append(float(line[60:66]))
    return coordinates, plddt_values


def answer_chars(pdb_text):
    answer = json.dumps({"pdb": pdb_text}, separators=(",", ":"))
    return len(answer)


def build_candidate(entry):
    accession = entry["primaryAccession"]
    sequence = entry["sequence"]["value"]
    metadata = fetch_json(f"https://alphafold.ebi.ac.uk/api/prediction/{accession}")
    if isinstance(metadata, list):
        if not metadata:
            return None
        metadata = metadata[0]
    pdb_url = metadata["pdbUrl"]
    pdb_text = fetch_bytes(pdb_url).decode("utf-8")
    coordinates, plddt_values = parse_ca_coordinates(pdb_text)
    if len(coordinates) != len(sequence):
        return None
    mean_plddt = statistics.fmean(plddt_values)
    wrapped_answer_chars = answer_chars(pdb_text)
    if mean_plddt < MIN_MEAN_PLDDT or wrapped_answer_chars >= MAX_ANSWER_CHARS:
        return None
    pdb_name = Path(pdb_url).name
    return {
        "record": {
            "accession": accession,
            "answer_json_chars": wrapped_answer_chars,
            "coordinates": coordinates,
            "mean_plddt": round(mean_plddt, 3),
            "pdb_path": str(PDB_DIR / pdb_name).replace("\\", "/"),
            "protein_name": protein_name(entry),
            "protein_sequence": sequence,
            "sequence_length": len(sequence),
            "source_url": pdb_url,
            "uniprot_id": entry.get("uniProtkbId", accession),
            "uniprot_url": f"https://rest.uniprot.org/uniprotkb/{accession}.json",
        },
        "pdb_name": pdb_name,
        "pdb_text": pdb_text,
    }


def fetch_candidates():
    fields = "accession,id,protein_name,length,sequence"
    url = (
        "https://rest.uniprot.org/uniprotkb/search"
        f"?query={quote(UNIPROT_QUERY)}"
        f"&format=json&fields={fields}&size=500"
    )
    entries = fetch_json(url)["results"]
    entries.sort(key=lambda entry: (entry["sequence"]["length"], entry["primaryAccession"]))
    candidates = []
    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = {executor.submit(build_candidate, entry): entry for entry in entries}
        for future in as_completed(futures):
            try:
                candidate = future.result()
            except Exception as exc:
                accession = futures[future]["primaryAccession"]
                print(f"Skipping {accession}: {exc}")
                continue
            if candidate is not None:
                candidates.append(candidate)
    candidates.sort(
        key=lambda item: (
            item["record"]["answer_json_chars"],
            -item["record"]["mean_plddt"],
            item["record"]["accession"],
        )
    )
    if len(candidates) < RECORD_COUNT:
        raise RuntimeError(
            f"Found only {len(candidates)} size-bounded high-confidence proteins; "
            f"need {RECORD_COUNT}"
        )
    selected = candidates[:RECORD_COUNT]
    selected.sort(key=lambda item: item["record"]["accession"])
    return selected


def write_fixture(selected):
    OUT.parent.mkdir(parents=True, exist_ok=True)
    PDB_DIR.mkdir(parents=True, exist_ok=True)
    selected_names = {item["pdb_name"] for item in selected}
    with tempfile.TemporaryDirectory(dir=OUT.parent) as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        temp_pdb_dir = temp_dir / "pdb"
        temp_pdb_dir.mkdir()
        for item in selected:
            (temp_pdb_dir / item["pdb_name"]).write_text(item["pdb_text"], newline="\n")
        temp_fixture = temp_dir / OUT.name
        with temp_fixture.open("w", newline="\n") as handle:
            for item in selected:
                handle.write(json.dumps(item["record"], sort_keys=True) + "\n")
        for item in selected:
            (temp_pdb_dir / item["pdb_name"]).replace(PDB_DIR / item["pdb_name"])
        temp_fixture.replace(OUT)
    for path in PDB_DIR.glob("AF-*-model_*.pdb"):
        if path.name not in selected_names:
            path.unlink()


def main():
    selected = fetch_candidates()
    write_fixture(selected)
    summary = [
        {
            "accession": item["record"]["accession"],
            "length": item["record"]["sequence_length"],
            "mean_plddt": item["record"]["mean_plddt"],
            "answer_json_chars": item["record"]["answer_json_chars"],
        }
        for item in selected
    ]
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
