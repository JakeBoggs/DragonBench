#!/usr/bin/env python3
"""Build non-eval AnoleGeneParse training records from local RefSeq GFF/FASTA."""

from __future__ import annotations

import argparse
import gzip
import json
import random
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def parse_attrs(raw: str) -> dict[str, str]:
    attrs = {}
    for part in raw.split(";"):
        if not part or "=" not in part:
            continue
        key, value = part.split("=", 1)
        attrs[key] = value
    return attrs


def load_eval_sequences(path: Path) -> set[str]:
    sequences = set()
    if not path.exists():
        return sequences
    with path.open() as handle:
        for line in handle:
            row = json.loads(line)
            if row.get("task") != "AnoleGeneParse":
                continue
            sequence = row.get("question", {}).get("model_input", {}).get("sequence")
            if isinstance(sequence, str):
                sequences.add(sequence.upper())
    return sequences


def parse_gff_candidates(gff_path: Path, *, min_len: int, max_len: int, max_introns: int) -> list[dict[str, Any]]:
    transcripts: dict[str, dict[str, Any]] = {}
    exons_by_parent: dict[str, list[tuple[int, int]]] = defaultdict(list)

    with gzip.open(gff_path, "rt") as handle:
        for line in handle:
            if not line or line.startswith("#"):
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) != 9:
                continue
            seqid, source, feature, start_raw, end_raw, _score, strand, _phase, attr_raw = parts
            attrs = parse_attrs(attr_raw)
            start = int(start_raw)
            end = int(end_raw)
            if feature == "mRNA":
                transcript_id = attrs.get("ID")
                if not transcript_id:
                    continue
                transcripts[transcript_id] = {
                    "id": transcript_id,
                    "seqid": seqid,
                    "source": source,
                    "start": start,
                    "end": end,
                    "strand": strand,
                    "gene": attrs.get("gene"),
                    "product": attrs.get("product"),
                    "transcript_id": attrs.get("transcript_id") or attrs.get("Name"),
                    "source_url": "https://www.ncbi.nlm.nih.gov/datasets/genome/GCF_000090745.1/",
                }
            elif feature == "exon":
                parent = attrs.get("Parent")
                if not parent:
                    continue
                for parent_id in parent.split(","):
                    exons_by_parent[parent_id].append((start, end))

    candidates = []
    for transcript_id, transcript in transcripts.items():
        exons_1based = sorted(set(exons_by_parent.get(transcript_id, [])))
        if len(exons_1based) < 2:
            continue
        start = min(item[0] for item in exons_1based)
        end = max(item[1] for item in exons_1based)
        length = end - start + 1
        if length < min_len or length > max_len:
            continue

        exons = [{"start": exon_start - start, "end": exon_end - start + 1} for exon_start, exon_end in exons_1based]
        introns = []
        for left, right in zip(exons, exons[1:]):
            if left["end"] < right["start"]:
                introns.append({"start": left["end"], "end": right["start"]})
        if not 1 <= len(introns) <= max_introns:
            continue
        transcript = dict(transcript)
        transcript.update({"region_start": start, "region_end": end, "exons": exons, "introns": introns})
        candidates.append(transcript)
    return candidates


def read_selected_fasta(fasta_path: Path, seqids: set[str]) -> dict[str, str]:
    records: dict[str, list[str]] = {}
    current: str | None = None
    with gzip.open(fasta_path, "rt") as handle:
        for line in handle:
            if line.startswith(">"):
                seqid = line[1:].split()[0]
                current = seqid if seqid in seqids else None
                if current is not None:
                    records[current] = []
                continue
            if current is not None:
                records[current].append(line.strip())
    return {seqid: "".join(parts).upper() for seqid, parts in records.items()}


def splice_sequence(sequence: str, introns: list[dict[str, int]]) -> str:
    out = []
    cursor = 0
    for intron in sorted(introns, key=lambda item: item["start"]):
        out.append(sequence[cursor : intron["start"]])
        cursor = intron["end"]
    out.append(sequence[cursor:])
    return "".join(out)


def build_records(candidates: list[dict[str, Any]], fasta: dict[str, str], eval_sequences: set[str], limit: int) -> list[dict[str, Any]]:
    records = []
    seen_sequences = set(eval_sequences)
    for candidate in candidates:
        contig = fasta.get(candidate["seqid"])
        if not contig:
            continue
        sequence = contig[candidate["region_start"] - 1 : candidate["region_end"]].upper()
        if len(sequence) != candidate["region_end"] - candidate["region_start"] + 1:
            continue
        if "N" in sequence or sequence in seen_sequences:
            continue
        seen_sequences.add(sequence)
        records.append(
            {
                "id": candidate["id"],
                "gene": candidate.get("gene"),
                "product": candidate.get("product"),
                "seqid": candidate["seqid"],
                "strand": candidate["strand"],
                "region_start": candidate["region_start"],
                "region_end": candidate["region_end"],
                "sequence": sequence,
                "exons": candidate["exons"],
                "introns": candidate["introns"],
                "spliced_sequence": splice_sequence(sequence, candidate["introns"]),
                "source_url": candidate["source_url"],
            }
        )
        if len(records) >= limit:
            break
    return records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gff", default="data/source/anole_refseq/GCF_000090745.1_AnoCar2.0_genomic.gff.gz")
    parser.add_argument("--fasta", default="data/source/anole_refseq/GCF_000090745.1_AnoCar2.0_genomic.fna.gz")
    parser.add_argument("--eval", default="data/eval/dragonbench_eval_v0.scoreable.jsonl")
    parser.add_argument("--out", default="data/source/anole_refseq/gene_parse_training_records.jsonl")
    parser.add_argument("--limit", type=int, default=240)
    parser.add_argument("--candidate-limit", type=int, default=2000)
    parser.add_argument("--min-len", type=int, default=800)
    parser.add_argument("--max-len", type=int, default=3000)
    parser.add_argument("--max-introns", type=int, default=5)
    parser.add_argument("--seed", type=int, default=29)
    args = parser.parse_args()

    eval_sequences = load_eval_sequences(Path(args.eval))
    candidates = parse_gff_candidates(
        Path(args.gff),
        min_len=args.min_len,
        max_len=args.max_len,
        max_introns=args.max_introns,
    )
    rng = random.Random(args.seed)
    rng.shuffle(candidates)
    candidates = candidates[: args.candidate_limit]
    fasta = read_selected_fasta(Path(args.fasta), {candidate["seqid"] for candidate in candidates})
    records = build_records(candidates, fasta, eval_sequences, args.limit)
    if len(records) < args.limit:
        raise SystemExit(f"only built {len(records)} records; requested {args.limit}")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as handle:
        for record in records:
            handle.write(json.dumps(record, separators=(",", ":")) + "\n")
    print(
        json.dumps(
            {
                "out": str(out),
                "records": len(records),
                "candidate_pool": len(candidates),
                "eval_sequences_excluded": len(eval_sequences),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
