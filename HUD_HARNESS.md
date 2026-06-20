# DragonBench HUD Harness

This repo exposes the 100-card seed eval as a HUD v6 taskset.

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

## Current Eval Status

The file `eval/dragonbench_eval_v0.scoreable.jsonl` has 100 scoreable cards:

- 20 `DragonGeneParse`
- 20 `DragonTFBind`
- 20 `DragonEnhancerTissue`
- 20 `DragonVariantEffect`
- 20 `DragonPhenotypeGene`

All cards have `hidden_answer.status: verified` and produce real rewards.

## Local Scoring Smoke Test

```bash
python3 scripts/make_smoke_answers.py
python3 scripts/score_answers.py --answers eval/smoke_answers.jsonl
```

The smoke file answers every task from the hidden answer and should score near `1.0`.

## Scoring Design

The scorer lives in `dragonbench/scoring.py`.

Task scoring:

- `DragonGeneParse`: exon interval F1, splice donor F1, splice acceptor F1, optional CDS interval F1
- `DragonTFBind`: interval F1 at IoU >= 0.5, center-distance score, confidence presence
- `DragonEnhancerTissue`: multi-label probability score with average precision and Brier-style calibration
- `DragonVariantEffect`: Spearman rank correlation with Pearson tie-breaker
- `DragonPhenotypeGene`: multi-label probability score over candidate phenotype terms

The scoring functions are deterministic, JSON-only, and avoid LLM judging.
