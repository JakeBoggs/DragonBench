# Fireworks RFT: AnoleGeneParse

This folder adapts the DragonBench intron task to Fireworks Eval Protocol RFT.
The model sees only the chat `messages`. The evaluator receives the hidden
`ground_truth` label from the dataset row and scores the last assistant message
with `dragonbench.scoring.score_gene_parse_introns`.

The required answer format is:

```text
<answer>{"introns":[{"start":123,"end":456}]}</answer>
```

The evaluator parses the last lowercase `<answer>...</answer>` block. Invalid
JSON, missing blocks, or the wrong top-level shape receive reward `0.0`.

## Build Non-Eval Training Data

```bash
python scripts/build_anole_intron_training_records.py \
  --out data/source/anole_refseq/gene_parse_training_records.jsonl \
  --limit 240

python scripts/build_intron_rl_dataset.py \
  --out-dir fireworks_rft/intron/data/rl_non_eval \
  --n-train 200 \
  --n-eval 40
```

`gene_parse_records.jsonl` is the 20-question eval source and must not be used
for post-training. `gene_parse_training_records.jsonl` is built from the local
RefSeq GFF/FASTA and excludes exact `AnoleGeneParse` eval sequences.

The RL rows include `messages`, `question_id`, and a hidden `label` with the
verified introns and source sequence. The label is not sent to the model by
`SingleTurnRolloutProcessor`; it is used only by the evaluator.

## Local Evaluator Smoke

Every Eval Protocol command needs `FIREWORKS_API_KEY` in the current shell:

```bash
source ~/.zshrc
python - <<'PY'
import json
from pathlib import Path
from eval_protocol.models import Message
from fireworks_rft.intron.test_intron_rft import (
    intron_dataset_adapter,
    test_dragonbench_intron_rft,
)

row = json.loads(Path("fireworks_rft/intron/data/rl_non_eval/train.jsonl").read_text().splitlines()[0])
eval_row = intron_dataset_adapter([row])[0]
oracle = {"introns": eval_row.ground_truth["answer"]["introns"]}
eval_row.messages.append(
    Message(role="assistant", content="<answer>" + json.dumps(oracle, separators=(",", ":")) + "</answer>")
)
print(test_dragonbench_intron_rft._origin_func(eval_row).evaluation_result.score)
PY
```

That oracle scorer smoke should print `1.0`.

You can also run an end-to-end Eval Protocol rollout smoke:

```bash
source ~/.zshrc
EP_MAX_ROWS=1 eval-protocol local-test \
  --entry fireworks_rft/intron/test_intron_rft.py::test_dragonbench_intron_rft \
  --ignore-docker \
  --yes
```

The default rollout smoke model is `accounts/fireworks/models/gpt-oss-120b`
because the Qwen RFT target models below are fine-tuning/on-demand models, not
serverless inference endpoints on this account. This produced a nonzero reward
after the RFT prompt was adjusted to avoid the degenerate empty-intron answer:

```text
<answer>{"introns":[{"start":100,"end":200}]}</answer>
reward = 0.07961783439490444
```

A low reward is acceptable for this smoke; it validates rollout, parsing, and scoring. Eval Protocol's
`local-test` wrapper currently enforces a small positive pass threshold, so a
valid zero-reward rollout can still exit nonzero.

## Launch RFT With W&B

Use `accounts/fireworks/models/gpt-oss-120b` for the intron RFT run. The
evaluator id below is the normalized id for
`test_intron_rft.py::test_dragonbench_intron_rft`. Do not pass the local JSONL
path to `--dataset`; this CLI uses `--dataset` for existing Fireworks dataset
ids. It infers `fireworks_rft/intron/data/rl_non_eval/train.jsonl` from the evaluator's
`input_dataset` and uploads the adapted `EvaluationRow` JSONL.

W&B observability requires `WANDB_API_KEY` and a W&B entity. The current default
entity is `ibrahim-ahmed-ia03`; override it with `WANDB_ENTITY` if needed. The
commands below default the project to `dragonbench-intron-rft`.

Run a dry-run first:

```bash
source ~/.zshrc
test -n "$WANDB_API_KEY"
wandb_entity=${WANDB_ENTITY:-ibrahim-ahmed-ia03}
wandb_project=${WANDB_PROJECT:-dragonbench-intron-rft}
eval-protocol create rft \
  --dry-run \
  --yes \
  --force \
  --skip-validation \
  --evaluator test-intron-rft-test-dragonbench-intron-rft \
  --base-model accounts/fireworks/models/gpt-oss-120b \
  --output-model accounts/ibrahim-85ise3pg4gdg/models/dragonbench-intron-gpt-oss-120b-rft-smoke \
  --epochs 1 \
  --learning-rate 1e-5 \
  --lora-rank 8 \
  --batch-size-samples 1 \
  --max-output-tokens 4096 \
  --temperature 0.8 \
  --extra-body '{"reasoning_effort":"low"}' \
  --max-concurrent-rollouts 1 \
  --max-concurrent-evaluations 1 \
  --wandb \
  --wandb-api-key "$WANDB_API_KEY" \
  --wandb-project "$wandb_project" \
  --wandb-entity "$wandb_entity"
```

Launch the live RFT job with a unique output model id:

```bash
source ~/.zshrc
test -n "$WANDB_API_KEY"
ts=$(date +%Y%m%d%H%M%S)
wandb_entity=${WANDB_ENTITY:-ibrahim-ahmed-ia03}
wandb_project=${WANDB_PROJECT:-dragonbench-intron-rft}
eval-protocol create rft \
  --yes \
  --force \
  --skip-validation \
  --evaluator test-intron-rft-test-dragonbench-intron-rft \
  --base-model accounts/fireworks/models/gpt-oss-120b \
  --output-model accounts/ibrahim-85ise3pg4gdg/models/dragonbench-intron-gpt-oss-120b-rft-$ts \
  --epochs 1 \
  --learning-rate 1e-5 \
  --lora-rank 8 \
  --batch-size-samples 1 \
  --max-output-tokens 4096 \
  --temperature 0.8 \
  --extra-body '{"reasoning_effort":"low"}' \
  --max-concurrent-rollouts 1 \
  --max-concurrent-evaluations 1 \
  --wandb \
  --wandb-api-key "$WANDB_API_KEY" \
  --wandb-project "$wandb_project" \
  --wandb-entity "$wandb_entity"
```

Fireworks requires `--output-model` to be a fully qualified resource name:
`accounts/<account-id>/models/<model-id>`. Passing only a bare model id is
rejected by the API.

Poll an RFT job:

```bash
source ~/.zshrc
python fireworks_rft/intron/status.py --kind rft --job-id <job-id>
```

Verified setup on 2026-06-20:

- Fireworks account resolved as `ibrahim-85ise3pg4gdg`.
- Evaluator uploaded and became `ACTIVE`:
  `accounts/ibrahim-85ise3pg4gdg/evaluators/test-intron-rft-test-dragonbench-intron-rft`.
- Non-eval source builder produced `240` unique records with zero exact overlap
  against the 20 intron eval sequences.
- Earlier RFT smoke job `ol1yhb6i` was cancelled after discovering it used the
  original 20-row eval source.
- Earlier SFT warmup job
  `accounts/ibrahim-85ise3pg4gdg/supervisedFineTuningJobs/dragonbench-intron-gpt-oss-120b-sft-20260620211100`
  was deleted/cancelled to keep the path simple: direct RFT only.
- W&B-enabled direct RFT job
  `accounts/ibrahim-85ise3pg4gdg/reinforcementFineTuningJobs/cy27nyuu`
  is running with W&B URL
  `https://wandb.ai/ibrahim-ahmed-ia03/dragonbench-intron-rft/runs/cy27nyuu`.

Do not train directly on the 100-question human-review eval set. This folder is
for the separate intron post-training set.
