# DragonBench HUD Harness

This repo exposes the 100-card scoreable eval as a HUD v6 taskset.

HUD references used:

- HUD hackathon quickstart: `pip install hud-python`, `hud set HUD_API_KEY=...`, `hud eval tasks.py claude`
- HUD v6 tasks: a task template yields a prompt, receives the answer, then yields a `0.0-1.0` reward
- HUD v6 graders: rewards can be plain Python floats, with custom scoring logic where needed

## Setup

```bash
pip install hud-python
hud set HUD_API_KEY=...
```

For Modal-backed full runs, copy the HUD key into Modal:

```bash
modal secret create dragonbench-hud-eval --from-dotenv "$HOME/.hud/.env" --force
```

## Preferred Run Path

For full sweeps, run the eval driver on Modal CPU and route model calls through
HUD Gateway:

```bash
modal run --detach runners/modal_hud_eval.py \
  --models claude-opus-4-8,gemini-3.1-pro-preview,gpt-5.5,gpt-5.4,gpt-5.4-mini,gpt-5,gpt-4o \
  --all \
  --max-concurrent 10 \
  --max-steps 2 \
  --max-output-tokens 32768
```

This runs `hud eval tasks.py <model> --gateway ...` inside Modal. The local
laptop can disconnect after submission; the Modal workers continue running the
eval driver, local task environment, and deterministic grading. HUD still records
jobs and traces for the resulting `tasks.py` runs.

Use `--wait` for small smoke tests:

```bash
modal run runners/modal_hud_eval.py \
  --models gpt-5.4-mini \
  --task-ids 60 \
  --max-concurrent 1 \
  --max-steps 2 \
  --max-output-tokens 8192 \
  --wait
```

Recommended defaults:

- `--max-steps 2`: one assistant tool-call step plus final evaluation.
- `--max-concurrent 10`: enough throughput without overloading HUD Gateway.
- `--max-output-tokens 32768`: needed for protein-folding PDB/mmCIF outputs.
- Do not use `--auto-respond`; each task expects one direct tool submission.

## Local Run

```bash
hud eval tasks.py claude --gateway --max-concurrent 5 --max-steps 2 --config max_tokens=32768
```

Replace `claude` with any model string supported by the HUD gateway.

## HUD Platform Remote Runs

The deployed taskset can also be run with `hud eval <taskset> <model> --remote`,
but this is no longer the preferred full-eval path. In larger sweeps, hosted
remote rollouts have shown long provider/platform queue times, detached-session
rollout errors, and provider capacity failures. Use remote runs for deployment
smoke tests; use `runners/modal_hud_eval.py` for full benchmark sweeps.

Each task family has a dedicated prompt with task-specific input and output
instructions. Benchmark internals and scoring details are omitted. Models
return exactly one JSON object matching the requested schema, without XML tags,
Markdown fences, or surrounding prose.

## Current Eval Status

The file `data/eval/dragonbench_eval_v0.scoreable.jsonl` has 100 scoreable cards:

- 20 `AnoleGeneParse`
- 20 `AnolePromoterExpression`
- 20 `KomodoProteinFold`
- 20 `DragonTFBind`
- 20 `RNAFold`

All cards have `hidden_answer.status: verified` and produce real rewards.

## Local Scoring Smoke Test

```bash
python3 scripts/make_smoke_answers.py
python3 scripts/score_answers.py --answers data/generated/smoke_answers.jsonl
```

The smoke file answers every task from the hidden answer and should score near `1.0`.

## Score Logs

Scoring appends JSONL events to `logs/score_events.jsonl` by default. Each event includes:

- task id
- task family
- lineage
- reward
- primary scorer
- secondary scorers
- subscores
- scorer info
- scoring explanation with the exact reward formula
- format contract
- answer preview, truncated to 500 characters, for HUD task runs

Hidden answers are not logged by the HUD harness. Local `scripts/score_answers.py` does not log answer previews by default, because local answer files may contain oracle/debug answers. Use `--log-answer-preview` only for non-secret model answers.

Controls:

```bash
DRAGONBENCH_SCORE_LOG=0 hud eval tasks.py claude --max-steps 1 --task-ids 20 -y
DRAGONBENCH_SCORE_LOG_PATH=logs/my_run.jsonl hud eval tasks.py claude --max-steps 1 --task-ids 20 -y
python3 scripts/score_answers.py --answers data/generated/smoke_answers.jsonl --no-log
python3 scripts/score_answers.py --answers model_answers.jsonl --log-answer-preview
```

## Scoring Design

The scorer lives in `dragonbench/scoring.py`.

Task scoring:

- `AnoleGeneParse`: Levenshtein similarity normalized by ground-truth intron length; interval F1, boundary score, and intron count accuracy are diagnostics
- `AnolePromoterExpression`: chance-clipped Spearman rank correlation; incomplete or duplicate rankings score zero
- `KomodoProteinFold`: C-alpha lDDT over reference residue pairs within 15 Å. Missing predicted residues contribute zero to affected contacts; coverage, validity, and backbone completeness are diagnostics.
- `DragonTFBind`: chance-clipped Spearman rank correlation over required binding probabilities; every candidate DNA sequence ID must be present exactly once
- `RNAFold`: base-pair F1 over a valid, length-matched dot-bracket structure

The scoring functions are deterministic, JSON-only, and avoid LLM judging.

## Protein 3D Visualization

Per `docs/data-spec.md`, `KomodoProteinFold` asks for a complete all-atom monomer structure:

```json
{
  "pdb": "ATOM      1  N   ..."
}
```

or:

```json
{
  "mmcif": "data_model\n..."
}
```

Build a 3D report:

```bash
python3 scripts/build_protein_3d_report.py --answers data/generated/smoke_answers.jsonl --out reports/protein_folding_3d.html
```

The single-model report renders the ground-truth structure in green, the submitted all-atom PDB/mmCIF model in orange, and an overlay. Model answers must use the canonical PDB/mmCIF JSON shape.

Incomplete-backbone PDB/mmCIF answers, such as mostly C-alpha-only structures, are rendered as explicit C-alpha traces so the submitted geometry stays visible in the single-answer viewer.

Build a two-model comparison report:

```bash
python3 scripts/build_protein_3d_report.py \
  --answers-a path/to/model_a_answers.jsonl \
  --answers-b path/to/model_b_answers.jsonl \
  --model-a-name ModelA \
  --model-b-name ModelB \
  --out reports/protein_folding_compare.html
```

The comparison report shows three 3Dmol panels: model A vs ground truth, model B vs ground truth, and model A vs model B on a ground-truth reference. PDB model structures are C-alpha-aligned to the target before overlay display when possible. For a local visual smoke test, create a deterministic perturbed second model:

```bash
python3 scripts/make_demo_model_b_answers.py
python3 scripts/build_protein_3d_report.py \
  --answers-a data/generated/smoke_answers.jsonl \
  --answers-b data/generated/demo_model_b_answers.jsonl \
  --model-a-name SmokeOracle \
  --model-b-name PerturbedDemo \
  --out reports/protein_folding_compare.html
```

The current protein targets are selected from UniProt `Varanus komodoensis`
entries with AlphaFold DB structures. The fixture and raw structures are stored in:

```text
data/source/komodo_alphafold/komodo_alphafold_structures.jsonl
data/source/komodo_alphafold/pdb/
```

Refresh the short, bounded protein set with:

```bash
python3 scripts/build_komodo_protein_fixture.py
python3 scripts/build_scoreable_eval.py
python3 scripts/make_smoke_answers.py
```

The visualization path and scoring path both consume the all-atom `docs/data-spec.md` output shape. The scorer extracts C-alpha coordinates from the submitted PDB/mmCIF structure for the current distance-matrix metric.

### HUD Visualization Links

HUD can show a link to the protein viewer through the grade payload `info.visualization_url` and `info.visualization.url`. The URL must be reachable from the browser where you open HUD. `127.0.0.1` works only for local viewing; use a public tunnel or deployment for the hosted HUD website.

For protein tasks, the HUD harness writes a per-answer single-answer report under `reports/hud/` and links to that file. That report uses the actual folded protein answer from the HUD trace and shows ground truth, submitted answer, and overlay. The older `reports/protein_folding_compare.html` report is only the static model-A-vs-model-B smoke/demo comparison report.

```bash
python3 -m http.server 8765
DRAGONBENCH_VIZ_BASE_URL=http://127.0.0.1:8765 hud eval tasks.py claude
```

For a hosted run, set `DRAGONBENCH_VIZ_BASE_URL` to the public base URL that serves this repo or the generated `reports/` and `vendor/` files:

```bash
DRAGONBENCH_VIZ_BASE_URL=https://your-public-dragonbench-viewer.example hud eval tasks.py claude
```

Protein task results include:

```json
{
  "info": {
    "visualization_mode": "single_answer",
    "visualization_source": "hud_model_answer",
    "visualization_url": "https://your-public-dragonbench-viewer.example/reports/hud/DBEVAL-V0-041-abc123def456.html?task_id=DBEVAL-V0-041",
    "visualization": {
      "kind": "protein_single_answer_structure",
      "viewer": "3dmol",
      "mode": "single_answer",
      "task_id": "DBEVAL-V0-041",
      "source": "hud_model_answer",
      "url": "https://your-public-dragonbench-viewer.example/reports/hud/DBEVAL-V0-041-abc123def456.html?task_id=DBEVAL-V0-041"
    }
  }
}
```

## HUD Environment Grade Payload

The environment yields a structured grade frame, not only a bare float:

```json
{
  "score": 0.6,
  "content": "DBEVAL-V0-096 DragonRNAFolding scored 0.600 (scored).",
  "status": "scored",
  "subscores": {"base_pair_f1": 0.75},
  "info": {"matched_base_pairs": 3},
  "scoring_explanation": "Reward = base_pair_f1.",
  "format_contract": "Return one JSON object matching the task's required answer schema."
}
```

This should make the HUD trace/result pane explain how the reward was computed for each run.

For protein tasks, the harness repeats the viewer URL in `content` and `info.visualization_url`. HUD may render `content` more visibly than nested `info` metadata.
