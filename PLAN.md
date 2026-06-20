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

### 1. DragonGeneParseIntrons

Goal: identify intron intervals from genomic DNA sequence.

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

- intron intervals

Scoring:

- intron interval F1 at IoU >= 0.8
- intron boundary score
- intron count accuracy

### 2. DragonAnolePromoterExpression

Goal: predict Anolis tissue expression ranking from the 2000 bp sequence upstream of CDS start.

Primary sources:

- Anolis expression atlas / reannotation datasets
- Ensembl Anolis genome annotation
- NCBI RefSeq reptile annotations where needed

Inputs:

- species: `Anolis carolinensis`
- 2000 bp promoter sequence upstream of CDS start
- candidate tissue list

Outputs:

- ordered tissues, highest predicted expression first

Scoring:

- NDCG across all candidate tissues
- top-1 tissue accuracy
- Spearman rank correlation

### 3. DragonProteinFolding

Goal: predict residue-residue contacts from protein sequence.

Primary sources:

- PDB
- CASP/CAMEO-style held-out structure targets

Inputs:

- protein sequence
- whether MSA/templates are allowed

Outputs:

- residue contact pairs with confidence

Scoring:

- contact F1
- contact precision/recall
- contact count accuracy

### 4. DragonTFBind

Goal: predict transcription-factor binding intervals from sequence.

Primary sources:

- JASPAR CORE motif profiles
- ENCODE TF ChIP-seq peaks
- ReMap TF binding atlas

Inputs:

- species
- TF name or motif ID
- one or more DNA sequences

Outputs:

- predicted binding intervals
- strand where applicable
- confidence

Scoring:

- interval F1 at IoU >= 0.5
- distance to motif center or ChIP-seq summit
- confidence presence/calibration

### 5. DragonRNAFolding

Goal: predict RNA secondary structure from sequence.

Primary sources:

- bpRNA
- ArchiveII
- Rfam

Inputs:

- RNA sequence
- pseudoknot policy

Outputs:

- dot-bracket secondary structure

Scoring:

- base-pair F1
- exact dot-bracket match
- output length validity

## Reptile and Non-Reptile Mix

The eval should use both reptile-specific and non-reptile datasets.

Recommended long-term locked-eval balance:

- 60 non-reptile examples
- 25 reptile-specific examples
- 15 cross-species or comparative examples

Current scoreable bootstrap balance:

- 29 non-reptile examples
- 26 reptile-specific examples
- 45 cross-species or comparative examples

The scoreable bootstrap set uses deterministic controls with source-family metadata. It should be replaced progressively with source-extracted records while preserving the same schemas and scorers.

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

- 20 `DragonGeneParseIntrons`
- 20 `DragonAnolePromoterExpression`
- 20 `DragonProteinFolding`
- 20 `DragonTFBind`
- 20 `DragonRNAFolding`

This file exists so the harness can run end-to-end immediately. The earlier `seed` file is only a source-curation scaffold and should not be used for model evaluation.

## Split Rules for Larger RL/SFT Data

When scaling beyond the 100-question eval:

- split GeneParseIntrons by chromosome or genomic locus, not random intron
- split AnolePromoterExpression by gene family or held-out tissue/gene sets
- split ProteinFolding by protein family or fold, not random contact
- split TFBind by TF, cell type, or genomic region
- split RNAFolding by RNA family, not random sequence
- hold out whole reptile species when possible

The 100-question eval must never be used for SFT or RL training.
