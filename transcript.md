
This is a copy of a shared ChatGPT conversation

Report conversation

Worked for 21s
Assuming RSI = recursive self-improvement, the hackathon-friendly framing is:

In 20 years, we want AI systems that can reason across genotype, development, morphology, biomechanics, metabolism, and safety well enough to design a fantastical organism in simulation.
Today, we build RL environments that test tiny, verifiable slices of that ability.

For safety and practicality, treat “genetically engineering a dragon” as a closed simulated design challenge, not a biological construction plan. The environments should reward models for making predictions or plans that satisfy hidden simulators, public labels, or formal constraints.

The 20-year north star
A future “Dragon Designer” agent receives a high-level spec:

{
  "organism": "fictional dragon-like vertebrate",
  "requirements": {
    "body_plan": "quadruped with wings",
    "locomotion": ["walking", "gliding_or_powered_flight"],
    "integument": "protective scales",
    "thermoregulation": "high heat tolerance",
    "metabolism": "energetically feasible",
    "development": "single viable embryo-to-adult program",
    "safety": "non-invasive, non-pathogenic, non-reproductive outside simulation"
  }
}
The agent outputs a complete simulated organism design: genome-like programs, regulatory networks, protein functions, developmental trajectories, organs, biomechanics, and safety constraints. The only thing that matters is whether it works in simulation and passes validators.

Work backward from that.

A ladder of RL environments
Tier 0: Toy genome literacy
These test whether a model can manipulate formal biological objects correctly.

1. DragonORF-v0
Goal: Identify coding regions in synthetic or real genomic fragments.

Observation:

{
  "species_context": "fictional vertebrate",
  "strand": "+",
  "sequence": "ATG..."
}
Action:

{
  "coding_intervals": [
    {"start": 120, "end": 684}
  ]
}
Reward: exon/CDS boundary F1, frame correctness, valid start/stop codons.

Why it matters: A dragon design system first needs basic sequence reasoning.

2. DragonSplice-v0
Goal: Predict exon/intron structure from raw DNA sequence.

Observation: genomic sequence window, strand, transcript policy.

Action: BED/GFF-like exon intervals.

Reward: splice junction F1, exon boundary accuracy, per-base exon/intron MCC.

Ground truth: public vertebrate gene annotations, but stripped of gene names and accession IDs before being given to the model.

Dragon relevance: developmental and morphological genes rely on correct transcript structure.

3. DragonMotif-v0
Goal: Predict where a transcription factor binds in a set of promoters.

Observation:

{
  "tf": "TF_17",
  "motif_hint": null,
  "promoters": [
    {"id": "p1", "sequence": "ACGT..."},
    {"id": "p2", "sequence": "TGCA..."}
  ]
}
Action:

[
  {"promoter_id": "p1", "start": 50, "end": 63, "confidence": 0.91}
]
Reward: overlap with hidden binding intervals.

Ground truth options: public ChIP-seq, PBM, SELEX, or synthetic motif-insertion datasets.

Dragon relevance: this is the smallest piece of “control where and when traits appear.”

Tier 1: Protein and molecular function
These test whether a model can reason from sequence to structure/function.

4. DragonFold-v0
Goal: Predict a protein structure from sequence only.

Observation: amino-acid sequence.

Action: residue coordinates or contact map.

Reward: TM-score, lDDT, contact precision.

Ground truth: held-out public structures, CASP/CAMEO/PDB-style targets.

Dragon relevance: every engineered trait ultimately depends on proteins doing physical work.

5. DragonVariant-v0
Goal: Predict which protein mutations preserve or improve a function.

Observation:

{
  "wild_type_sequence": "MKT...",
  "variants": ["A12V", "G45D", "L92P"],
  "assay_definition": "higher score means more stable folded protein"
}
Action: predicted score per variant.

Reward: rank correlation with hidden measured scores.

Ground truth: DMS/MAVE datasets.

Dragon relevance: models need to reason about tradeoffs: stability, activity, expression, toxicity, folding.

6. DragonBinder-v0
Goal: Predict which residues participate in binding or catalysis.

Observation: protein sequence, optional ligand class.

Action: residue-level probabilities.

Reward: residue-level precision/recall against structural or curated labels.

Dragon relevance: useful for hypothetical receptors, pigments, structural proteins, signaling pathways.

Tier 2: Regulatory and developmental control
This is where “genetic engineering a body plan” starts to appear, still in a safe simulated form.

7. DragonEnhancer-v0
Goal: Predict tissue-specific regulatory activity from DNA sequence.

Observation:

{
  "sequence": "ACGT...",
  "context": {
    "developmental_stage": "limb_bud",
    "cell_type": "mesenchyme"
  }
}
Action:

{
  "predicted_activity": 0.73
}
Reward: correlation with hidden expression/activity labels.

Ground truth: MPRA/enhancer datasets, or synthetic enhancer grammars.

Dragon relevance: wings, scales, horns, and body proportions require spatially controlled gene expression.

8. DragonGRN-v0
Goal: Infer a gene regulatory network from perturbation data.

Observation: expression matrix across time, perturbations, and tissues.

Action: directed graph of regulatory edges.

Reward: AUROC/AUPRC against hidden network.

Can be real or synthetic: For hackathon purposes, synthetic GRNs are better because you control ground truth exactly.

Dragon relevance: body plans are not single genes; they are regulatory programs.

9. DragonPattern-v0
Goal: Produce a regulatory program that creates a target spatial pattern.

Observation:

{
  "target_pattern": "stripe-like scale primordia across dorsal surface",
  "allowed_modules": ["activator", "repressor", "diffusible_signal", "threshold_sensor"],
  "grid_size": [64, 64]
}
Action: small GRN / reaction-diffusion program.

Reward: image similarity between simulated final pattern and target.

Dragon relevance: scales, pigmentation, horns, claws, and limb fields all involve spatial patterning.

This is one of the best hackathon environments because it is visual, safe, and easy to simulate.

Tier 3: Tissue and organ-level simulators
Now the agent designs abstract developmental modules, not literal lab-ready genomes.

10. DragonLimb-v0
Goal: Create a developmental program that forms a target limb skeleton.

Observation:

{
  "target": "three-segment appendage with five terminal digits",
  "constraints": {
    "left_right_symmetry": true,
    "max_cells": 50000
  }
}
Action: parameters for a toy morphogen/cellular automaton simulator.

Reward: structural similarity to target, symmetry, no invalid growth, no disconnected bones.

Dragon relevance: legs, wings, tails, horns.

11. DragonWing-v0
Goal: Design a simulated wing with enough lift under mass and energy constraints.

Observation: body mass, target glide ratio or flight speed, allowed skeletal/membrane parameters.

Action:

{
  "span": 4.2,
  "area": 3.1,
  "aspect_ratio": 5.7,
  "membrane_stiffness": 0.62,
  "muscle_power_fraction": 0.18
}
Reward: lift-to-drag, energy feasibility, structural stress limits.

Ground truth: physics simulator, not biological database.

Dragon relevance: this directly tests whether the model can respect scaling laws.

This is a great environment because many proposed dragon designs fail on mass, lift, or metabolic budget.

12. DragonScale-v0
Goal: Optimize protective scales under weight/flexibility constraints.

Observation: target body region, attack/abrasion model, max mass, flexibility requirement.

Action: scale geometry/material parameters.

Reward: protection score minus weight and mobility penalties.

Ground truth: simulator.

Dragon relevance: converts “has scales” into a measurable design tradeoff.

13. DragonThermal-v0
Goal: Design a heat-management system for a large active reptile-like animal.

Observation: body size, environment, metabolic heat production.

Action: abstract parameters: insulation, vascular cooling, surface area, behavior policy.

Reward: time spent in viable temperature range, energy cost.

Dragon relevance: large animals need thermal regulation. This is safer and more realistic than asking for “fire-breathing” chemistry.

For the mythic fire trait, I’d use a fictional effect channel like “visible plume intensity” or “heat pulse simulator,” not actual biochemical recipes.

Tier 4: Whole-organism integration
These test cross-domain reasoning.

14. DragonBodyPlan-v0
Goal: Assemble a coherent organism from modules.

Observation:

{
  "desired_traits": ["quadruped", "wings", "tail", "scales"],
  "module_library": ["limb_A", "wing_B", "scale_C", "lung_D"],
  "constraints": {
    "max_mass": 80,
    "min_gait_stability": 0.8,
    "min_glide_ratio": 3.0
  }
}
Action: choose modules and parameter settings.

Reward: multi-objective phenotype score.

Penalties: incompatible modules, impossible mass budget, developmental conflicts.

Dragon relevance: a dragon is not a bag of traits. The traits must fit together.

15. DragonDevelopment-v0
Goal: Find a developmental schedule that reaches the target adult form.

Observation: initial embryo grid, allowed gene modules, target adult morphology.

Action: timed activation policy for modules.

Reward: final morphology match, viability throughout development, low intervention count.

Dragon relevance: this is probably the core “future” environment. It asks: can the model design a process, not just a final object?

16. DragonViability-v0
Goal: Given a proposed organism design, predict whether it is viable.

Observation: full simulated design spec.

Action:

{
  "viability": 0.41,
  "failure_modes": [
    "wing loading too high",
    "metabolic budget negative",
    "developmental module conflict in forelimb field"
  ]
}
Reward: calibration against simulator outcomes and correct failure diagnosis.

Dragon relevance: future systems should be critics before they are designers.

17. DragonPareto-v0
Goal: Optimize tradeoffs among size, flight, armor, growth time, and energy cost.

Observation: target preferences and constraints.

Action: candidate designs.

Reward: hypervolume improvement on Pareto frontier.

Dragon relevance: most interesting biological design is multi-objective optimization.

Tier 5: Recursive self-improvement environments
This connects directly to the RSI theme.

The agent is not just solving one task. It is improving its own search, hypothesis generation, and simulator use.

18. DragonScientist-v0
Goal: Learn an unknown genotype-to-phenotype simulator through experiments.

Observation: budget, previous designs, observed phenotypes.

Action: propose the next batch of simulated designs to test.

Reward: improvement in predictive model accuracy or best design score.

Important: experiments are simulator calls only.

Dragon relevance: this mimics closed-loop biological design without real-world intervention.

19. DragonCurriculum-v0
Goal: The agent designs easier subtasks that help another agent solve the final dragon task.

Observation: final benchmark and learner performance logs.

Action: generate training tasks.

Reward: downstream improvement on held-out dragon tasks.

RSI relevance: this tests whether a model can create environments that improve future models.

20. DragonVerifier-v0
Goal: Given proposed tasks, detect whether they are underspecified, unsafe, unscorable, or contaminated.

Observation: benchmark specification.

Action: critique plus repaired version.

Reward: human/validator score for clarity, safety, and machine-checkability.

RSI relevance: self-improving systems need to improve the evals themselves.

Concrete hackathon MVP
For a hackathon, I would not try to build all of this. I’d build a tiny stack:

MVP: DragonBench
Three environments:

A. MotifDragon
A promoter-binding game.

Input: 20 short DNA sequences.

Hidden rule: one or more motifs, spacing constraints, orientation constraints.

Action: predict binding intervals.

Reward: interval F1.

This represents regulatory control.

B. MorphoDragon
A 2D developmental simulator.

Input: target silhouette: wing, tail, horn, scale pattern.

Action: small gene regulatory program controlling cell growth/differentiation.

Reward: shape similarity, symmetry, low complexity, no tumors/unbounded growth.

This represents development.

C. FlightDragon
A biomechanics optimizer.

Input: body mass and morphology constraints.

Action: wing parameters.

Reward: lift/drag/energy feasibility.

This represents organism-level physics.

Together, these form a nice story:

To engineer a dragon, an AI must learn to control gene regulation, generate morphology through development, and satisfy physical constraints.

That is compelling, safe, and implementable.

Suggested benchmark progression
A clean backward chain from “dragon” to “today”:

Dragon organism
→ viable body plan
→ compatible organs and tissues
→ developmental program
→ gene regulatory networks
→ enhancers/promoters
→ transcription-factor binding
→ DNA/protein sequence reasoning
Each arrow becomes an environment.

You can make the benchmark suite look like this:

Level	Environment	Core capability tested
1	SequenceDragon	ORFs, motifs, splice sites
2	ProteinDragon	fold/function/variant prediction
3	RegulatoryDragon	promoter and enhancer logic
4	PatternDragon	spatial tissue patterning
5	MorphoDragon	developmental body formation
6	BiomechDragon	flight, gait, scaling laws
7	MetabolismDragon	energy and heat budgets
8	BodyPlanDragon	whole-organism integration
9	ScientistDragon	active learning over simulators
10	VerifierDragon	self-improving benchmark design
The important design principle
Do not ask:

“Design a genome for a dragon.”

That is too vague, unsafe, and unscorable.

Ask:

“Given this exact simulated developmental grammar, produce a program that generates a winged quadruped silhouette while satisfying mass, symmetry, and energy constraints.”

That is precise, safe, and benchmarkable.

The best hackathon artifact would be a small Gymnasium-style environment where an agent receives:

{
  "target_traits": ["wing", "tail", "scales"],
  "constraints": {
    "max_mass": 50,
    "bilateral_symmetry": true,
    "min_flight_score": 0.7
  },
  "allowed_gene_modules": ["grow", "inhibit", "differentiate", "signal", "stiffen"]
}
and outputs:

{
  "development_program": [
    {"time": 0, "region": "midline", "module": "signal", "strength": 0.8},
    {"time": 4, "region": "lateral", "module": "grow", "strength": 0.6},
    {"time": 7, "region": "dorsal", "module": "differentiate_scale", "strength": 0.9}
  ],
  "wing_parameters": {
    "span": 3.5,
    "area": 2.1,
    "stiffness": 0.7
  }
}
The simulator returns:

{
  "morphology_score": 0.82,
  "flight_score": 0.64,
  "energy_score": 0.71,
  "safety_score": 1.0,
  "overall_reward": 0.74
}
That gives you a vivid “future of genetic engineering” narrative while staying in the domain of RL environments, RSI, simulators, and measurable reasoning.


No physics sims. Focus on the genetics. You also need to be able to cite specific datasets that could be used for these tasks. If there isn't a good public dataset, we can't create a task out of it

Got it. No physics, no vague “design a dragon genome,” and no database/tool access for the model. The clean hackathon framing is:

Dragon genetics = a stack of closed-book genetic prediction environments.
The model only sees sequences, variants, cell/tissue context, and a strict output schema. The benchmark builder uses public datasets to create hidden labels and rewards.

The “dragon” story becomes a genetic capability ladder: sequence → regulation → development → tissue traits → genotype-to-phenotype.

Hard rule for task inclusion
A task only belongs if it has:

{
  "model_input": "sequence / variant / perturbation / context only",
  "no_model_access": "no database, no accession lookup, no papers",
  "output": "fixed JSON/BED/GFF/PDB/dot-bracket/scalar labels",
  "ground_truth": "specific public dataset",
  "reward": "fully automatic metric"
}
If there is no public dataset with labels, don’t include the task. For example, “predict genes for fire-breathing” should be excluded. There is no public biological ground truth for that.

Genetics-only “dragon engineering” environment ladder
1. DragonGeneParse: find genes, exons, introns, splice sites
Dragon capability being tested: Can the model read raw genome sequence and infer the gene architecture needed before any higher-level engineering?

Model input

{
  "species": "mouse",
  "assembly": "GRCm39",
  "strand": "+",
  "sequence": "ACGT...",
  "transcript_policy": "single selected transcript"
}
Action/output

{
  "exons": [
    {"start": 120, "end": 244},
    {"start": 981, "end": 1120}
  ],
  "splice_donors": [244],
  "splice_acceptors": [981]
}
Datasets

Use GENCODE human/mouse annotations for exon, intron, transcript, CDS, and UTR labels. GENCODE’s stated goal is to identify and classify all gene features in human and mouse genomes with high accuracy based on biological evidence, and current releases provide downloadable comprehensive gene annotations. 

Reward

Splice-junction F1.

Exact exon-boundary F1.

Per-base exon/intron MCC.

CDS frame validity.

Why it belongs: Strong public ground truth; precise; closed-book.

2. DragonSpliceVariant: predict whether a mutation changes splicing
Dragon capability: Can the model predict when a genetic variant disrupts transcript processing?

Model input

{
  "reference_sequence": "ACGT...",
  "variant": {"pos": 317, "ref": "G", "alt": "A"},
  "species": "human",
  "assay": "splicing reporter",
  "output_quantity": "delta_exon_inclusion"
}
Action/output

{
  "delta_exon_inclusion": -0.42,
  "affected_site": "acceptor_loss",
  "confidence": 0.78
}
Datasets

Use massively parallel splicing assay datasets. A 2023 benchmarking study used MPSAs as experimentally determined ground truth and compared predictions for 3,616 variants in five genes. 

Use VastDB for vertebrate alternative splicing profiles across tissues/cell types; it provides quantitative inclusion information for alternative splicing events. 

Reward

Pearson/Spearman correlation for ΔPSI or Δ exon inclusion.

AUROC for splice-disrupting vs neutral.

Correct donor/acceptor gain/loss classification.

Why it belongs: Directly matches “identify introns / splice consequences” and has experimental labels.

3. DragonTFBind: predict TF binding intervals in promoters/enhancers
Dragon capability: Can the model infer regulatory control from DNA sequence?

Model input

{
  "species": "human",
  "cell_type": "K562",
  "tf": "CTCF",
  "sequences": [
    {"id": "seq_001", "sequence": "ACGT..."},
    {"id": "seq_002", "sequence": "TGCA..."}
  ]
}
Action/output

[
  {
    "sequence_id": "seq_001",
    "start": 221,
    "end": 240,
    "strand": "+",
    "confidence": 0.91
  }
]
Datasets

Use ENCODE TF ChIP-seq peaks for cell-type-specific binding labels; ENCODE provides TF ChIP-seq data and pipeline-generated datasets. 

Use ReMap for a larger uniformly processed atlas of public DNA-binding experiments across human, mouse, fly, and Arabidopsis; ReMap 2022 processed more than 11,000 DNA-binding datasets. 

Use JASPAR for motif-only subtasks; JASPAR is an open-access database of curated, non-redundant TF binding profiles. 

Reward

Peak-overlap F1.

Interval IoU.

AUROC over tiled sequence windows.

Distance from predicted motif center to ChIP-seq peak summit.

Dragon link: “Which regulatory switches turn on wing/scale/craniofacial programs?” starts with TF binding.

4. DragonEnhancerTissue: predict tissue-specific enhancer activity
Dragon capability: Can the model map noncoding DNA to where in the embryo it activates expression?

Model input

{
  "species": "mouse",
  "developmental_stage": "embryonic day 11.5",
  "sequence": "ACGT...",
  "candidate_tissues": [
    "limb",
    "forebrain",
    "midbrain",
    "hindbrain",
    "heart",
    "branchial_arch",
    "neural_tube"
  ]
}
Action/output

{
  "active": true,
  "tissues": {
    "limb": 0.82,
    "heart": 0.03,
    "forebrain": 0.11
  }
}
Datasets

Use the VISTA Enhancer Browser, which is a central resource for human and mouse enhancers validated in vivo in transgenic mouse embryos. 

Use FANTOM5 for promoter/enhancer activity across human samples; FANTOM5 identified tens of thousands of active enhancers across many primary cells, tissues, and cell lines using CAGE data. 

Use ENCODE cCREs for candidate cis-regulatory elements in human and mouse genomes; SCREEN exposes the ENCODE Registry of cCREs. 

Reward

Multi-label tissue AUROC/AUPRC.

Exact active/inactive accuracy.

Ontology-aware tissue similarity.

Calibration of tissue probabilities.

Dragon link: This is the most direct genetics-only proxy for “make a wing/scale/horn program activate in the right place.”

5. DragonPromoterExpression: predict promoter/enhancer expression strength
Dragon capability: Can the model predict quantitative regulatory output?

Model input

{
  "sequence": "ACGT...",
  "assay_context": {
    "species": "human",
    "cell_type": "endothelial_cell",
    "measurement": "CAGE_expression"
  }
}
Action/output

{
  "predicted_activity": 2.41
}
Datasets

Use FANTOM5 promoter and enhancer atlases, which include promoter and enhancer activity across many human and mouse samples. 

Use GTEx eQTL/expression data for tissue-specific gene expression and genetic regulation; GTEx v8 includes DNA data from 838 donors and 17,382 RNA-seq samples across 54 tissue sites and two cell lines. 

Reward

Pearson/Spearman correlation.

Top-decile enrichment.

Mean squared error after normalization.

Dragon link: Lets you test whether a model can tune “how much expression” rather than just “on/off.”

6. DragonVariantEffect: predict protein variant function
Dragon capability: Can the model choose mutations likely to preserve or alter a protein function?

Model input

{
  "wild_type_protein": "MKT...",
  "variants": ["A12V", "G45D", "L92P"],
  "assay_definition": "higher score means higher measured activity"
}
Action/output

[
  {"variant": "A12V", "predicted_score": 0.73},
  {"variant": "G45D", "predicted_score": -1.20}
]
Datasets

Use ProteinGym, which contains more than 250 standardized deep mutational scanning assays and over 2.7 million mutated sequences across more than 200 protein families. 

Use MaveDB, a public repository for Multiplexed Assays of Variant Effect datasets. 

Reward

Spearman rank correlation.

Top-k enrichment.

Hit rate above functional threshold.

Calibration error.

Dragon link: A future “dragon genetics” system needs to reason about protein changes without destroying function.

7. DragonProteinFold: predict structure from protein sequence
Dragon capability: Can the model infer molecular machinery from sequence alone?

Model input

{
  "protein_sequence": "MKT...",
  "msa_allowed": false,
  "templates_allowed": false
}
Action/output

PDB/mmCIF coordinates, or simpler contact-map output.

{
  "contacts": [
    {"i": 12, "j": 88, "probability": 0.93}
  ]
}
Datasets

Use CASP targets for blind structure-prediction-style tasks; CASP exists to provide objective testing of structure prediction methods. 

Use CAMEO, which provides weekly automated and independent benchmarking of structure-prediction servers. 

Use RCSB PDB, which archives experimentally determined 3D structures from the Protein Data Bank. 

Reward

TM-score.

lDDT.

Contact precision@L.

RMSD on aligned residues.

Dragon link: Any engineered trait ultimately depends on proteins folding and functioning.

8. DragonRNAFold: predict RNA secondary structure
Dragon capability: Can the model infer regulatory RNA structure from sequence?

Model input

{
  "rna_sequence": "AUGCG..."
}
Action/output

{
  "dot_bracket": "..(((...))).."
}
Datasets

Use bpRNA-1m, which provides RNA sequences with bpseq, FASTA, dot-bracket files, and structure type annotations. 

Use ArchiveII, a widely used RNA secondary-structure benchmark dataset. 

Use Rfam, which represents RNA families with multiple sequence alignments, consensus secondary structures, and covariance models. 

Reward

Base-pair precision/recall/F1.

Exact dot-bracket match for short RNAs.

Pseudoknot-aware score if included.

Dragon link: Noncoding RNAs are part of regulatory control, so this is another genetics-only molecular reasoning task.

9. DragonGeneKnockoutPhenotype: predict phenotype from gene knockout
Dragon capability: Can the model map gene perturbations to organismal traits?

Model input

{
  "species": "mouse",
  "gene_sequence": "ATG...",
  "protein_sequence": "M...",
  "perturbation": "loss_of_function",
  "candidate_phenotypes": [
    "abnormal limb morphology",
    "abnormal craniofacial morphology",
    "abnormal skin morphology",
    "abnormal pigmentation",
    "embryonic lethality"
  ]
}
Action/output

{
  "phenotypes": {
    "abnormal limb morphology": 0.67,
    "abnormal skin morphology": 0.22,
    "embryonic lethality": 0.14
  }
}
Datasets

Use IMPC/KOMP2 knockout mouse phenotyping data; KOMP2 has generated and phenotyped over 5,500 mouse lines, and IMPC provides public knockout mouse phenotype data. 

Use MGI/MGD for curated mouse genotype, allele, phenotype, and disease model annotations. MGI is the international database resource for laboratory mouse genetics/genomics, and its phenotype project covers mutations and strain-specific phenotypes. 

Reward

Multi-label phenotype AUROC.

Precision@k phenotype terms.

Ontology-distance score using Mammalian Phenotype terms.

Exact match for coarse phenotype categories.

Dragon link: This is probably the closest public-data proxy for “which genes affect wings, limbs, skin, skeleton, size, pigmentation, craniofacial traits?”

10. DragonZebrafishDevelopment: predict developmental phenotype/expression in a vertebrate embryo
Dragon capability: Can the model reason about vertebrate development from gene perturbations or expression?

Model input

{
  "species": "zebrafish",
  "gene_sequence": "ATG...",
  "perturbation": "loss_of_function",
  "developmental_stage": "24 hpf",
  "candidate_anatomy_terms": [
    "fin",
    "craniofacial skeleton",
    "pigment cell",
    "heart",
    "neural tube"
  ]
}
Action/output

{
  "affected_anatomy": {
    "fin": 0.74,
    "pigment_cell": 0.38,
    "heart": 0.06
  }
}
Datasets

Use ZFIN, the Zebrafish Information Network, which is the database of genetic and genomic data for zebrafish and includes curated gene expression and phenotype data. 

A ZFIN publication reports large-scale curated gene expression and mutant/knockdown phenotype data, including over 216,000 zebrafish gene-expression assays. 

Reward

Multi-label anatomical phenotype accuracy.

Stage-specific expression/phenotype AUROC.

Ontology-aware term similarity.

Dragon link: Zebrafish give you a real vertebrate development proxy for fins, craniofacial patterning, pigmentation, and embryonic viability.

11. DragonFlyWingGene: predict wing/body-part phenotypes from Drosophila genetics
Dragon capability: Can the model connect gene perturbations to appendage/body-plan phenotypes?

Model input

{
  "species": "Drosophila melanogaster",
  "gene_sequence": "ATG...",
  "perturbation": "loss_of_function",
  "candidate_phenotypes": [
    "abnormal wing morphology",
    "abnormal leg morphology",
    "abnormal bristle morphology",
    "lethal"
  ]
}
Action/output

{
  "phenotypes": {
    "abnormal_wing_morphology": 0.81,
    "lethal": 0.31
  }
}
Datasets

Use FlyBase, which is the central database for Drosophila genetics and molecular biology, including genes, alleles, expression, and phenotypes. 

FlyBase phenotype statements are curated from published literature and attached to alleles. 

Reward

Multi-label phenotype AUROC.

Precision@k phenotype terms.

Coarse body-part phenotype accuracy.

Dragon link: Not vertebrate, but excellent public data for genetic control of wings and body patterning. This is a good hackathon-friendly “wing genetics” environment.

12. DragonTraitQTL: predict trait-associated loci from animal genotype/trait data
Dragon capability: Can the model connect naturally varying genomic regions to traits like size, growth, pigmentation, skeletal features, or integument?

Model input

{
  "species": "chicken",
  "candidate_loci": [
    {"id": "locus_1", "sequence_window": "ACGT..."},
    {"id": "locus_2", "sequence_window": "TGCA..."}
  ],
  "trait": "body size",
  "output": "rank candidate loci by association"
}
Action/output

[
  {"locus_id": "locus_2", "score": 0.88},
  {"locus_id": "locus_1", "score": 0.31}
]
Datasets

Use Animal QTLdb, which collects publicly available QTL, eQTL, candidate gene, GWAS, and CNV data mapped to livestock animal genomes. 

Reward

Rank correlation with association strength.

Top-k locus recovery.

Trait-category accuracy.

Dragon link: This is a genetics-only proxy for selecting traits such as size, growth, pigmentation, skin/scale-like integument, and skeletal morphology from animal genetic data.

13. DragonPerturbExpression: predict expression response to gene perturbation
Dragon capability: Can the model predict how a genetic intervention changes cell state?

Model input

{
  "cell_type": "K562",
  "perturbation_type": "CRISPRi",
  "target_gene_sequence": "ATG...",
  "readout_genes": ["gene_A", "gene_B", "gene_C"]
}
Action/output

{
  "delta_expression": {
    "gene_A": -0.8,
    "gene_B": 0.2,
    "gene_C": 1.4
  }
}
Datasets

Use Replogle et al. genome-scale Perturb-seq, which targeted all expressed genes with CRISPRi across more than 2.5 million human cells. 

Processed Replogle datasets are publicly available and include K562 genome-scale, K562 essential-scale, and RPE1 essential-scale Perturb-seq data in AnnData format. 

Use LINCS L1000 for broader genetic perturbation expression signatures; LINCS L1000 includes high-throughput expression profiles after chemical and genetic perturbations. 

Reward

Pearson/Spearman over held-out genes.

Top-k upregulated/downregulated recovery.

Directional accuracy.

Cell-state classification accuracy.

Dragon link: A future genetic designer needs to predict downstream consequences of changing regulators.

14. DragonClinicalVariantProxy: classify variant consequences, not clinical advice
Dragon capability: Can the model reason from genotype to phenotype labels?

Model input

{
  "reference_sequence_context": "ACGT...",
  "variant": {"pos": 402, "ref": "C", "alt": "T"},
  "gene_context": "protein_coding",
  "task": "predict retrospective database label"
}
Action/output

{
  "label": "loss_of_function_likely",
  "confidence": 0.72
}
Datasets

Use ClinVar only as a retrospective label source, not as medical advice. ClinVar is a freely accessible public archive of human variations classified for diseases and drug responses with supporting evidence. 

Use high-confidence, non-conflicting labels only.

Reward

AUROC for benign/pathogenic-style labels.

Calibration.

Conflicting-label exclusion rate.

Dragon link: This is less dragon-specific, but useful for measuring genotype-to-phenotype reasoning.

Best hackathon subset
For a hackathon, I’d build five environments, not fourteen:

Environment	Dataset	Why it fits the dragon genetics story
DragonGeneParse	GENCODE	Basic gene structure: exons, introns, splice sites.
DragonTFBind	ENCODE / ReMap / JASPAR	Regulatory binding: where TFs control genes.
DragonEnhancerTissue	VISTA / FANTOM5 / ENCODE cCREs	Tissue-specific developmental switches.
DragonVariantEffect	ProteinGym / MaveDB	Mutation-to-function reasoning.
DragonGeneKnockoutPhenotype	IMPC / MGI / ZFIN / FlyBase	Gene-to-trait reasoning for limbs, skin, pigmentation, skeleton, viability.
That stack gives you a credible backward chain:

dragon-like phenotype
→ organismal traits
→ gene perturbation phenotypes
→ tissue-specific enhancers
→ TF binding sites
→ gene structure and sequence function
What to exclude
I would explicitly exclude these unless you find a real labeled dataset:

Proposed task	Include?	Why
“Predict genes needed for fire-breathing”	No	No public biological ground truth.
“Design a full dragon genome”	No	Not well-scored, unsafe, no labels.
“Predict whether this mutation gives wings in vertebrates”	Usually no	No dense public dataset for that exact phenotype.
“Predict tissue enhancer activity in mouse embryo”	Yes	VISTA has in vivo enhancer reporter labels.
“Predict Drosophila wing phenotype after mutation”	Yes	FlyBase phenotype annotations exist.
“Predict mouse limb/skull/skin phenotype after knockout”	Yes	IMPC/MGI phenotype annotations exist.
A precise RL environment pattern
Each environment can be a closed-book Gym-style task:

obs = {
    "sequence": "...",
    "context": {...},
    "candidate_labels": [...]
}

action = {
    "predictions": [...]
}

reward = score(action, hidden_labels)
The agent never queries the dataset. The dataset is only the hidden oracle used by the environment.

The most “RSI” version is not that the model gets access to biology databases. It is that the agent improves its internal heuristics over many closed episodes:

episode 1: predict TF binding on held-out promoter sequences
episode 2: receive reward only
episode 3: improve strategy
...
held-out final: new sequences, same schema, hidden labels
That keeps it aligned with the theme: models learning to improve their genetic reasoning in constrained, measurable environments.





Sources

Do they have any of these datasets for reptiles?

Worked for 39s
Yes, but only for a subset. For non-avian reptiles, the usable public datasets are much thinner than human/mouse/fly/zebrafish. I’d treat reptiles as good for gene parsing, transcriptome/expression, comparative regulatory elements, and some limb-regulatory chromatin tasks, but weak for TF-specific binding, enhancer reporter assays, knockout phenotype, and dense genotype-to-phenotype.

Also: if you count birds as reptiles phylogenetically, the dataset situation improves a lot. If you mean lizards/snakes/turtles/crocodilians, it is much spottier.

Reptile datasets that can support real benchmark tasks
Benchmark task	Reptile dataset exists?	Specific usable datasets	Verdict
Gene/exon/intron annotation	Yes	Green anole genome annotation in Ensembl; ASU/Dryad Anolis reannotation with GFF3/GTF/exon/protein FASTA. Ensembl’s Anolis annotation uses protein alignments, mapped annotation, and RNA-seq where available; the ASU/Dryad reannotation provides downloadable cDNA, exon, GFF3, GTF, and protein files. 
 
Good task
Reptile transcriptome annotation	Yes	Reptilian Transcriptomes Database 2.0, covering major reptile lineages including Squamata, Rhynchocephalia, Crocodilia, and Testudines. 
Good task
Tissue/developmental expression prediction	Somewhat	Anolis reannotation from 14 adult and embryonic deep transcriptomes; another Anolis dataset collected 30 adult and 48 embryonic RNA-seq samples across organs/development. 
 
Usable, but smaller
Regulatory-region prediction / chromatin accessibility	Somewhat	Tegu lizard embryonic limb ATAC-seq; the study identified 5,635 limb-specific ATAC-seq peaks, plus brain/liver-specific peaks. 
Good for limb-regulatory proxy
Comparative noncoding element prediction	Yes	Tegu genome paper provides conserved non-exonic elements and a reptile-focused multiple-genome alignment across squamates and other amniotes. 
Good task
Reptile genome assembly / annotation quality	Yes	VGP/GenomeArk provide high-quality reference genome resources; tegu, green anole, snakes, turtles, alligator, etc. have assemblies, but annotation quality varies. 
 
Good for gene/repeat/comparative tasks
TF-specific binding prediction	Barely / no broad atlas	I found reptile chromatin accessibility and histone-mark examples, but not an ENCODE-scale reptile TF ChIP-seq atlas. One Anolis study generated H4K16ac ChIP-seq for brain/liver, but that is a histone mark, not broad TF binding. 
Probably not a core reptile task
Enhancer reporter activity by tissue	Very limited	There are reptile-related enhancer studies, but nothing like VISTA mouse-scale in vivo reporter labels for reptiles.	Probably exclude
Gene knockout → phenotype	Very limited	No IMPC/ZFIN/FlyBase equivalent for reptiles.	Exclude for reptiles
Dense genotype-to-phenotype / DMS	Mostly no	ProteinGym/MaveDB are not reptile-focused; reptile trait genetics exist in scattered papers, but not as a broad benchmark substrate.	Exclude or use cross-species proteins
Best reptile-specific environments
1. ReptileGeneParse
Task: Given a green anole genomic sequence window, predict exon/intron/CDS intervals.

Dataset:
Use ASU_Acar_v2.1 from Dryad or Ensembl Anolis annotations. The Dryad package has GFF3, GTF, exon FASTA, cDNA FASTA, and protein FASTA files. 

Why it works: precise labels, closed-book, machine-scorable.

Reward: splice-junction F1, exon-boundary F1, CDS-frame correctness.

2. ReptileTranscriptomeAnnotate
Task: Given an assembled reptile transcript or predicted protein, classify likely ortholog/function/domain/family.

Dataset:
Use Reptilian Transcriptomes Database 2.0, which annotates transcriptomes/genomes across snakes, lizards, crocodilians, tuatara, and turtles. 

Reward: top-k ortholog/function accuracy, protein-family accuracy, domain F1.

This is less “dragon body plan” and more “can the model understand reptile genes.”

3. AnolisExpressionTissue
Task: Given an Anolis gene sequence and a tissue/developmental context, predict whether the gene is expressed or rank expression level.

Dataset:
The Anolis reannotation gives an expression atlas from adult and embryonic tissues; the paper reports 59,373 transcripts and 22,962 predicted protein-coding genes. 

Reward: AUROC for expressed/not expressed, Spearman correlation for expression level.

This is usable, but weaker than GTEx-style human expression because reptile sample breadth is smaller.

4. TeguLimbRegulatoryElement
Task: Given a tegu genomic sequence window, classify whether it is a limb-specific open chromatin region.

Dataset:
The limb-regulatory evolution study generated tegu lizard embryonic ATAC-seq and identified 5,635 limb-specific ATAC-seq peaks, plus brain/liver-specific peaks. 

Output schema:

{
  "sequence_id": "seq_001",
  "limb_regulatory_probability": 0.83
}
Reward: AUROC/AUPRC over limb-specific ATAC peak vs matched negative windows.

This is probably the most “dragon-relevant” non-avian reptile dataset: it touches limb development and regulatory DNA.

5. SnakeLimbLossCNE
Task: Given conserved noncoding elements, predict whether they are snake-diverged and/or overlap limb regulatory elements.

Dataset:
The same study found that snake-diverged conserved noncoding elements overlap limb regulatory elements from tegu, green anole, and mouse, including limb-specific ATAC-seq and other limb datasets. 

Reward: binary classification accuracy/AUROC for snake-diverged limb-associated CNEs.

This is a nice “dragon genetics” proxy because it asks about regulatory changes tied to limb evolution.

6. ReptileConservedElement
Task: Given reptile genomic windows, predict whether they are conserved non-exonic elements, squamate-specific conserved elements, or neutral sequence.

Dataset:
The tegu genome paper reports a reptile-focused multiple-genome alignment, 324,770 conserved non-exonic elements, and 47,931 squamate-specific CNEs. 

Reward: AUROC/AUPRC for CNE classification, calibration, sequence-context generalization.

This is clean, closed-book, and scalable.

What I would not use for reptiles
I would not build reptile-specific versions of these unless you are okay with very small/scattered datasets:

Task	Why not
TF binding interval prediction for named TFs	No broad reptile TF ChIP-seq atlas comparable to ENCODE/ReMap. Use ATAC/CNE tasks instead.
In vivo enhancer tissue activity	No VISTA-scale reptile reporter dataset.
Gene knockout phenotype prediction	No IMPC/MGI/ZFIN/FlyBase equivalent for reptiles.
Dense genotype-to-phenotype variant effect	No broad reptile MAVE/DMS equivalent.
Full dragon-trait genotype prediction	No public ground truth.
Hackathon-friendly reptile suite
I’d make a reptile-specific mini-benchmark with four environments:

ReptileGeneParse
→ predict exons/introns from Anolis genomic sequence

ReptileExpression
→ predict tissue/developmental expression from Anolis gene sequence

TeguLimbRegulatory
→ classify limb-specific ATAC-seq regulatory windows

SnakeLimbLossCNE
→ identify conserved noncoding elements associated with limb loss/divergence
That gives you a concrete genetics-only “dragon” story:

A dragon-like body plan would require reading reptile genes, predicting reptile developmental expression, identifying limb regulatory elements, and understanding regulatory evolution of appendages.

The strongest reptile-specific task is probably tegu/anole/snake limb regulatory DNA, not phenotype prediction.





Sources


