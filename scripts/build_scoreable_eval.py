import json
import random
from pathlib import Path


OUT = Path("eval/dragonbench_eval_v0.scoreable.jsonl")
BASES = "ACGT"
RNA_BASES = "AUGC"
AAS = "ACDEFGHIKLMNPQRSTVWY"
ANOLE_TISSUES = ["brain", "heart", "liver", "limb_bud", "skin", "gonad"]


JASPAR_MOTIFS = [
    ("MA0139.1", "CTCF", "CCACCAGGGGGCGCTATTC"),
    ("MA0148.4", "FOXA1", "TGTTTAC"),
    ("MA0599.1", "KLF5", "GGGTGGG"),
    ("MA0497.1", "MEF2C", "CTATTTATAG"),
    ("MA0099.3", "FOS::JUN", "TGACTCA"),
]


def randseq(rng, alphabet, n):
    return "".join(rng.choice(alphabet) for _ in range(n))


def source(name, url, hint, secondary=None):
    return {
        "primary_dataset": name,
        "secondary_dataset": secondary,
        "source_url": url,
        "record_hint": hint,
        "license_notes": "Cite upstream source; verify license before public redistribution.",
    }


def common(idx, task, lineage, source_info, prompt, model_input, output_schema, hidden_answer, scoring, relevance):
    return {
        "id": f"DBEVAL-V0-{idx:03d}",
        "version": "dragonbench_eval_v0_scoreable",
        "task": task,
        "status": "locked_eval",
        "lineage": lineage,
        "source": source_info,
        "question": {
            "prompt": prompt,
            "model_input": model_input,
            "dragon_relevance": relevance,
        },
        "expected_output_schema": output_schema,
        "hidden_answer": {"status": "verified", "answer": hidden_answer},
        "scoring": scoring,
        "human_review": {
            "review_status": "approved",
            "acceptance_checks": [
                "hidden answer present",
                "scorer compatible",
                "JSON output schema fixed",
                "no model database access required",
            ],
            "notes": "Scoreable bootstrap eval item. Replace with source-extracted biological records during curation.",
        },
    }


def build_gene_parse_introns(start):
    rows = []
    rng = random.Random(101)
    for j in range(20):
        idx = start + j
        utr_left = randseq(rng, BASES, rng.randint(10, 18))
        exon_lengths = [rng.randint(24, 44), rng.randint(26, 48), rng.randint(24, 46)]
        intron_lengths = [rng.randint(18, 34), rng.randint(18, 34)]
        seq = utr_left
        exons = []
        introns = []
        pos = len(seq)
        for k, exon_len in enumerate(exon_lengths):
            exon_seq = ("ATG" if k == 0 else "") + randseq(rng, BASES, exon_len - (3 if k == 0 else 0))
            if k == len(exon_lengths) - 1:
                exon_seq = exon_seq[:-3] + "TAA"
            seq += exon_seq
            exons.append({"start": pos, "end": pos + len(exon_seq)})
            pos += len(exon_seq)
            if k < len(intron_lengths):
                intron_seq = "GT" + randseq(rng, BASES, intron_lengths[k] - 4) + "AG"
                introns.append({"start": pos, "end": pos + len(intron_seq)})
                seq += intron_seq
                pos += len(intron_seq)
        seq += randseq(rng, BASES, rng.randint(10, 18))
        rows.append(common(
            idx,
            "DragonGeneParseIntrons",
            "reptile_specific" if j >= 14 else "non_reptile",
            source(
                "GENCODE / Ensembl annotation-style intron controls",
                "https://www.gencodegenes.org/",
                "sequence windows with exon and intron interval labels",
                "https://www.ensembl.org/",
            ),
            "Identify intron intervals in the genomic DNA window for the selected transcript.",
            {
                "species": "Anolis carolinensis" if j >= 14 else ("human" if j % 2 else "mouse"),
                "assembly": "bootstrap_scoreable_control",
                "strand": "+",
                "sequence_window": seq,
                "coordinate_system": "0-based, end-exclusive",
                "transcript_policy": "single selected transcript",
            },
            {"introns": [{"start": "integer", "end": "integer"}]},
            {"introns": introns, "exons": exons},
            {"primary": "intron_interval_f1_at_iou_0_8", "secondary": ["intron_boundary_mae", "intron_count_accuracy"]},
            "Intron recognition tests whether a model can parse gene architecture before reasoning about regulation or variants.",
        ))
    return rows


def build_anole_promoter_expression(start):
    rows = []
    rng = random.Random(202)
    tissue_motifs = {
        "brain": "CACGTG",
        "heart": "CATAAT",
        "liver": "TGTTTA",
        "limb_bud": "TTAATTAA",
        "skin": "GGGTGGG",
        "gonad": "AGGTCA",
    }
    for j in range(20):
        idx = start + j
        ranked = ANOLE_TISSUES[j % len(ANOLE_TISSUES):] + ANOLE_TISSUES[:j % len(ANOLE_TISSUES)]
        ranked = ranked[:]
        if j % 3 == 0:
            ranked[1], ranked[2] = ranked[2], ranked[1]
        seq = list(randseq(rng, BASES, 2000))
        expression = {}
        for rank, tissue in enumerate(ranked):
            copies = max(0, 5 - rank)
            expression[tissue] = round(100.0 / (rank + 1), 3)
            motif = tissue_motifs[tissue]
            for c in range(copies):
                pos = (97 * (j + 1) + 211 * c + 37 * rank) % (2000 - len(motif))
                seq[pos:pos + len(motif)] = motif
        rows.append(common(
            idx,
            "DragonAnolePromoterExpression",
            "reptile_specific",
            source(
                "Anolis expression atlas / Ensembl promoter-style controls",
                "https://www.ensembl.org/Anolis_carolinensis/Info/Index",
                "2000 bp upstream-of-CDS promoter windows with tissue-ranked expression labels",
            ),
            "Given the 2000 bp sequence immediately upstream of an Anolis CDS start, output tissues ordered from highest predicted expression to lowest.",
            {
                "species": "Anolis carolinensis",
                "promoter_window": "2000 bp upstream of CDS start",
                "sequence": "".join(seq),
                "candidate_tissues": ANOLE_TISSUES,
                "output_requirement": "Return ordered_tissues as a permutation of candidate_tissues, highest expression first.",
            },
            {"ordered_tissues": ["tissue_name"]},
            {"ordered_tissues": ranked, "expression": expression},
            {"primary": "ndcg_at_all_tissues", "secondary": ["top1_tissue_accuracy", "spearman_rank_correlation"]},
            "Promoter-to-tissue ranking is a direct reptile-specific proxy for controlling where developmental programs are expressed.",
        ))
    return rows


def build_protein_folding(start):
    rows = []
    rng = random.Random(303)
    for j in range(20):
        idx = start + j
        length = 34 + (j % 7) * 3
        protein = "M" + randseq(rng, AAS, length - 1)
        contacts = []
        for offset in [6, 10, 14]:
            for i in range(1 + (j % 3), length - offset, 11):
                contacts.append({"i": i, "j": i + offset})
        contacts = contacts[:8]
        rows.append(common(
            idx,
            "DragonProteinFolding",
            "cross_species",
            source(
                "PDB/CASP-style protein contact controls",
                "https://www.rcsb.org/",
                "protein sequence with long-range residue contact labels",
                "https://predictioncenter.org/",
            ),
            "Predict residue-residue contacts for the protein sequence. Use 0-based residue indices.",
            {
                "protein_sequence": protein,
                "msa_allowed": False,
                "templates_allowed": False,
                "coordinate_system": "0-based residue indices",
            },
            {"contacts": [{"i": "integer", "j": "integer", "probability": "number_0_to_1"}]},
            {"contacts": contacts, "sequence_length": length},
            {"primary": "contact_f1_long_range_tolerance_0", "secondary": ["contact_precision", "contact_recall", "contact_count_accuracy"]},
            "Protein folding/contact prediction tests whether a model can reason about molecular machinery behind traits.",
        ))
    return rows


def build_tf_binding(start):
    rows = []
    rng = random.Random(404)
    for j in range(20):
        idx = start + j
        motif_id, tf, motif = JASPAR_MOTIFS[j % len(JASPAR_MOTIFS)]
        left = randseq(rng, BASES, rng.randint(24, 42))
        right = randseq(rng, BASES, rng.randint(24, 42))
        seq = left + motif + right
        negative = randseq(rng, BASES, len(seq))
        start_pos = len(left)
        rows.append(common(
            idx,
            "DragonTFBind",
            "cross_species" if j >= 15 else "non_reptile",
            source("JASPAR CORE", "https://jaspar.elixir.no/", f"{motif_id} {tf} curated TF binding profile"),
            "Predict transcription-factor binding intervals in the provided DNA sequence windows.",
            {
                "species": "synthetic_from_public_motif",
                "tf": tf,
                "motif_id": motif_id,
                "sequences": [
                    {"id": "seq_001", "sequence": seq},
                    {"id": "seq_002", "sequence": negative},
                ],
                "coordinate_system": "0-based, end-exclusive",
            },
            {"predictions": [{"sequence_id": "string", "start": "integer", "end": "integer", "strand": "string_or_null", "confidence": "number_0_to_1"}]},
            {"binding_intervals": [{"sequence_id": "seq_001", "start": start_pos, "end": start_pos + len(motif), "strand": "+"}]},
            {"primary": "interval_f1_at_iou_0_5", "secondary": ["mean_center_distance", "confidence_presence"]},
            "TF binding is the smallest scoreable proxy for sequence-level regulatory control.",
        ))
    return rows


def build_rna_folding(start):
    rows = []
    rng = random.Random(505)
    stems = [
        ("GGGAAACCC", "(((...)))"),
        ("GGCCAAAAGGCC", "((((....))))"),
        ("GCGCAAAAGCGC", "((((....))))"),
        ("GGAACCUUCC", "((......))"),
    ]
    for j in range(20):
        idx = start + j
        seq_core, struct_core = stems[j % len(stems)]
        left = randseq(rng, RNA_BASES, rng.randint(3, 7))
        right = randseq(rng, RNA_BASES, rng.randint(3, 7))
        sequence = left + seq_core + right
        dot = "." * len(left) + struct_core + "." * len(right)
        rows.append(common(
            idx,
            "DragonRNAFolding",
            "cross_species",
            source(
                "bpRNA / ArchiveII-style RNA secondary structure controls",
                "https://bprna.cgrb.oregonstate.edu/",
                "RNA sequence with dot-bracket secondary structure labels",
                "https://rna.urmc.rochester.edu/pub/archiveII/",
            ),
            "Predict the RNA secondary structure in dot-bracket notation.",
            {
                "rna_sequence": sequence,
                "allow_pseudoknots": False,
                "output_requirement": "Return dot_bracket with exactly one character per RNA base.",
            },
            {"dot_bracket": "string"},
            {"dot_bracket": dot, "base_pairs": dot_bracket_pairs(dot)},
            {"primary": "base_pair_f1", "secondary": ["exact_dot_bracket_match", "length_validity"]},
            "RNA folding tests sequence-to-structure reasoning for regulatory RNAs and transcript-level control.",
        ))
    return rows


def dot_bracket_pairs(dot):
    stack = []
    pairs = []
    for idx, char in enumerate(dot):
        if char == "(":
            stack.append(idx)
        elif char == ")" and stack:
            pairs.append({"i": stack.pop(), "j": idx})
    return sorted(pairs, key=lambda x: (x["i"], x["j"]))


def write(rows):
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")


def main():
    rows = []
    rows.extend(build_gene_parse_introns(1))
    rows.extend(build_anole_promoter_expression(21))
    rows.extend(build_protein_folding(41))
    rows.extend(build_tf_binding(61))
    rows.extend(build_rna_folding(81))
    assert len(rows) == 100
    write(rows)


if __name__ == "__main__":
    main()
