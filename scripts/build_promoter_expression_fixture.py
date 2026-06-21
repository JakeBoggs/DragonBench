import csv
import gzip
import io
import json
import math
import statistics
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path


OUT = Path("data/source/anole_expression/promoter_expression_records.jsonl")
BGEE_RELEASE = "15.2"
EXPERIMENT_ID = "SRP009831"
STUDY_URL = "https://doi.org/10.1186/1471-2164-14-49"
BGEE_EXPERIMENT_URL = f"https://www.bgee.org/experiment/{EXPERIMENT_ID}"
BGEE_DATA_URL = (
    "https://www.bgee.org/ftp/bgee_v15_2/download/processed_expr_values/rna_seq/"
    "Anolis_carolinensis/"
    f"Anolis_carolinensis_RNA-Seq_read_counts_TPM_{EXPERIMENT_ID}.tsv.gz"
)
ENSEMBL_REST = "https://rest.ensembl.org"
USER_AGENT = "DragonBench/1.0 (benchmark fixture builder)"

LIBRARY_TO_TISSUE = {
    "SRX145078": "adrenal_gland",
    "SRX146889": "adrenal_gland",
    "SRX111454": "brain",
    "SRX111451": "dewlap_skin",
    "SRX115247": "embryo",
    "SRX146888": "embryo",
    "SRX111452": "heart",
    "SRX112551": "liver",
    "SRX112552": "lung",
    "SRX111453": "ovary",
    "SRX112550": "skeletal_muscle",
}
TISSUES = [
    "adrenal_gland",
    "brain",
    "dewlap_skin",
    "embryo",
    "heart",
    "liver",
    "lung",
    "ovary",
    "skeletal_muscle",
]
TARGET_COUNTS = {
    "adrenal_gland": 2,
    "brain": 2,
    "dewlap_skin": 3,
    "embryo": 2,
    "heart": 2,
    "liver": 2,
    "lung": 3,
    "ovary": 2,
    "skeletal_muscle": 2,
}


def request_bytes(
    url: str,
    *,
    body: bytes | None = None,
    accept_json: bool = False,
    attempts: int = 4,
) -> bytes:
    headers = {
        "Accept": "application/json" if accept_json else "*/*",
        "Content-Type": "application/json" if accept_json else "application/octet-stream",
        "User-Agent": USER_AGENT,
    }
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, data=body, headers=headers)
            with urllib.request.urlopen(request, timeout=90) as response:
                return response.read()
        except (TimeoutError, urllib.error.URLError) as exc:
            if attempt + 1 == attempts:
                raise RuntimeError(f"request failed after {attempts} attempts: {url}") from exc
            time.sleep(2 ** attempt)
    raise AssertionError("unreachable")


def request_json(url: str, *, body: dict | None = None) -> dict:
    payload = json.dumps(body).encode() if body is not None else None
    return json.loads(request_bytes(url, body=payload, accept_json=True))


def load_expression() -> dict[str, dict[str, float]]:
    compressed = request_bytes(BGEE_DATA_URL)
    per_gene: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    with gzip.open(io.BytesIO(compressed), mode="rt", encoding="utf-8") as source:
        for row in csv.DictReader(source, delimiter="\t"):
            tissue = LIBRARY_TO_TISSUE.get(row["Library ID"])
            if tissue is None:
                continue
            per_gene[row["Gene ID"]][tissue].append(float(row["TPM"]))

    expression = {}
    for gene_id, values in per_gene.items():
        if set(values) != set(TISSUES):
            continue
        expression[gene_id] = {
            tissue: statistics.mean(values[tissue])
            for tissue in TISSUES
        }
    return expression


def candidate_pools(expression: dict[str, dict[str, float]]) -> dict[str, list[dict]]:
    pools: dict[str, list[dict]] = {tissue: [] for tissue in TISSUES}
    tiers = [
        (9, 20.0, 2.0),
        (8, 15.0, 1.75),
        (7, 10.0, 1.5),
    ]
    for gene_id, values in expression.items():
        ranking = sorted(TISSUES, key=lambda tissue: (-values[tissue], tissue))
        top_tissue = ranking[0]
        top_value = values[ranking[0]]
        second_value = values[ranking[1]]
        measurable = sum(value >= 0.5 for value in values.values())
        if second_value <= 0:
            continue
        ratio = top_value / second_value
        tier = next(
            (
                tier_index
                for tier_index, (min_measurable, min_top, min_ratio) in enumerate(tiers)
                if measurable >= min_measurable and top_value >= min_top and ratio >= min_ratio
            ),
            None,
        )
        if tier is None:
            continue
        pools[top_tissue].append({
            "gene_id": gene_id,
            "expression": values,
            "tissue_ranking": ranking,
            "measurable_tissues": measurable,
            "top_tissue": top_tissue,
            "top_tpm": top_value,
            "top_to_second_ratio": ratio,
            "tier": tier,
        })

    target_log_ratio = math.log2(3.0)
    for tissue, rows in pools.items():
        rows.sort(key=lambda row: (
            row["tier"],
            -row["measurable_tissues"],
            abs(math.log2(row["top_to_second_ratio"]) - target_log_ratio),
            -row["top_tpm"],
            row["gene_id"],
        ))
        if len(rows) < TARGET_COUNTS[tissue]:
            raise RuntimeError(
                f"not enough eligible {tissue} genes: need {TARGET_COUNTS[tissue]}, found {len(rows)}"
            )
    return pools


def lookup_genes(gene_ids: list[str]) -> dict[str, dict]:
    results = {}
    for start in range(0, len(gene_ids), 100):
        chunk = gene_ids[start:start + 100]
        results.update(request_json(
            f"{ENSEMBL_REST}/lookup/id",
            body={"ids": chunk},
        ))
    return results


def canonical_cds_start(gene_id: str) -> tuple[dict, dict, int] | None:
    gene = request_json(f"{ENSEMBL_REST}/lookup/id/{gene_id}?expand=1")
    canonical_id = str(gene["canonical_transcript"]).split(".", 1)[0]
    transcripts = gene["Transcript"]
    canonical = next(
        (
            transcript
            for transcript in transcripts
            if transcript.get("id") == canonical_id or transcript.get("is_canonical") == 1
        ),
        None,
    )
    if canonical is None or not isinstance(canonical.get("Translation"), dict):
        return None
    translation = canonical["Translation"]
    cds_start = int(translation["start"] if int(gene["strand"]) == 1 else translation["end"])
    return gene, canonical, cds_start


def promoter_sequence(gene: dict, cds_start: int) -> tuple[str, int, int] | None:
    strand = int(gene["strand"])
    if strand == 1:
        start = cds_start - 2000
        end = cds_start - 1
    else:
        start = cds_start + 1
        end = cds_start + 2000
    if start < 1:
        return None
    region = f"{gene['seq_region_name']}:{start}..{end}:{strand}"
    encoded_region = urllib.parse.quote(region, safe=":.-")
    payload = request_json(
        f"{ENSEMBL_REST}/sequence/region/anolis_carolinensis/{encoded_region}"
    )
    sequence = str(payload["seq"]).upper()
    if len(sequence) != 2000 or set(sequence) - set("ACGT"):
        return None
    return sequence, start, end


def build_records() -> list[dict]:
    expression = load_expression()
    pools = candidate_pools(expression)
    pool_ids = list(dict.fromkeys(
        row["gene_id"]
        for tissue in TISSUES
        for row in pools[tissue][:40]
    ))
    lookups = lookup_genes(pool_ids)

    records = []
    used_rankings: set[tuple[str, ...]] = set()
    for tissue in TISSUES:
        selected = 0
        for candidate in pools[tissue]:
            ranking_key = tuple(candidate["tissue_ranking"])
            if ranking_key in used_rankings:
                continue
            summary = lookups.get(candidate["gene_id"])
            if not isinstance(summary, dict):
                continue
            if summary.get("biotype") != "protein_coding":
                continue
            expanded = canonical_cds_start(candidate["gene_id"])
            if expanded is None:
                continue
            gene, transcript, cds_start = expanded
            promoter = promoter_sequence(gene, cds_start)
            if promoter is None:
                continue
            sequence, promoter_start, promoter_end = promoter
            values = {
                name: round(candidate["expression"][name], 6)
                for name in TISSUES
            }
            records.append({
                "candidate_tissues": TISSUES,
                "canonical_transcript_id": transcript["id"],
                "cds_start": cds_start,
                "ensembl_gene_url": (
                    "https://www.ensembl.org/Anolis_carolinensis/Gene/Summary?"
                    f"g={candidate['gene_id']}"
                ),
                "expression": values,
                "expression_experiment_id": EXPERIMENT_ID,
                "expression_source_url": BGEE_DATA_URL,
                "expression_unit": "TPM",
                "gene_id": candidate["gene_id"],
                "gene_name": gene["display_name"],
                "promoter_end": promoter_end,
                "promoter_sequence": sequence,
                "promoter_start": promoter_start,
                "seq_region": gene["seq_region_name"],
                "source_url": STUDY_URL,
                "strand": "+" if int(gene["strand"]) == 1 else "-",
                "tissue_ranking": candidate["tissue_ranking"],
                "top_tissue": candidate["top_tissue"],
                "top_to_second_ratio": round(candidate["top_to_second_ratio"], 6),
                "bgee_release": BGEE_RELEASE,
                "bgee_experiment_url": BGEE_EXPERIMENT_URL,
            })
            used_rankings.add(ranking_key)
            selected += 1
            if selected == TARGET_COUNTS[tissue]:
                break
        if selected != TARGET_COUNTS[tissue]:
            raise RuntimeError(
                f"could not build {TARGET_COUNTS[tissue]} records for {tissue}; built {selected}"
            )

    records.sort(key=lambda row: (TISSUES.index(row["top_tissue"]), row["gene_id"]))
    if len(records) != 20:
        raise RuntimeError(f"expected 20 records, built {len(records)}")
    return records


def main() -> None:
    records = build_records()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as target:
        for record in records:
            target.write(json.dumps(record, sort_keys=True) + "\n")
    counts = {
        tissue: sum(record["top_tissue"] == tissue for record in records)
        for tissue in TISSUES
    }
    print(json.dumps({
        "output": str(OUT),
        "records": len(records),
        "candidate_tissues": len(TISSUES),
        "top_tissue_counts": counts,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
