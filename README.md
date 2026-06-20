# DragonBench

DragonBench is a 100-question genetics benchmark for evaluating models on dataset-backed "dragon design" tasks. The current eval is intentionally small enough for full human review, but runnable end-to-end through HUD with deterministic scoring.

The benchmark has 5 task families with 20 questions each:

- `DragonGeneParseIntrons`: identify intron spans in gene sequences.
- `DragonAnolePromoterExpression`: rank Anolis tissues by expression from a 2 kb upstream promoter sequence.
- `DragonProteinFolding` / `KomodoProteinFold`: generate an all-atom monomer structure from a protein sequence.
- `DragonTFBind`: predict transcription-factor binding probabilities or intervals.
- `DragonRNAFolding`: predict RNA secondary structure.

See `PLAN.md` for the eval-building plan and `data-spec.md` for the current target data contract.

## Repository Layout

```text
dragonbench/
  prompts.py                       # HUD/model prompt rendering
  scoring.py                       # deterministic scorers
  logging.py                       # local/HUD score-event logs
eval/
  dragonbench_eval_v0.scoreable.jsonl
  smoke_answers.jsonl
  demo_model_b_answers.jsonl
scripts/
  build_scoreable_eval.py
  make_smoke_answers.py
  make_demo_model_b_answers.py
  score_answers.py
  build_protein_3d_report.py
reports/
  protein_folding_3d.html
  protein_folding_compare.html
vendor/
  3Dmol-min.js
tasks.py                           # HUD taskset entrypoint
HUD_HARNESS.md                     # detailed HUD notes
```

## Setup

Install Python dependencies:

```bash
pip install -r requirements.txt
pip install hud-python
```

If you use the installed conda HUD CLI on this machine, the binary is expected at:

```bash
/Users/ibrahim/anaconda3/bin/hud
```

Set the HUD API key before running hosted evals:

```bash
hud set HUD_API_KEY=...
```

## Dataset

The runnable eval is:

```text
eval/dragonbench_eval_v0.scoreable.jsonl
```

It contains 100 scoreable cards:

- 20 `DragonGeneParseIntrons`
- 20 `DragonAnolePromoterExpression`
- 20 `DragonProteinFolding`
- 20 `DragonTFBind`
- 20 `DragonRNAFolding`

Each scoreable card has a hidden answer with `status: verified`, so every task can be scored automatically. The hidden answers are not included in model prompts.

## Model Output Contract

HUD prompts require the model to end with a lowercase final answer block:

```xml
<answer>{"field": "value"}</answer>
```

Rules:

- The final answer must be the last thing in the response.
- The scorer parses the last lowercase `<answer>...</answer>` block.
- If multiple lowercase answer blocks appear, only the last one is scored.
- The JSON inside the block must be valid and match the task schema.
- Uppercase tags like `<Answer>` are invalid.
- Zero lowercase blocks or malformed JSON scores `0`.
- Raw JSON is still accepted by local scoring tools for convenience.

## Scoring

Scoring is deterministic and lives in:

```text
dragonbench/scoring.py
```

Current scoring functions:

- Gene parsing: spliced-sequence Levenshtein similarity when the input sequence is available, plus intron interval F1, boundary score, and count accuracy.
- Promoter expression: Spearman rank correlation, top-1 tissue accuracy, pairwise ranking accuracy, ranking completeness, and NDCG diagnostics.
- Protein folding: structure validity, backbone completeness, coordinate coverage, and C-alpha distance-matrix RMSD score. All-atom PDB/mmCIF is accepted, with C-alpha extraction used as the scoring bridge.
- TF binding: AUROC, AUPRC, ranking accuracy, and Brier score for probability tasks; interval F1 for interval tasks.
- RNA folding: base-pair F1, exact dot-bracket match, and length validity.

Score logs are written by default to:

```text
logs/score_events.jsonl
```

Controls:

```bash
DRAGONBENCH_SCORE_LOG=0 hud eval tasks.py claude
DRAGONBENCH_SCORE_LOG_PATH=logs/my_run.jsonl hud eval tasks.py claude
DRAGONBENCH_SCORE_STDOUT=1 hud eval tasks.py claude
```

## Local Smoke Test

Generate oracle-style smoke answers from hidden answers:

```bash
python3 scripts/make_smoke_answers.py
python3 scripts/score_answers.py --answers eval/smoke_answers.jsonl
```

The smoke answers should score near `1.0`.

Generate a deterministic perturbed second model for visualization demos:

```bash
python3 scripts/make_demo_model_b_answers.py
python3 scripts/score_answers.py --answers eval/demo_model_b_answers.jsonl
```

## HUD Eval

Run the full eval:

```bash
hud eval tasks.py claude
```

Run a subset:

```bash
hud eval tasks.py claude --task-ids 20 -y
```

The HUD task entrypoint is:

```text
tasks.py
```

For each task, the environment yields a structured grade payload:

```json
{
  "score": 0.6,
  "status": "scored",
  "subscores": {"base_pair_f1": 0.75},
  "info": {"matched_base_pairs": 3},
  "scoring_explanation": "Reward = ...",
  "format_contract": "Model output is parsed from the last lowercase <answer>...</answer> block..."
}
```

Protein tasks may also include visualization links in `info` when configured.

## Protein 3D Reports

The protein visualization uses vendored 3Dmol.js:

```text
vendor/3Dmol-min.js
```

Build a single-model report:

```bash
python3 scripts/build_protein_3d_report.py \
  --answers eval/smoke_answers.jsonl \
  --out reports/protein_folding_3d.html
```

Build a two-model comparison report:

```bash
python3 scripts/build_protein_3d_report.py \
  --answers-a eval/smoke_answers.jsonl \
  --answers-b eval/demo_model_b_answers.jsonl \
  --model-a-name SmokeOracle \
  --model-b-name PerturbedDemo \
  --out reports/protein_folding_compare.html
```

The comparison report has three panels:

- Model A vs ground truth.
- Model B vs ground truth.
- Model A vs Model B with the ground-truth reference.

The viewer supports:

- all-atom PDB answers via `{"pdb": "ATOM ..."}`;
- mmCIF answers via `{"mmcif": "data_model..."}`;
- coordinate-array fallback for older C-alpha answers;
- task deep links through `?task_id=DBEVAL-V0-041`;
- an offset overlay toggle so nearly identical structures are still readable.

Serve reports locally:

```bash
python3 -m http.server 8765
```

Open:

```text
http://127.0.0.1:8765/reports/protein_folding_compare.html
http://127.0.0.1:8765/reports/protein_folding_compare.html?task_id=DBEVAL-V0-041
```

## HUD Visualization Links

HUD can receive a protein viewer URL through the grade payload. This is opt-in so ordinary eval runs do not emit broken localhost links.

Set:

```bash
DRAGONBENCH_VIZ_BASE_URL=http://127.0.0.1:8765
```

Then run HUD:

```bash
DRAGONBENCH_VIZ_BASE_URL=http://127.0.0.1:8765 hud eval tasks.py claude
```

Protein task results include both a flat URL and a structured object:

```json
{
  "info": {
    "visualization_url": "http://127.0.0.1:8765/reports/protein_folding_compare.html?task_id=DBEVAL-V0-041",
    "visualization": {
      "kind": "protein_structure_comparison",
      "viewer": "3dmol",
      "task_id": "DBEVAL-V0-041",
      "url": "http://127.0.0.1:8765/reports/protein_folding_compare.html?task_id=DBEVAL-V0-041"
    }
  }
}
```

Important:

- `127.0.0.1` only works on the same machine where the report server is running.
- For the hosted HUD website or teammates, `DRAGONBENCH_VIZ_BASE_URL` must be a public URL.
- The public URL must serve both `reports/` and `vendor/`, because the HTML loads `/vendor/3Dmol-min.js`.
- The generated report deep-links to the task id using `?task_id=...`.

Optional override for the report path:

```bash
DRAGONBENCH_PROTEIN_VIZ_REPORT=reports/protein_folding_compare.html
```

Example hosted run:

```bash
DRAGONBENCH_VIZ_BASE_URL=https://your-public-dragonbench-viewer.example hud eval tasks.py claude
```

Good hosting options:

- a static site deployment for this repo;
- S3/R2/Netlify/Vercel serving `reports/` and `vendor/`;
- a temporary `ngrok` or `cloudflared` tunnel pointed at `python3 -m http.server 8765`.

HUD will not necessarily embed the 3Dmol viewer inline. The reliable integration is a clickable visualization URL in the result metadata.

## Regenerating Eval Artifacts

Build or refresh the scoreable eval:

```bash
python3 scripts/build_scoreable_eval.py
python3 scripts/make_smoke_answers.py
```

Refresh protein structure cache when needed:

```bash
python3 scripts/fetch_pdb_ca_structures.py
python3 scripts/build_scoreable_eval.py
python3 scripts/make_smoke_answers.py
```

Check data-spec conformance:

```bash
python3 scripts/check_data_spec_conformance.py
```

## Validation

Run tests:

```bash
pytest -q tests/test_scoring.py
```

Check generated Python:

```bash
python3 -m py_compile tasks.py scripts/build_protein_3d_report.py
```

Check generated report JavaScript:

```bash
node --check <(perl -0777 -ne 'print $1 if m#<script>\n(.*)\n  </script>#s' reports/protein_folding_compare.html)
```

## Current Caveats

- The eval is a scoreable bootstrap set intended for human review, not a final locked benchmark.
- Protein visualization supports all-atom structures, but scoring still uses a C-alpha extraction bridge until TM-score/lDDT-style scoring is integrated.
- HUD visualization links are URL-based metadata, not guaranteed inline artifacts on the HUD website.
- Local visualization URLs only work locally; use a public base URL for hosted HUD demos.
