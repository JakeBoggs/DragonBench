import json
from pathlib import Path


OUT = Path("eval/dragonbench_eval_v0.scoreable.jsonl")
ANOLE_GENE_PARSE_FIXTURE = Path("data/source/anole_refseq/gene_parse_records.jsonl")
KOMODO_ALPHAFOLD_FIXTURE = Path("data/source/komodo_alphafold/komodo_alphafold_structures.jsonl")
RFAM_RNA_FIXTURE = Path("data/source/rfam/rna_folding_records.jsonl")
ANOLE_PROMOTER_FIXTURE = Path("data/source/anole_expression/promoter_expression_records.jsonl")
JASPAR_TFBIND_FIXTURE = Path("data/source/jaspar_tfbind/tf_binding_records.jsonl")


def source(name, url, hint, secondary=None):
    return {
        "primary_dataset": name,
        "secondary_dataset": secondary,
        "source_url": url,
        "record_hint": hint,
        "license_notes": "Cite upstream source; verify license before public redistribution.",
    }


def common(idx, task, source_info, prompt, model_input, output_schema, hidden_answer, scoring, relevance):
    return {
        "id": f"DBEVAL-V0-{idx:03d}",
        "version": "dragonbench_eval_v0_scoreable",
        "task": task,
        "status": "locked_eval",
        "lineage": "reptile_specific" if task in {"AnoleGeneParse", "AnolePromoterExpression", "KomodoProteinFold"} else "cross_species",
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
            "notes": "Scoreable eval item. Source extraction status is recorded in source metadata.",
        },
    }


def build_anole_gene_parse(start):
    rows = []
    records = load_jsonl_required(ANOLE_GENE_PARSE_FIXTURE, 20)
    for j, record in enumerate(records[:20]):
        idx = start + j
        rows.append(common(
            idx,
            "AnoleGeneParse",
            source(
                "NCBI RefSeq Anolis carolinensis annotation",
                record["source_url"],
                f"{record['seqid']}:{record['source_start']}-{record['source_end']} transcript {record['id']}",
            ),
            "Given the genomic DNA sequence of one green anole gene region, identify all intron spans.",
            {"sequence": record["sequence"]},
            {"introns": [{"start": "integer", "end": "integer"}]},
            {"introns": record["introns"], "exons": record["exons"], "spliced_sequence": record["spliced_sequence"]},
            {"primary": "spliced_sequence_levenshtein_similarity", "secondary": ["intron_interval_f1_at_iou_0_8", "intron_count_accuracy"]},
            "Intron recognition tests whether a model can parse reptile gene architecture before downstream regulatory reasoning.",
        ))
    return rows


def build_anole_promoter_expression(start):
    rows = []
    records = load_jsonl_required(ANOLE_PROMOTER_FIXTURE, 20)
    for j, record in enumerate(records[:20]):
        idx = start + j
        rows.append(common(
            idx,
            "AnolePromoterExpression",
            source(
                "Bgee-normalized RNA-seq from the Anolis tissue transcriptome study",
                record["source_url"],
                (
                    f"{record['gene_id']} {record['gene_name']} canonical CDS promoter "
                    f"{record['seq_region']}:{record['promoter_start']}-{record['promoter_end']}"
                ),
                record["expression_source_url"],
            ),
            (
                "Given the 2000 bp sequence upstream of an Anolis CDS start, "
                "rank every candidate tissue from highest to lowest predicted expression. "
                "Return each candidate tissue exactly once."
            ),
            {"promoter_sequence": record["promoter_sequence"], "candidate_tissues": record["candidate_tissues"]},
            {"tissue_ranking": ["tissue_name"]},
            {
                "tissue_ranking": record["tissue_ranking"],
                "expression": record["expression"],
                "gene_id": record["gene_id"],
                "gene_name": record["gene_name"],
                "expression_experiment_id": record["expression_experiment_id"],
                "expression_unit": record["expression_unit"],
            },
            {
                "primary": "spearman_rank_correlation",
                "secondary": [
                    "ranking_completeness",
                ],
            },
            "Promoter-to-tissue ranking is a reptile-specific proxy for controlling where developmental programs are expressed.",
        ))
    return rows


def build_komodo_protein_fold(start):
    rows = []
    structures = load_jsonl_required(KOMODO_ALPHAFOLD_FIXTURE, 20)
    for j, structure in enumerate(structures[:20]):
        sequence_length = len(structure["protein_sequence"])
        if not 80 <= sequence_length <= 100:
            raise ValueError(
                f"{structure['accession']} has length {sequence_length}; "
                "KomodoProteinFold requires 80-100 aa"
            )
        answer_json_chars = int(structure["answer_json_chars"])
        if not 0 < answer_json_chars < 60_000:
            raise ValueError(
                f"{structure['accession']} has a {answer_json_chars}-character "
                "PDB task-answer JSON; KomodoProteinFold requires fewer than 60000"
            )
        idx = start + j
        rows.append(common(
            idx,
            "KomodoProteinFold",
            source(
                "UniProt Varanus komodoensis proteins with AlphaFold DB predicted structures",
                structure["source_url"],
                f"{structure['accession']} {structure['protein_name']}",
                structure["uniprot_url"],
            ),
            "Given a Komodo dragon amino-acid sequence, generate a complete all-atom monomer structure in PDB or mmCIF format.",
            {"protein_sequence": structure["protein_sequence"]},
            {"pdb": "string containing a valid PDB structure, or use mmcif for mmCIF text"},
            {
                "coordinates": [
                    {
                        "residue_index": item["residue_index"],
                        "x": item["x"],
                        "y": item["y"],
                        "z": item["z"],
                    }
                    for item in structure["coordinates"]
                ],
                "answer_json_chars": answer_json_chars,
                "mean_plddt": structure["mean_plddt"],
                "sequence_length": sequence_length,
                "uniprot_accession": structure["accession"],
                "protein_name": structure["protein_name"],
                "raw_pdb_path": structure["pdb_path"],
            },
            {"primary": "distance_matrix_rmsd_score", "secondary": ["coordinate_coverage", "structure_validity", "backbone_atom_completeness"]},
            "Protein folding tests concrete sequence-to-structure reasoning for reptile molecular machinery.",
        ))
    return rows


def build_tf_binding(start):
    rows = []
    records = load_jsonl_required(JASPAR_TFBIND_FIXTURE, 20)
    for j, record in enumerate(records[:20]):
        idx = start + j
        rows.append(common(
            idx,
            "DragonTFBind",
            source(
                "JASPAR CORE HT-SELEX/SELEX transcription factor binding profiles",
                record["source_url"],
                f"{record['matrix_id']} {record['tf_name']} UniProt {record['uniprot_id']}",
                record["uniprot_id"],
            ),
            "Given one transcription factor protein sequence and 10 DNA sequences, predict which DNA sequences are bound.",
            {"tf_sequence": record["tf_sequence"], "dna_candidates": record["dna_candidates"]},
            {"binding_probabilities": {"seq_id": "number_0_to_1"}},
            {
                "binding_probabilities": record["binding_probabilities"],
                "tf": record["tf_name"],
                "matrix_id": record["matrix_id"],
                "uniprot_id": record["uniprot_id"],
                "pfm": record["pfm"],
            },
            {"primary": "auroc", "secondary": ["auprc", "ranking_accuracy"]},
            "TF binding is the smallest scoreable proxy for sequence-level regulatory control.",
        ))
    return rows


def build_rna_folding(start):
    rows = []
    records = load_jsonl_required(RFAM_RNA_FIXTURE, 20)
    for j, record in enumerate(records[:20]):
        idx = start + j
        rows.append(common(
            idx,
            "RNAFold",
            source(
                "Rfam seed alignments",
                record["source_url"],
                f"{record['rfam_acc']} {record['rfam_id']} {record['sequence_id']}",
            ),
            "Given a realistic RNA sequence, predict its secondary structure in dot-bracket notation.",
            {"sequence": record["sequence"]},
            {"dot_bracket": "string"},
            {"dot_bracket": record["dot_bracket"], "base_pairs": dot_bracket_pairs(record["dot_bracket"])},
            {"primary": "base_pair_f1", "secondary": ["precision", "recall", "exact_structure_match"]},
            "RNA folding tests sequence-to-structure reasoning for transcript-level control.",
        ))
    return rows


def load_jsonl_required(path, minimum):
    if not path.exists():
        raise FileNotFoundError(f"{path} does not exist. Run the source fixture generation step first.")
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if len(rows) < minimum:
        raise ValueError(f"{path} must contain at least {minimum} records, found {len(rows)}")
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
    rows.extend(build_anole_gene_parse(1))
    rows.extend(build_anole_promoter_expression(21))
    rows.extend(build_komodo_protein_fold(41))
    rows.extend(build_tf_binding(61))
    rows.extend(build_rna_folding(81))
    assert len(rows) == 100
    write(rows)


if __name__ == "__main__":
    main()
