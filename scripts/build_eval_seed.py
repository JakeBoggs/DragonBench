import json
from pathlib import Path


VERSION = "dragonbench_eval_v0"
OUT = Path("eval/dragonbench_eval_v0.seed.jsonl")


def review_notes():
    return {
        "review_status": "not_started",
        "acceptance_checks": [
            "source record verified",
            "model-facing input finalized",
            "hidden answer extracted",
            "scorer run on answer",
            "leakage and ambiguity checked"
        ],
        "notes": "Candidate card for human review before promotion to locked eval."
    }


def card(idx, task, lineage, source, prompt, model_input, output_schema, scoring, relevance, hidden=None):
    return {
        "id": f"DBEVAL-V0-{idx:03d}",
        "version": VERSION,
        "task": task,
        "status": "candidate_needs_human_review",
        "lineage": lineage,
        "source": source,
        "question": {
            "prompt": prompt,
            "model_input": model_input,
            "dragon_relevance": relevance
        },
        "expected_output_schema": output_schema,
        "hidden_answer": hidden or {
            "status": "needs_source_extraction",
            "answer": None
        },
        "scoring": scoring,
        "human_review": review_notes()
    }


SOURCES = {
    "gencode": {
        "primary_dataset": "GENCODE",
        "secondary_dataset": None,
        "source_url": "https://www.gencodegenes.org/",
        "record_hint": "Human or mouse comprehensive annotation, selected transcript window",
        "license_notes": "Verify release-specific terms before redistribution."
    },
    "ensembl_reptile": {
        "primary_dataset": "Ensembl reptile genome annotations",
        "secondary_dataset": "NCBI RefSeq when needed",
        "source_url": "https://www.ensembl.org/",
        "record_hint": "Annotated reptile gene window, preferably Anolis carolinensis or another well-annotated reptile",
        "license_notes": "Verify assembly and annotation release before locking."
    },
    "jaspar": {
        "primary_dataset": "JASPAR CORE",
        "secondary_dataset": None,
        "source_url": "https://jaspar.elixir.no/",
        "record_hint": "Curated TF binding profile, e.g. MA0139.1 CTCF",
        "license_notes": "Open database; cite JASPAR release used."
    },
    "encode_remap": {
        "primary_dataset": "ENCODE TF ChIP-seq",
        "secondary_dataset": "ReMap",
        "source_url": "https://www.encodeproject.org/",
        "record_hint": "TF/cell-type peak set with matched sequence windows",
        "license_notes": "Verify experiment accession and metadata terms."
    },
    "vista": {
        "primary_dataset": "VISTA Enhancer Browser",
        "secondary_dataset": "ENCODE cCREs / FANTOM5",
        "source_url": "https://enhancer.lbl.gov/",
        "record_hint": "In vivo validated enhancer with tissue labels",
        "license_notes": "Verify image/sequence redistribution policy before locking."
    },
    "reptile_regulatory": {
        "primary_dataset": "Reptile limb regulatory ATAC/CNE datasets",
        "secondary_dataset": "Tegu/anole/snake comparative regulatory studies",
        "source_url": "https://www.ncbi.nlm.nih.gov/geo/",
        "record_hint": "Embryonic limb ATAC-seq peak or conserved noncoding element with verified accession",
        "license_notes": "Exact accession must be verified before locking."
    },
    "proteingym": {
        "primary_dataset": "ProteinGym",
        "secondary_dataset": "MaveDB",
        "source_url": "https://proteingym.org/",
        "record_hint": "Deep mutational scanning assay with wild-type sequence and variant scores",
        "license_notes": "Verify assay-specific license and citation."
    },
    "mavedb": {
        "primary_dataset": "MaveDB",
        "secondary_dataset": "ProteinGym",
        "source_url": "https://www.mavedb.org/",
        "record_hint": "Multiplexed assay of variant effect score table",
        "license_notes": "Verify score-set license and citation."
    },
    "impc": {
        "primary_dataset": "IMPC",
        "secondary_dataset": "MGI",
        "source_url": "https://www.mousephenotype.org/",
        "record_hint": "Mouse knockout gene with Mammalian Phenotype labels",
        "license_notes": "Verify data release and attribution."
    },
    "zfin_flybase": {
        "primary_dataset": "ZFIN or FlyBase",
        "secondary_dataset": None,
        "source_url": "https://zfin.org/",
        "record_hint": "Curated developmental or body-part phenotype annotation",
        "license_notes": "Verify source-specific redistribution terms."
    }
}


def gene_parse_cards(start):
    cards = []
    lineages = ["non_reptile"] * 14 + ["reptile_specific"] * 4 + ["cross_species"] * 2
    for i, lineage in enumerate(lineages, start=start):
        source = SOURCES["ensembl_reptile"] if lineage == "reptile_specific" else SOURCES["gencode"]
        species = "Anolis carolinensis" if lineage == "reptile_specific" else ("mouse" if i % 2 else "human")
        cards.append(card(
            i,
            "DragonGeneParse",
            lineage,
            source,
            "Given a genomic DNA window and strand, predict exon intervals and splice junctions for the selected transcript.",
            {
                "species": species,
                "assembly": "source_release_to_verify",
                "strand": "+" if i % 3 else "-",
                "sequence_window": "TO_EXTRACT_FROM_SOURCE",
                "coordinate_system": "0-based, end-exclusive",
                "transcript_policy": "single selected canonical or longest coding transcript"
            },
            {
                "exons": [{"start": "integer", "end": "integer"}],
                "splice_donors": ["integer"],
                "splice_acceptors": ["integer"],
                "cds_intervals": [{"start": "integer", "end": "integer"}]
            },
            {
                "primary": "splice_junction_f1",
                "secondary": ["exon_interval_f1", "per_base_exon_intron_mcc", "cds_frame_validity"]
            },
            "Dragon-like morphology requires reading gene structure before reasoning about regulation, variants, or phenotypes."
        ))
    return cards


def tfbind_cards(start):
    cards = []
    lineages = ["non_reptile"] * 13 + ["reptile_specific"] * 2 + ["cross_species"] * 5
    for offset, lineage in enumerate(lineages):
        i = start + offset
        source = SOURCES["jaspar"] if offset < 8 else SOURCES["encode_remap"]
        if lineage == "reptile_specific":
            source = SOURCES["reptile_regulatory"]
        hidden = None
        model_input = {
            "species": "synthetic" if offset < 8 else "human",
            "cell_type": None if offset < 8 else "source_cell_type_to_verify",
            "tf": "CTCF" if offset == 0 else "TF_TO_VERIFY",
            "sequences": [{"id": "seq_001", "sequence": "TO_EXTRACT_OR_GENERATE_FROM_SOURCE"}],
            "coordinate_system": "0-based, end-exclusive"
        }
        if offset == 0:
            model_input = {
                "species": "synthetic",
                "cell_type": None,
                "tf": "CTCF",
                "sequences": [
                    {
                        "id": "seq_001",
                        "sequence": "AACGTGACCTAGGTCATGCACTTAGGACCTTGGCCACCAGGGGGCGCTATTCGATCCGTAAGCTT"
                    },
                    {
                        "id": "seq_002",
                        "sequence": "GATCTTACGACTAGCTAGGATCCATATCGGATCGTAGCTAACGATCGGATCTAGCATCGATCGA"
                    }
                ],
                "coordinate_system": "0-based, end-exclusive"
            }
            hidden = {
                "status": "extracted",
                "answer": {
                    "binding_intervals": [
                        {"sequence_id": "seq_001", "start": 30, "end": 49, "strand": "+", "label_type": "embedded_jaspar_ctcf_consensus"}
                    ]
                }
            }
        cards.append(card(
            i,
            "DragonTFBind",
            lineage,
            source,
            "Predict transcription-factor binding intervals in the provided DNA sequence windows.",
            model_input,
            {
                "predictions": [
                    {
                        "sequence_id": "string",
                        "start": "integer",
                        "end": "integer",
                        "strand": "string_or_null",
                        "confidence": "number_0_to_1"
                    }
                ]
            },
            {
                "primary": "interval_f1_at_iou_0_5",
                "secondary": ["auprc_over_candidate_windows", "mean_center_distance", "brier_score"]
            },
            "Regulatory switches are a core mechanism for changing where and when developmental programs activate.",
            hidden
        ))
    return cards


def enhancer_cards(start):
    cards = []
    lineages = ["non_reptile"] * 10 + ["reptile_specific"] * 6 + ["cross_species"] * 4
    for offset, lineage in enumerate(lineages):
        i = start + offset
        source = SOURCES["reptile_regulatory"] if lineage == "reptile_specific" else SOURCES["vista"]
        cards.append(card(
            i,
            "DragonEnhancerTissue",
            lineage,
            source,
            "Given a candidate regulatory DNA sequence and candidate tissues, predict tissue-specific activity.",
            {
                "species": "reptile_to_verify" if lineage == "reptile_specific" else "mouse",
                "developmental_stage": "source_stage_to_verify",
                "sequence": "TO_EXTRACT_FROM_SOURCE",
                "candidate_tissues": ["limb", "forebrain", "midbrain", "heart", "branchial_arch", "neural_tube"]
            },
            {
                "active": "boolean_or_probability",
                "tissues": {"tissue_name": "probability_0_to_1"}
            },
            {
                "primary": "macro_auprc_tissue_activity",
                "secondary": ["macro_auroc", "active_inactive_accuracy", "calibration_error"]
            },
            "Dragon-like body plans depend on regulatory DNA activating traits in the right tissues at the right developmental stages."
        ))
    return cards


def variant_cards(start):
    cards = []
    lineages = ["non_reptile"] * 15 + ["cross_species"] * 5
    for offset, lineage in enumerate(lineages):
        i = start + offset
        source = SOURCES["proteingym"] if offset < 12 else SOURCES["mavedb"]
        cards.append(card(
            i,
            "DragonVariantEffect",
            lineage,
            source,
            "Given a wild-type protein sequence, variant list, and assay definition, predict relative functional scores.",
            {
                "wild_type_protein": "TO_EXTRACT_FROM_SOURCE",
                "variants": ["VARIANT_LIST_TO_EXTRACT"],
                "assay_definition": "higher score means higher measured function unless source says otherwise"
            },
            {
                "variant_scores": [
                    {"variant": "string", "predicted_score": "number"}
                ]
            },
            {
                "primary": "spearman_rank_correlation",
                "secondary": ["pearson_correlation", "top_k_enrichment", "binary_auprc_if_thresholded"]
            },
            "Protein function is the molecular substrate for engineered traits; variants must preserve or alter function predictably."
        ))
    return cards


def phenotype_cards(start):
    cards = []
    lineages = ["non_reptile"] * 8 + ["cross_species"] * 12
    for offset, lineage in enumerate(lineages):
        i = start + offset
        source = SOURCES["impc"] if offset < 10 else SOURCES["zfin_flybase"]
        species = "mouse" if offset < 10 else ("zebrafish" if offset < 15 else "Drosophila melanogaster")
        cards.append(card(
            i,
            "DragonPhenotypeGene",
            lineage,
            source,
            "Given a gene, perturbation, and candidate phenotype terms, predict which phenotypes are associated with the perturbation.",
            {
                "species": species,
                "gene_sequence": "TO_EXTRACT_FROM_SOURCE",
                "protein_sequence": "TO_EXTRACT_FROM_SOURCE_IF_AVAILABLE",
                "perturbation": "loss_of_function",
                "candidate_phenotypes": [
                    "abnormal limb morphology",
                    "abnormal craniofacial morphology",
                    "abnormal skin morphology",
                    "abnormal pigmentation",
                    "embryonic lethality"
                ]
            },
            {
                "phenotypes": {"phenotype_term": "probability_0_to_1"}
            },
            {
                "primary": "macro_auprc",
                "secondary": ["macro_auroc", "precision_at_3", "ontology_similarity"]
            },
            "This is the closest public-data proxy for linking genes to morphology, viability, pigmentation, skin, skeleton, and appendage traits."
        ))
    return cards


def main():
    records = []
    records.extend(gene_parse_cards(1))
    records.extend(tfbind_cards(21))
    records.extend(enhancer_cards(41))
    records.extend(variant_cards(61))
    records.extend(phenotype_cards(81))
    if len(records) != 100:
        raise RuntimeError(f"expected 100 records, got {len(records)}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as f:
        for record in records:
            f.write(json.dumps(record, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
