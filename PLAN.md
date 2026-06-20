# DragonBench Eval v0 Plan

DragonBench Eval v0 is a small, human-reviewed evaluation set for genetics-focused "dragon design" reasoning. The eval should be high precision, dataset-backed, and stable. It is intentionally separate from larger RL/SFT datasets.

## Target Size

- 5 tasks
- 20 questions per task
- 100 total questions
- All questions must be reviewed before they become locked eval items

This size is large enough to compare model behavior across task families, but small enough for humans to inspect every example.

## Core Rule

A question can enter the locked eval only if it has:

- a named public source dataset
- a stable source record, accession, file, or genomic/protein coordinate
- a fixed input/output schema
- a hidden answer derived from the source dataset
- an automatic scoring function
- no requirement that the evaluated model query a database or the internet
- a clear reason it belongs in the dragon genetics story

## Eval Tasks

### 1. DragonGeneParse

Goal: predict gene structure from DNA sequence.

Primary sources:

- GENCODE human/mouse annotations
- Ensembl reptile genome annotations
- NCBI RefSeq reptile annotations where Ensembl coverage is weak

Inputs:

- species
- assembly
- strand
- genomic sequence window
- transcript policy

Outputs:

- exon intervals
- splice donor positions
- splice acceptor positions
- optional CDS intervals

Scoring:

- splice junction F1
- exon interval F1 at exact boundary or tolerance
- per-base exon/intron MCC
- CDS frame validity

### 2. DragonTFBind

Goal: predict transcription-factor binding intervals or motif windows from sequence.

Primary sources:

- JASPAR CORE motif profiles
- ENCODE TF ChIP-seq peaks
- ReMap TF binding atlas

Inputs:

- species
- cell type when applicable
- TF name or motif ID
- one or more DNA sequences

Outputs:

- predicted binding intervals
- strand where applicable
- confidence

Scoring:

- interval F1 at IoU >= 0.5
- AUPRC over candidate windows
- distance to motif center or ChIP-seq summit
- calibration / Brier score for confidence

### 3. DragonEnhancerTissue

Goal: predict tissue-specific regulatory activity from noncoding DNA.

Primary sources:

- VISTA Enhancer Browser
- ENCODE cCREs / SCREEN
- FANTOM5 enhancer/promoter activity
- reptile limb ATAC-seq or conserved noncoding element datasets when source records are verified

Inputs:

- species
- developmental stage or cell/tissue context
- candidate enhancer sequence
- candidate tissue labels

Outputs:

- active/inactive probability
- multi-label tissue activity probabilities

Scoring:

- multi-label AUROC/AUPRC
- exact active/inactive accuracy
- tissue ontology similarity
- calibration error

### 4. DragonVariantEffect

Goal: predict functional effects of protein or splice-affecting variants.

Primary sources:

- ProteinGym
- MaveDB
- massively parallel splicing assays for splice-specific variants

Inputs:

- wild-type sequence
- variant list
- assay definition

Outputs:

- predicted score per variant
- optional functional/neutral class

Scoring:

- Spearman rank correlation
- Pearson correlation
- top-k enrichment
- binary AUROC/AUPRC when labels are thresholded

### 5. DragonPhenotypeGene

Goal: predict phenotype labels from gene perturbation data.

Primary sources:

- IMPC / KOMP mouse knockout phenotypes
- MGI genotype-phenotype annotations
- ZFIN zebrafish phenotypes and expression
- FlyBase Drosophila allele/gene phenotypes

Inputs:

- species
- gene sequence or protein sequence
- perturbation type
- candidate phenotype terms

Outputs:

- multi-label phenotype probabilities

Scoring:

- macro AUROC/AUPRC
- precision@k
- recall@k
- ontology-aware similarity where available

## Reptile and Non-Reptile Mix

The eval should use both reptile-specific and non-reptile datasets.

Recommended long-term locked-eval balance:

- 60 non-reptile examples
- 25 reptile-specific examples
- 15 cross-species or comparative examples

Current seed balance:

- 60 non-reptile examples
- 12 reptile-specific examples
- 28 cross-species or comparative examples

The seed set is conservative about reptile-specific labels because reptile phenotype and variant-effect sources are much thinner than human, mouse, fly, zebrafish, and protein assay sources. Reptile-specific cards should be increased only after exact accessions and labels are verified.

Reptile-specific examples should initially focus on:

- reptile gene annotation
- reptile expression/transcript annotation
- reptile limb regulatory elements
- reptile conserved noncoding elements

Avoid reptile-specific knockout phenotype tasks unless a sufficiently curated, public, machine-readable source is verified.

## Candidate Review Workflow

Each candidate question starts with:

- `status: candidate_needs_human_review`
- `hidden_answer_status: needs_source_extraction`
- source names and intended source records
- scoring function
- acceptance checks

A human reviewer promotes a question to locked eval only after:

1. The source record is verified.
2. The model-facing input is finalized.
3. The hidden answer is extracted and stored.
4. The scoring function runs successfully.
5. The example is checked for leakage, ambiguity, and biological plausibility.

## Dataset Layout

```text
eval/
  dragonbench_eval_v0.seed.jsonl      # 100 source-curation candidate cards
  dragonbench_eval_v0.scoreable.jsonl # 100 runnable scoreable bootstrap cards
  dragonbench_eval_v0.locked.jsonl    # reviewed eval items only

schemas/
  eval_question.schema.json            # candidate/locked question contract

data/
  jaspar/
    MA0139.1_CTCF.jaspar              # first retrieved public source example

examples/
  dragon_tfbind_jaspar_ctcf_episode.json
```

## Current Runnable Harness Dataset

`eval/dragonbench_eval_v0.scoreable.jsonl` is the HUD-facing bootstrap dataset. It contains 100 scoreable cards with verified hidden answers:

- 20 `DragonGeneParse`
- 20 `DragonTFBind`
- 20 `DragonEnhancerTissue`
- 20 `DragonVariantEffect`
- 20 `DragonPhenotypeGene`

This file exists so the harness can run end-to-end immediately. The earlier `seed` file is only a source-curation scaffold and should not be used for model evaluation.

## Split Rules for Larger RL/SFT Data

When scaling beyond the 100-question eval:

- split GeneParse by chromosome or genomic locus, not random exon
- split VariantEffect by protein family or assay, not random variant
- split TFBind by TF, cell type, or genomic region
- split PhenotypeGene by orthology group or phenotype family
- hold out whole reptile species when possible

The 100-question eval must never be used for SFT or RL training.
