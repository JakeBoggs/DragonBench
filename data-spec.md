# Dragon Genetics Benchmark Spec v0.1

## Goal

Create a 100-question genetics benchmark with 20 questions in each of five categories:

1. Anole gene parsing: identify intron spans inside genes.
2. Anole promoter expression: rank tissues by expression from a 2 kb upstream sequence.
3. Komodo dragon protein folding: generate an all-atom PDB/mmCIF structure from an amino-acid sequence.
4. TF binding: given a transcription factor and 10 DNA sequences, predict relative binding probabilities.
5. RNA folding: predict secondary structure for realistic RNA sequences.

The focus is on selecting high-quality examples rather than maximizing dataset size.

---

# Category 1: `AnoleGeneParse`

## Task

Given the genomic DNA sequence of one green anole gene region, identify all intron spans.

## Input

```json
{
  "sequence": "ACGT..."
}
```

## Output

```json
{
  "introns": [
    {"start": 150, "end": 620},
    {"start": 900, "end": 1250}
  ]
}
```

## Dataset

Use a single Anolis carolinensis annotation source throughout the benchmark.

Preferred sources:

* NCBI RefSeq Anolis carolinensis annotation
* Transcriptome-supported Anolis carolinensis reannotation

## Selection criteria

Only include genes that are:

* protein-coding;
* represented by a single chosen transcript;
* between 1,000 and 5,000 bp in total span;
* contain 1–5 introns;
* free of ambiguous bases;
* reasonably clean and unambiguous in annotation.

## Selecting 20 questions

Aim for a mix of intron counts:

* 5 genes with 1 intron;
* 5 genes with 2 introns;
* 5 genes with 3 introns;
* 5 genes with 4–5 introns.

Include a range of sequence lengths across the 1–5 kb range.

## Scoring

Compare the ground-truth and predicted spliced sequences using:

`max(0, 1 - Levenshtein distance / (original sequence length - ground-truth spliced sequence length))`

---

# Category 2: `AnolePromoterExpression`

## Task

Given the 2,000 bp sequence upstream of the CDS start for an Anolis carolinensis gene, predict the ordered ranking of tissues by expression.

## Input

```json
{
  "promoter_sequence": "ACGT...",
  "candidate_tissues": [
    "adrenal_gland",
    "brain",
    "dewlap_skin",
    "embryo",
    "heart",
    "liver",
    "lung",
    "ovary",
    "skeletal_muscle"
  ]
}
```

## Output

```json
{
  "tissue_ranking": [
    "adrenal_gland",
    "brain",
    "dewlap_skin",
    "embryo",
    "heart",
    "liver",
    "lung",
    "ovary",
    "skeletal_muscle"
  ]
}
```

The output must contain every candidate tissue exactly once.

## Dataset

Use Bgee 15.2 TPM values for experiment `SRP009831`, derived from the
Anolis carolinensis tissue transcriptome study:

* Eckalbar et al. 2013, DOI `10.1186/1471-2164-14-49`;
* adrenal gland, brain, dewlap skin, pooled embryo, heart, liver, lung,
  ovary, and skeletal muscle;
* Bgee-normalized data from a single experiment and processing pipeline.

The separately prepared 28- and 38-somite embryo libraries and the
tail-regeneration samples are excluded to avoid cross-protocol and
non-baseline comparisons.

## Selection criteria

Only include genes that:

* are protein-coding;
* have a clearly defined CDS start;
* have a full 2 kb upstream region available;
* have measurable expression in at least seven of the nine tissues;
* have at least 10 TPM in the top-ranked tissue;
* have a top-to-second expression ratio of at least 1.5.

Prefer genes where:

* the ranking is biologically meaningful and not nearly flat.

Avoid:

* housekeeping genes expressed similarly everywhere;
* genes with weak expression across all tissues;
* genes whose tissue rankings are unstable or noisy.

## Selecting 20 questions

Try to cover multiple tissue classes:

* every candidate tissue is represented as the top-ranked tissue;
* no two selected genes have the same complete tissue ordering;
* top-tissue frequencies are approximately balanced.

The exact distribution is less important than selecting clear, high-confidence examples.

## Scoring

The submission must contain every candidate tissue exactly once.
Incomplete rankings, duplicates, or unknown tissues score zero.

```text
reward = max(0, Spearman rank correlation)
```

Negative correlations are clipped to zero, so inverse rankings score zero.

---

# Category 3: `KomodoProteinFold`

## Task

Given a Komodo dragon amino-acid sequence, generate a complete all-atom monomer structure in PDB.

## Input

```json
{
  "protein_sequence": "M..."
}
```

## Output

A valid PDB or mmCIF structure for the protein.

## Dataset

Use Komodo dragon protein sequences together with a consistent structure source.

## Selection criteria

Choose proteins that are structurally clean and interesting.

Prefer proteins that:

* are 80–100 amino acids long;
* are likely monomeric;
* have compact, well-defined folds;
* have little intrinsic disorder;
* represent a variety of biological functions.

The complete reference PDB task-answer JSON must remain below 60,000 characters.
The size check ensures the complete all-atom structure fits directly in the
model response and HUD transport.

Avoid:

* highly disordered proteins;
* proteins with unresolved regions.

## Selecting 20 questions

Aim for structural diversity:

* enzymes;
* signaling proteins;
* structural proteins;
* metabolic proteins;
* other biologically interesting Komodo proteins.

## Scoring

Primary metric:

* C-alpha lDDT over reference residue pairs within 15 Å.

Secondary metrics:

* coordinate coverage;
* structural completeness;
* validity of the generated structure file.

---

# Category 4: `DragonTFBind`

## Task

Given one transcription factor protein sequence and 10 DNA sequences, predict relative binding probabilities for the DNA sequences.

## Input

```json
{
  "tf_sequence": "M...",
  "dna_candidates": [
    {"id": "seq_01", "sequence": "ACGT..."},
    {"id": "seq_02", "sequence": "TGCA..."}
  ]
}
```

## Output

```json
{
  "binding_probabilities": {
    "seq_01": "<number from 0 through 1>",
    "seq_02": "<number from 0 through 1>"
  }
}
```

## Dataset

Use an in-vitro TF binding dataset where full transcription factor sequences are available.

SMiLE-seq is the preferred starting point because it is closest to the intended task format.

## Selection criteria

Choose transcription factors that:

* have full protein sequences available;
* have clear sequence-specific DNA binding preferences;
* have enough positive and negative DNA examples.

For each question:

* provide exactly 10 DNA sequences;
* include a mix of strong binders, weak/intermediate binders, and non-binders;
* shuffle candidate order and reassign candidate IDs after candidate selection
  so IDs do not encode binding rank;
* keep sequence lengths reasonably consistent.

Avoid:

* TFs that only function as obligate heterodimers;
* ambiguous binding datasets;

## Selecting 20 questions

Prefer 20 distinct transcription factors.

Try to cover multiple TF families:

* homeodomain;
* zinc finger;
* bHLH;
* bZIP;
* nuclear receptor;
* forkhead and related families.

## Scoring

Primary metric:

* chance-clipped Spearman rank correlation over predicted and reference binding probabilities.

The answer must include exactly one probability for every candidate DNA sequence ID.

---

# Category 5: `RNAFold`

## Task

Given a realistic RNA sequence, predict its secondary structure.

## Input

```json
{
  "sequence": "AUGC..."
}
```

## Output

```json
{
  "dot_bracket": "..(((...))).."
}
```

## Dataset

Pick a curated RNA secondary-structure datasets such as:

* bpRNA;
* Rfam-derived structures;
* experimentally supported RNA structure collections.

## Selection criteria

Choose RNAs that:

* are 50–250 nucleotides long;
* contain only A, C, G, and U;
* have complete secondary-structure annotations;
* contain meaningful stem-loop structure.

Prefer:

* realistic biological RNAs;
* diverse structural motifs;
* moderate complexity.

Avoid:

* pseudoknots in the initial version;
* highly repetitive sequences;
* trivial single-hairpin examples;
* extremely famous textbook examples that are likely memorized.

## Selecting 20 questions

Aim for structural diversity:

* tRNAs;
* riboswitches;
* miRNA precursors;
* structured ncRNAs;
* rRNA or related fragments.

Avoid selecting many highly similar sequences from the same family.

## Scoring

Primary metric:

* base-pair F1.

Secondary metrics:

* precision and recall of predicted base pairs;
* exact structure match for shorter RNAs;
* structural distance metrics.
