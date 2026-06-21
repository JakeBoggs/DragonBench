# DragonBench: Dragon Feasibility Projection v0.2

Date: 2026-06-20  
Purpose: A deck-ready but auditable forecast for when dragon-like engineered organisms could become technically feasible.

## Executive summary

This model forecasts **technical feasibility**, not legality, deployment, desirability, funding, or consumer availability.

| Target | Definition | Median | 80% interval |
|---|---|---:|---:|
| Prototype drake | Small edited vertebrate with dragon-like aesthetics; no powered flight required. | 2039 | 2037–2043 |
| Wyvern-style dragon | Viable dragon-like vertebrate with two hind limbs plus wings/forelimbs, likely pterosaur/bat/bird-inspired; no six-limb body plan and no literal fire. | 2057 | 2050–2068 |
| Classic fantasy dragon | Large, six-limbed, winged vertebrate-like animal with dragon morphology and fire-like biochemical display. | 2071 | 2061–2087 |

Main result: **the long pole is not DNA synthesis or AI model scale; it is predictive control over vertebrate development and morphogenesis.**

Short deck line:

> DNA writing gets us the ink. AI design gets us the spellbook. Morphogenesis is the dragon.

---

## Definitions

### Prototype drake

A small animal whose phenotype is visibly dragon-coded: reptile/bird-like face, scales or scale-like skin, horns/crests, coloration, maybe gliding membranes or ornamentation. It does **not** need powered flight, large size, six limbs, or fire.

### Wyvern-style dragon

A viable engineered vertebrate with dragon-like morphology using a more physically plausible body plan: two hind limbs plus wings/forelimbs. This is closer to pterosaurs, birds, or bats than to a six-limbed medieval dragon.

### Classic fantasy dragon

A large winged dragon with four legs plus separate wings, plus some fire-like biochemical display. This is substantially harder because it requires a deeper body-plan departure from known tetrapods.

---

## Source anchors

### 1. Genome-size target is plausible in base-pair scale

A dragon-like vertebrate genome is likely in the 1–2 Gb range if based on bird/reptile/bat-like architectures.

- Green anole draft genome: **1.78 Gb**.  
  Source: https://pmc.ncbi.nlm.nih.gov/articles/PMC3184186/
- Chicken genome: approximately **1.05 Gb**.  
  Source: https://www.ncbi.nlm.nih.gov/datasets/genome/GCA_000002315.1/ and https://www.genome.gov/11510730/2004-release-chicken-genome-assembled
- Bat genomes are generally around **2 Gb**.  
  Source: https://www.nature.com/articles/s41586-020-2486-3

### 2. Large flying vertebrates are physically plausible, but not arbitrary

Known giant pterosaurs imply that large flying reptile-like animals are not automatically impossible. One estimate gives upper values around **10–11 m wingspan** and **200–250 kg** for the largest pterosaurs.

Source: https://pmc.ncbi.nlm.nih.gov/articles/PMC2981443/

This supports a wyvern/pterosaur-like target more than a heavy six-limbed fantasy dragon.

### 3. Genome writing has advanced, but animal-scale genome construction is far beyond routine

Key milestones:

- JCVI-syn1.0: synthetic bacterial cell lineage, **~1.08 Mb**, 2010.
- JCVI-syn3.0: minimal synthetic cell, **531,560 bp**, 2016.
- Synthetic Yeast / Sc2.0: synthetic yeast genome project targeting **16 chromosomes** and about **12 Mb** total. Recent commentary says the project is nearing completion after synthesis/characterization of all 16 chromosomes.
- Commercial long DNA is still usually in kb-scale to low hundreds of kb depending on vendor and service tier. Examples include Ansa announcing **50 kb** clonal DNA and GenScript advertising complex genes/constructs up to **200 kb**.

Sources:
- https://www.jcvi.org/research/first-minimal-synthetic-bacterial-cell
- https://www.jcvi.org/media-center/first-minimal-synthetic-bacterial-cell-designed-and-constructed-scientists-venter
- https://pmc.ncbi.nlm.nih.gov/articles/PMC11046031/
- https://www.genscript.com/case-study-the-synthetic-yeast-genome-project-sc20.html
- https://ansabio.com/blog/what-if-you-could-build-without-limits-with-50-kb-dna-now-you-can/
- https://www.genscript.com/gene_synthesis.html

### 4. DNA synthesis cost has fallen, but cost is not the only bottleneck

Gene synthesis costs have fallen by orders of magnitude, with older commercial synthetic genes often quoted around $0.10–$0.30/bp and some later industry discussion around ~$0.01/bp for gene synthesis. Array oligos can be much cheaper per base, but sequence-perfect long constructs remain harder.

Sources:
- https://pmc.ncbi.nlm.nih.gov/articles/PMC5204324/
- https://www.genengnews.com/topics/genome-editing/the-long-and-winding-road-on-demand-dna-synthesis-in-high-demand/
- https://www.synthesis.cc/synthesis/2022/10/dna-synthesis-cost-data

### 5. Multiplex editing is real but still far from organism-design scale

A Nature 2023 xenotransplantation paper describes a pig donor engineered with **69 genomic edits**. This is a strong anchor for current high-end animal multiplex engineering.

Source: https://www.nature.com/articles/s41586-023-06594-4

### 6. Biology AI is scaling quickly

AI biology progress is accelerating on several axes:

- AlphaFold 3 predicts joint structures of complexes including proteins, nucleic acids, small molecules, ions, and modified residues.
- Evo 2 is described as a **40B parameter**, **1 Mb context** genomic foundation model trained on **over 9 trillion nucleotides**.
- Borzoi predicts tissue/cell-type-specific RNA-seq coverage from DNA sequence, with a 524 kb input sequence in the public repo.
- Epoch estimates biology AI model training compute has grown **2–4x/year** after a rapid 2019–2021 jump, and also notes that frontier language models still use much more compute than biology foundation models.

Sources:
- https://www.nature.com/articles/s41586-024-07487-w
- https://arcinstitute.org/tools/evo
- https://www.nature.com/articles/s41586-026-10176-5
- https://www.nature.com/articles/s41588-024-02053-6
- https://github.com/calico/borzoi
- https://epoch.ai/data-insights/biology-models-trends

### 7. Morphogenesis is the deep bottleneck

Recent work in synthetic multicellularity emphasizes that complex multicellular agents require both cellular diversity and predictable spatial organization. Synthetic organizer cells now enable spatial/biochemical control over aspects of development in stem-cell systems, but this is not yet equivalent to designing a whole vertebrate body plan. Hox genes and related regulatory programs are central to regional patterning and limb/body-plan organization.

Sources:
- https://www.nature.com/articles/s41540-024-00477-8
- https://www.cell.com/cell/fulltext/S0092-8674(24)01323-0
- https://pmc.ncbi.nlm.nih.gov/articles/PMC2909379/
- https://pubmed.ncbi.nlm.nih.gov/17644373/
- https://pmc.ncbi.nlm.nih.gov/articles/PMC9023767/

---

## Model

The model is a bottlenecked log-gap forecast.

For target `k` and capability `j`:

```text
T[k,j] = 2026 + G[k,j] / R[j]
```

where:

```text
G[k,j] = log10(required capability / current effective capability) + complexity penalty
R[j]   = annual progress rate in orders of magnitude per year
```

The target becomes feasible when all bottlenecks clear, so:

```text
T[k] = max_j T[k,j] + integration_penalty[k]
```

The integration penalty captures the lag between “each subsystem is individually feasible” and “a well-funded program can combine them into a working organism.”

---

## Parameter table

The full parameter table is saved separately as:

`dragon_projection_parameters.csv`

Mode values are:

| Target | Genome writing | Editing/repro | AI design | Morphogenesis | Validation |
|---|---:|---:|---:|---:|---:|
| Prototype drake | 1.0 OOM | 1.0 OOM | 1.8 OOM | 1.1 OOM | 1.2 OOM |
| Wyvern-style dragon | 2.1 OOM | 1.8 OOM | 2.7 OOM | 3.2 OOM | 2.1 OOM |
| Classic fantasy dragon | 2.3 OOM | 2.2 OOM | 3.1 OOM | 4.5 OOM | 2.7 OOM |

Progress-rate mode assumptions:

| Capability | Mode progress rate |
|---|---:|
| Genome writing / assembly | 0.14 OOM/year |
| Multiplex editing + reproductive platform | 0.16 OOM/year |
| AI biological design intelligence | 0.32 OOM/year |
| Morphogenesis / body-plan control | 0.12 OOM/year |
| Closed-loop validation | 0.14 OOM/year |

---

## How the core mode dates are calculated

### Wyvern-style dragon example

Genome writing:

```text
Current anchor: ~12 Mb synthetic yeast genome scale
Target anchor: ~1.5 Gb vertebrate-scale genome
Raw gap = log10(1.5e9 / 1.2e7) = 2.10 OOM
Rate = 0.14 OOM/year
Date = 2026 + 2.10 / 0.14 = 2041
```

Multiplex editing:

```text
Current anchor: 69 genomic edits in engineered pig
Target anchor: ~1000 coordinated edits/equivalent interventions plus reproductive complexity
Raw edit gap = log10(1000 / 69) = 1.16 OOM
Added complexity penalty ≈ 0.6 OOM
Total gap ≈ 1.8 OOM
Rate = 0.16 OOM/year
Date = 2026 + 1.8 / 0.16 = 2037
```

AI design:

```text
Source anchor: bio AI compute scaling 2–4x/year; frontier LMs still ~100x+ above biological foundation models in compute
Compute/design gap ≈ 2.0 OOM
Added integration/data/agentic-design gap ≈ 0.7 OOM
Total gap ≈ 2.7 OOM
Rate = 0.32 OOM/year
Date = 2026 + 2.7 / 0.32 = 2034
```

Morphogenesis:

```text
Current anchor: organoids, xenobots/anthrobots, synthetic organizer cells, partial developmental control
Target: reliable vertebrate body-plan control for a viable dragon-like organism
Judgment gap ≈ 3.2 OOM
Rate = 0.12 OOM/year
Date = 2026 + 3.2 / 0.12 = 2053
```

Closed-loop validation:

```text
Gap ≈ 2.1 OOM
Rate = 0.14 OOM/year
Date = 2026 + 2.1 / 0.14 = 2041
```

Final wyvern mode:

```text
max(2041, 2037, 2034, 2053, 2041) + integration penalty ≈ 2056
```

---

## Monte Carlo uncertainty method

For each target and bottleneck:

- Gap `G` is sampled from a triangular distribution.
- Progress rate `R` is sampled from a triangular distribution.
- Integration penalty is sampled from a triangular distribution.
- 200,000 runs are simulated.

The resulting 80% interval is the 10th–90th percentile range.

---

## Results

| Target | p10 | p25 | median | p75 | p90 |
|---|---:|---:|---:|---:|---:|
| Prototype drake | 2036.6 | 2037.8 | 2039.3 | 2041.1 | 2043.1 |
| Wyvern-style dragon | 2049.9 | 2052.6 | 2056.5 | 2061.6 | 2067.6 |
| Classic fantasy dragon | 2061.0 | 2065.0 | 2070.8 | 2078.1 | 2086.6 |

---

## Bottleneck probability

Probability that each capability is the final binding bottleneck in the simulation.

| Capability | Prototype drake | Wyvern-style dragon | Classic fantasy dragon |
|---|---:|---:|---:|
| Genome writing / assembly | 0.142 | 0.042 | 0.007 |
| Multiplex editing + reproductive platform | 0.049 | 0.002 | 0.000 |
| AI biological design intelligence | 0.010 | 0.000 | 0.000 |
| Morphogenesis / body-plan control | 0.465 | 0.914 | 0.969 |
| Closed-loop validation | 0.335 | 0.042 | 0.024 |

Interpretation: DragonBench is important because AI design is the fastest-moving bottleneck we can directly measure and improve. But for actual organism production, developmental control dominates the long-run timeline.

---

## Sensitivity

Wyvern-style dragon, mode assumptions:

- If morphogenesis progresses at **0.20 OOM/year**, morphogenesis clears around `2026 + 3.2 / 0.20 = 2042`, and the full wyvern date can move toward the mid/late 2040s after integration.
- If morphogenesis progresses at **0.06 OOM/year**, morphogenesis clears around `2026 + 3.2 / 0.06 = 2079`, pushing the full wyvern date into the 2080s.
- If AI biological design slows to **0.20 OOM/year**, the AI design bottleneck clears around `2026 + 2.7 / 0.20 = 2039.5`, still earlier than morphogenesis in the median model.
- If genome writing remains slow at **0.08 OOM/year**, the wyvern genome-writing bottleneck clears around `2026 + 2.1 / 0.08 = 2052`, becoming competitive with morphogenesis.

---

## Slide-ready conclusions

1. **DragonBench measures the bottleneck we can accelerate now: biological design intelligence.**
2. **The main long-term bottleneck is not writing DNA; it is making development obey the design.**
3. **A dragon-like prototype is plausible in the late 2030s.**
4. **A real wyvern-style dragon is a mid-century project under aggressive assumptions.**
5. **The classic six-limbed fantasy dragon is a second-half-of-century target unless developmental biology has a discontinuous breakthrough.**

---

## Reproducible simulation snippet

```python
import numpy as np

Y0 = 2026
N = 200_000
rng = np.random.default_rng(42)

rates = {
    "Genome writing / assembly": (0.08, 0.14, 0.22),
    "Multiplex editing + reproductive platform": (0.10, 0.16, 0.25),
    "AI biological design intelligence": (0.20, 0.32, 0.50),
    "Morphogenesis / body-plan control": (0.06, 0.12, 0.20),
    "Closed-loop validation": (0.08, 0.14, 0.22)
}

targets = {
    "Prototype drake": {
        "gaps_mode": {
            "Genome writing / assembly": 1.0,
            "Multiplex editing + reproductive platform": 1.0,
            "AI biological design intelligence": 1.8,
            "Morphogenesis / body-plan control": 1.1,
            "Closed-loop validation": 1.2
        },
        "gap_unc": (0.35, 0.55),
        "integration": (0.5, 2, 5)
    },
    "Wyvern-style dragon": {
        "gaps_mode": {
            "Genome writing / assembly": 2.1,
            "Multiplex editing + reproductive platform": 1.8,
            "AI biological design intelligence": 2.7,
            "Morphogenesis / body-plan control": 3.2,
            "Closed-loop validation": 2.1
        },
        "gap_unc": (0.45, 0.75),
        "integration": (1, 3, 8)
    },
    "Classic fantasy dragon": {
        "gaps_mode": {
            "Genome writing / assembly": 2.3,
            "Multiplex editing + reproductive platform": 2.2,
            "AI biological design intelligence": 3.1,
            "Morphogenesis / body-plan control": 4.5,
            "Closed-loop validation": 2.7
        },
        "gap_unc": (0.55, 1.0),
        "integration": (2, 6, 15)
    }
}

for target, cfg in targets.items():
    dates = []
    for cap, gap_mode in cfg["gaps_mode"].items():
        gap_low = max(0.05, gap_mode - cfg["gap_unc"][0])
        gap_high = gap_mode + cfg["gap_unc"][1]
        G = rng.triangular(gap_low, gap_mode, gap_high, N)
        R = rng.triangular(*rates[cap], N)
        dates.append(Y0 + G / R)

    base = np.max(np.vstack(dates), axis=0)
    integration = rng.triangular(*cfg["integration"], N)
    total = base + integration

    print(target, np.percentile(total, [10, 50, 90]))
```
