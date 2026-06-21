# Modal SFT/RL Stack

This is the DragonBench post-training path for the hackathon. The first training
target is `AnolePromoterExpression`: given a 2000 bp Anolis promoter, rank
tissues by predicted expression.

## Why This Target

- It is reptile-specific and close to the “genetically engineering a dragon”
  story: regulatory DNA controls where traits are expressed.
- Haiku scored poorly on it (`0.129` mean reward), leaving room for improvement.
- The output is small and verifiable: a complete tissue ranking.
- The same scorer can be used for eval and RL reward.

Protein folding remains useful for visualization, but it is a poor first RL
target for a text LLM because full 3D coordinates are hard to learn directly.

## Recommended Order

Use two stages:

1. **SFT with MS-SWIFT LoRA** so Qwen learns the exact output contract and
   promoter-expression priors.
2. **GRPO/RL with Modal Training Gym + Slime** so Qwen optimizes the deterministic
   DragonBench promoter reward.

Do not start with RL from the raw base model unless we intentionally want to
spend rollouts on format failures.

## SFT Architecture

`modal_promoter_sft.py` runs `swift sft` on Modal:

- production model: `Qwen/Qwen3.6-35B-A3B`
- smoke model: `Qwen/Qwen3-0.6B`
- trainer: MS-SWIFT
- train type: LoRA
- dataset format: `messages` JSONL with the supervised assistant answer
- checkpoint storage: Modal Volume `dragonbench-promoter-sft`

Qwen’s MS-SWIFT docs define the SFT custom dataset format as JSON/JSONL/CSV rows
with a `messages` array and document support for LoRA/QLoRA/full fine-tuning,
distributed training, and Megatron parallelism for Qwen MoE models.

## RL Architecture

`modal_promoter_rl.py` uses Modal Training Gym with Slime GRPO:

1. `DragonBenchPromoterDataset` materializes JSONL rows with:
   - `messages`: system + user prompt
   - `label`: hidden expression/ranking JSON
2. `promoter_expression_rm` parses the model response and calls the deterministic
   DragonBench promoter scorer.
3. Smoke runs use `Qwen3_1_7B` so the rollout/training loop can be debugged
   without waiting on the 35B MoE path.
4. Production runs use `Qwen3_6_35B` + `Qwen3_6_35b_Recipe` to train
   Qwen3.6-35B-A3B on 1 x 8 H100.
5. The matching SGLang recipe serves base and trained checkpoints for eval.

Modal’s RL guidance frames the hard parts as training, rollout serving, and
environment/reward execution. Training Gym handles the cluster topology, Ray/NCCL
bring-up, checkpoint volumes, serving, and eval plumbing.

## Prerequisites

Training Gym requires Python 3.12 locally because serialized Modal functions
must match the remote Python version.

```bash
python3.12 -m venv .venv-rl
source .venv-rl/bin/activate
pip install -U pip
pip install modal
pip install git+https://github.com/modal-projects/training-gym.git@main
```

You already logged into Modal. Also create a Modal secret named
`huggingface-secret` with `HF_TOKEN`:

```bash
modal secret create huggingface-secret HF_TOKEN=...
```

Optional dashboard:

```bash
training-gym setup
```

## Local Dataset Smoke

SFT rows include the supervised assistant answer:

```bash
python scripts/build_promoter_sft_dataset.py --out-dir runs/promoter_sft_dataset
```

RL rows include the prompt plus hidden label for the reward function:

```bash
python scripts/build_promoter_rl_dataset.py --out-dir runs/promoter_rl_dataset
```

The current eval only has 20 promoter examples. Use these for pipeline smoke; for
real training, point the builders at Jake’s improved/larger promoter dataset.

## Run SFT

Start with the small smoke model:

```bash
modal run modal_promoter_sft.py \
  --smoke \
  --n-train 1 \
  --n-eval 1 \
  --max-steps 1
```

This path uses `Qwen/Qwen3-0.6B` on one A10G. A verified smoke run trained and
evaluated one step, then wrote a checkpoint under:

```text
/runs/checkpoints/dragonbench-promoter-sft/Qwen__Qwen3-0.6B
```

Verified smoke command:

```bash
modal run modal_promoter_sft.py --smoke --n-train 1 --n-eval 1 --max-steps 1
```

For the 35B target, run:

```bash
modal run modal_promoter_sft.py \
  --n-train 20 \
  --n-eval 20 \
  --num-train-epochs 1
```

The launcher uses:

- `swift sft`
- `--model Qwen/Qwen3.6-35B-A3B`
- `--target_modules all-linear`
- `--deepspeed zero3`
- `--attn_impl sdpa`
- `--use_liger_kernel true`

For the current 20-row eval set, this is only a plumbing smoke.

## Run GRPO / RL

For a quick infrastructure check without training:

```bash
modal run modal_promoter_rl.py \
  --smoke \
  --no-eval-base \
  --no-train \
  --n-train 1 \
  --n-eval 1
```

For a tiny small-model training smoke:

```bash
modal run modal_promoter_rl.py \
  --smoke \
  --no-eval-base \
  --no-serve-trained \
  --n-train 1 \
  --n-eval 1 \
  --num-rollout 1 \
  --rollout-batch-size 1 \
  --n-samples-per-prompt 1 \
  --save-interval 1
```

The smoke RL path uses `Qwen/Qwen3-1.7B` on one A100. It intentionally avoids
the default full-node H100 recipe because this Modal workspace does not have
RDMA enabled. After SFT and eval audit, run a small 35B GRPO job:

Verified smoke run:

```text
training_run_id: sparse-inning-ba752d283784
model: Qwen/Qwen3-1.7B
gpu: A100:1
checkpoint_dir: /checkpoints/sparse-inning-ba752d283784
result: Ray job SUCCEEDED; TrainResult saved
dashboard: https://ia03--training-gym-dashboard-fastapi-app.modal.run/training/sparse-inning-ba752d283784
```

This smoke run used one rollout and one sample, so the observed reward was
`0.0` and the advantage was `0.0`. Treat it as infrastructure validation, not a
learning-quality signal.

```bash
modal run modal_promoter_rl.py \
  --n-train 20 \
  --n-eval 20 \
  --num-rollout 64 \
  --rollout-batch-size 8 \
  --n-samples-per-prompt 4
```

## Scaling Plan

After the eval is fixed:

1. Build a larger promoter-expression SFT/RL set from `data/source/anole_expression`.
2. Hold out the 100-card eval and any human-reviewed cards.
3. Run SFT first to teach the output schema and biological priors.
4. Run low-rollout GRPO against the deterministic promoter reward.
5. Compare base, SFT, and SFT+GRPO on the held-out HUD eval.
6. Only then add mixed tasks such as TF-binding and gene parsing.

## Cost Controls

Qwen3.6-35B-A3B is large. Keep early runs short:

- use `--smoke` for fast iteration;
- small SFT rows and one epoch;
- `--max-steps 1` for initial SFT checks;
- small `num_rollout`;
- low `rollout_batch_size`;
- `save_interval` around 10-20;
- `rollout_max_response_len=1024`.

Do not run long SFT or GRPO jobs until the promoter eval/data audit is complete.
