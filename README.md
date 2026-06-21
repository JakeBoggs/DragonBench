# DragonBench

DragonBench is a 100-question genetics benchmark for evaluating models on dataset-backed "dragon design" tasks. The current eval is intentionally small enough for full human review, but runnable end-to-end through HUD with deterministic scoring.

The benchmark has 5 task families with 20 questions each:

- `AnoleGeneParse`: identify intron spans in gene sequences.
- `AnolePromoterExpression`: rank Anolis tissues by expression from a 2 kb upstream promoter sequence.
- `KomodoProteinFold`: generate an all-atom monomer structure from a protein sequence.
- `DragonTFBind`: predict transcription-factor binding probabilities.
- `RNAFold`: predict RNA secondary structure.

See `data-spec.md` for the current data contract.

## Repository Layout

```text
dragonbench/
  prompts.py                       # HUD/model prompt rendering
  scoring.py                       # deterministic scorers
  logging.py                       # local/HUD score-event logs
data/source/                       # source-backed benchmark fixtures
eval/
  dragonbench_eval_v0.scoreable.jsonl
schemas/
  eval_question.schema.json
scripts/
  build_promoter_expression_fixture.py
  build_komodo_protein_fixture.py
  build_scoreable_eval.py
  make_smoke_answers.py
  make_demo_model_b_answers.py
  score_answers.py
  build_protein_3d_report.py
tasks.py                           # HUD taskset entrypoint
Dockerfile.hud                     # containerized HUD environment
```

Smoke answers, demo answers, reports, logs, and the local 3Dmol.js asset are generated artifacts and are ignored by Git.

## Setup

Install Python dependencies:

```bash
pip install -r requirements.txt
pip install hud-python
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

- 20 `AnoleGeneParse`
- 20 `AnolePromoterExpression`
- 20 `KomodoProteinFold`
- 20 `DragonTFBind`
- 20 `RNAFold`

Each scoreable card has a hidden answer with `status: verified`, so every task can be scored automatically. The hidden answers are not included in model prompts.
Protein-folding cards use 80–100 aa sequences. Fixture generation keeps each complete reference PDB task-answer JSON below 60,000 characters, while HUD transports only the small `submit_answer` receipt.

## Model Output Contract

HUD prompts require the model to submit the task answer through the `submit_answer` tool, then end with a lowercase final answer block containing only the returned receipt:

```xml
<answer>{"answer_ref":"runs/hud_answers/DBEVAL-V0-001/abc123.json","sha256":"..."}</answer>
```

Rules:

- The `submit_answer` tool receives `question_id` and `answer`; `answer` must be the JSON object matching the task schema.
- The final answer must be the last thing in the response.
- The scorer parses the last lowercase `<answer>...</answer>` block as the `submit_answer` receipt.
- If multiple lowercase answer blocks appear, only the last one is scored.
- Direct task answers inside `<answer>` are invalid for HUD grading and score `0`.
- The receipt JSON inside the block must include `answer_ref` and `sha256`.
- Uppercase tags like `<Answer>` are invalid.
- Zero lowercase blocks or malformed JSON scores `0`.
- Raw task-answer JSON is still accepted by local scoring helpers for scripts and unit tests, but not by the HUD eval harness.

## Scoring

Scoring is deterministic and lives in:

```text
dragonbench/scoring.py
```

Current scoring functions:

- Gene parsing: `max(0, 1 - Levenshtein(predicted spliced, true spliced) / (original length - true spliced length))`. Intron interval F1, boundary score, and count accuracy are diagnostics.
- Promoter expression: chance-clipped Spearman rank correlation across nine tissues. Incomplete or duplicate rankings score zero; top-1 accuracy and NDCG are diagnostics.
- Protein folding: coordinate coverage multiplied by local C-alpha distance-matrix similarity, with all-atom PDB/mmCIF validity and backbone completeness folded into the local structure score. Low residue coverage caps the reward.
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
  "content": "DBEVAL-V0-096 DragonRNAFolding scored 0.600 (scored).",
  "status": "scored",
  "subscores": {"base_pair_f1": 0.75},
  "info": {
    "matched_base_pairs": 3,
    "answer_submission_mode": "artifact",
    "answer_ref": "/abs/path/runs/hud_answers/DBEVAL-V0-096/abc123.json"
  },
  "scoring_explanation": "Reward = ...",
  "format_contract": "HUD eval output must end with a final lowercase <answer>...</answer> block containing the submit_answer receipt JSON: answer_ref and sha256..."
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
- automatic C-alpha trace rendering for incomplete-backbone PDB/mmCIF answers, so sparse or CA-only outputs remain visible instead of disappearing in cartoon mode;
- task deep links through `?task_id=DBEVAL-V0-041`;
- an offset overlay toggle so nearly identical structures are still readable.

Serve reports locally:

```bash
python3 -m http.server 8765
```

Open the static demo reports:

```text
http://127.0.0.1:8765/reports/protein_folding_3d.html
http://127.0.0.1:8765/reports/protein_folding_compare.html
http://127.0.0.1:8765/reports/protein_folding_compare.html?task_id=DBEVAL-V0-041
```

## HUD Visualization Links

HUD can receive a protein viewer URL through the grade payload. This is opt-in so ordinary eval runs do not emit broken localhost links.

For protein tasks, the HUD harness writes a trace-specific single-answer report under:

```text
reports/hud/
```

That trace-specific report uses the actual model answer returned during that HUD run. It is a single-answer viewer: ground truth, the submitted model answer, and an overlay. It does not point at the static model-A-vs-model-B smoke/demo comparison report.

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
  "content": "DBEVAL-V0-041 KomodoProteinFold scored 0.750 (scored).\nProtein visualization: http://127.0.0.1:8765/reports/hud/DBEVAL-V0-041-abc123def456.html?task_id=DBEVAL-V0-041",
  "info": {
    "visualization_status": "local_only",
    "visualization_mode": "single_answer",
    "visualization_source": "hud_model_answer",
    "visualization_url": "http://127.0.0.1:8765/reports/hud/DBEVAL-V0-041-abc123def456.html?task_id=DBEVAL-V0-041",
    "visualization": {
      "kind": "protein_single_answer_structure",
      "viewer": "3dmol",
      "mode": "single_answer",
      "task_id": "DBEVAL-V0-041",
      "source": "hud_model_answer",
      "url": "http://127.0.0.1:8765/reports/hud/DBEVAL-V0-041-abc123def456.html?task_id=DBEVAL-V0-041"
    }
  }
}
```

Important:

- `127.0.0.1` only works on the same machine where the report server is running.
- HUD may show `content` more visibly than nested `info`, so the harness repeats the visualization URL in both places.
- `visualization_mode: "single_answer"` means the link is not the model-A-vs-model-B comparison demo.
- `visualization_source: "hud_model_answer"` means the report is using the actual folded protein from that HUD trace.
- For the hosted HUD website or teammates, `DRAGONBENCH_VIZ_BASE_URL` must be a public URL.
- The public URL must serve both `reports/` and `vendor/`, because the HTML loads `/vendor/3Dmol-min.js`.
- The generated report deep-links to the task id using `?task_id=...`.

Optional override for the report path:

```bash
DRAGONBENCH_PROTEIN_VIZ_REPORT=reports/protein_folding_3d.html
```

This override is only a fallback. Normal HUD protein runs generate and link to `reports/hud/<task-id>-<answer-hash>.html`.

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
python3 scripts/build_promoter_expression_fixture.py
python3 scripts/build_komodo_protein_fixture.py
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
