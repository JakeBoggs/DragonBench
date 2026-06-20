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

## Run

```bash
hud eval tasks.py claude
```

Replace `claude` with any model string supported by the HUD gateway.

Model answers should end with a lowercase final-answer block in this shape:

```xml
<answer>{"field": "value"}</answer>
```

The scorer accepts exact raw JSON for local tooling, but HUD prompts ask for the lowercase XML wrapper. For HUD answers, zero lowercase blocks, uppercase tags, or malformed JSON in the final block score `0`. If multiple lowercase `<answer>` blocks are present, only the last one is scored.

## Current Eval Status

The file `eval/dragonbench_eval_v0.scoreable.jsonl` has 100 scoreable cards:

- 20 `DragonGeneParseIntrons`
- 20 `DragonAnolePromoterExpression`
- 20 `DragonProteinFolding`
- 20 `DragonTFBind`
- 20 `DragonRNAFolding`

All cards have `hidden_answer.status: verified` and produce real rewards.

## Local Scoring Smoke Test

```bash
python3 scripts/make_smoke_answers.py
python3 scripts/score_answers.py --answers eval/smoke_answers.jsonl
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
DRAGONBENCH_SCORE_LOG=0 hud eval tasks.py claude --task-ids 20 -y
DRAGONBENCH_SCORE_LOG_PATH=logs/my_run.jsonl hud eval tasks.py claude --task-ids 20 -y
python3 scripts/score_answers.py --answers eval/smoke_answers.jsonl --no-log
python3 scripts/score_answers.py --answers model_answers.jsonl --log-answer-preview
```

## Scoring Design

The scorer lives in `dragonbench/scoring.py`.

Task scoring:

- `DragonGeneParseIntrons`: intron interval F1 at IoU >= 0.8, boundary score, intron count accuracy
- `DragonAnolePromoterExpression`: NDCG over tissue ranking, top-1 tissue accuracy, Spearman rank correlation
- `DragonProteinFolding` / `KomodoProteinFold`: all-atom PDB/mmCIF validity and structure similarity, with C-alpha extraction as a fallback visualization/scoring bridge while TM-score/lDDT integration lands
- `DragonTFBind`: interval F1 at IoU >= 0.5, center-distance score, confidence presence
- `DragonRNAFolding`: base-pair F1, exact dot-bracket match, length validity

The scoring functions are deterministic, JSON-only, and avoid LLM judging.

## Protein 3D Visualization

Per `data-spec.md`, `KomodoProteinFold` asks for a complete all-atom monomer structure:

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
python3 scripts/build_protein_3d_report.py --answers eval/smoke_answers.jsonl --out reports/protein_folding_3d.html
```

The single-model report renders the ground-truth structure in green, the submitted all-atom PDB/mmCIF model in orange, and an overlay. Coordinate-array answers are still supported as a fallback and render as C-alpha traces.

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
  --answers-a eval/smoke_answers.jsonl \
  --answers-b eval/demo_model_b_answers.jsonl \
  --model-a-name SmokeOracle \
  --model-b-name PerturbedDemo \
  --out reports/protein_folding_compare.html
```

The current bootstrap protein targets are source-extracted from RCSB PDB files into:

```text
data/protein_structures/ca_structures.jsonl
```

Refresh the local PDB cache with:

```bash
python3 scripts/fetch_pdb_ca_structures.py
python3 scripts/build_scoreable_eval.py
python3 scripts/make_smoke_answers.py
```

The visualization path is now ready for the all-atom `data-spec.md` output shape. The scoring path still has a C-alpha fallback until the separate TM-score/lDDT scorer work lands.

### HUD Visualization Links

HUD can show a link to the protein viewer through the grade payload `info.visualization_url` and `info.visualization.url`. The URL must be reachable from the browser where you open HUD. `127.0.0.1` works only for local viewing; use a public tunnel or deployment for the hosted HUD website.

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
    "visualization_url": "https://your-public-dragonbench-viewer.example/reports/protein_folding_compare.html?task_id=DBEVAL-V0-041",
    "visualization": {
      "kind": "protein_structure_comparison",
      "viewer": "3dmol",
      "task_id": "DBEVAL-V0-041",
      "url": "https://your-public-dragonbench-viewer.example/reports/protein_folding_compare.html?task_id=DBEVAL-V0-041"
    }
  }
}
```

## HUD Environment Grade Payload

The environment yields a structured grade frame, not only a bare float:

```json
{
  "score": 0.6,
  "status": "scored",
  "subscores": {"base_pair_f1": 0.75},
  "info": {"matched_base_pairs": 3},
  "scoring_explanation": "Reward = 0.80 * base_pair_f1 + ...",
  "format_contract": "Model output is parsed from the last lowercase <answer>...</answer> block..."
}
```

This should make the HUD trace/result pane explain how the reward was computed for each run.
