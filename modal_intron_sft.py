"""Modal MS-SWIFT SFT launcher for DragonBench intron parsing.

Run from Python 3.12:

    modal run modal_intron_sft.py --smoke --n-train 5 --n-eval 2 --max-steps 5

The smoke path uses Qwen/Qwen3-0.6B on one A10G. This is intended as a
warm-start before GRPO: first teach the model to emit valid intron JSON, then
use the stricter intron reward in ``modal_intron_rl.py``.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

import modal


MODEL_ID = "Qwen/Qwen3.6-35B-A3B"
SMOKE_MODEL_ID = "Qwen/Qwen3-0.6B"
APP_NAME = "dragonbench-intron-sft"
VOLUME_ROOT = Path("/runs")
DATA_ROOT = VOLUME_ROOT / "data" / "dragonbench-intron-sft"
OUTPUT_ROOT = VOLUME_ROOT / "checkpoints" / "dragonbench-intron-sft"

image = (
    modal.Image.from_registry("nvidia/cuda:13.0.2-devel-ubuntu22.04", add_python="3.12")
    .apt_install("git", "build-essential", "ninja-build")
    .uv_pip_install(
        "torch",
        "transformers>=4.52.0",
        "accelerate",
        "deepspeed",
        "ms-swift",
        "peft",
        "liger-kernel",
        "qwen_vl_utils>=0.0.14",
        "decord",
        "torchvision",
    )
    .add_local_dir("dragonbench", "/root/dragonbench", copy=True)
    .add_local_dir("scripts", "/root/scripts", copy=True)
    .add_local_dir("data/source/anole_refseq", "/root/data/source/anole_refseq", copy=True)
    .env({"PYTHONPATH": "/root", "CUDA_HOME": "/usr/local/cuda"})
)

app = modal.App(APP_NAME, image=image)
volume = modal.Volume.from_name("dragonbench-intron-sft", create_if_missing=True)


def _run(cmd: list[str], env: dict[str, str] | None = None) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, env={**os.environ, **(env or {})})


def _latest_adapter_dir(output_root: Path) -> Path | None:
    adapters = sorted(
        output_root.rglob("adapter_config.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return adapters[0].parent if adapters else None


def _post_train_generation_check(
    *,
    model_id: str,
    output_root: Path,
    n_train: int,
    n_eval: int,
    seed: int,
) -> dict[str, Any]:
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    from dragonbench.rl.intron_dataset import DragonBenchIntronDataset
    from dragonbench.rl.intron_reward import score_intron_response

    adapter_dir = _latest_adapter_dir(output_root)
    if adapter_dir is None:
        return {"error": f"no adapter_config.json found below {output_root}"}

    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True,
    )
    model = PeftModel.from_pretrained(model, str(adapter_dir))
    model.eval()

    dataset = DragonBenchIntronDataset(n_train=n_train, n_eval=n_eval, seed=seed)

    def score_row(split: str, row: dict[str, Any]) -> dict[str, Any]:
        prompt = tokenizer.apply_chat_template(
            row["messages"],
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        with torch.no_grad():
            output_ids = model.generate(
                **inputs,
                max_new_tokens=256,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
            )
        new_tokens = output_ids[0, inputs["input_ids"].shape[-1] :]
        response = tokenizer.decode(new_tokens, skip_special_tokens=True)
        return {
            "split": split,
            "question_id": row["question_id"],
            "response": response,
            "reward": score_intron_response(response, row["label"]),
        }

    return {
        "adapter_dir": str(adapter_dir),
        "samples": [
            score_row("train", dataset.load("train")[0]),
            score_row("eval", dataset.load("eval")[0]),
        ],
    }


def _train_sft_impl(
    *,
    model_id: str,
    nproc_per_node: int,
    use_deepspeed: bool,
    use_liger_kernel: bool,
    n_train: int = 20,
    n_eval: int = 5,
    seed: int = 17,
    num_train_epochs: float = 1.0,
    learning_rate: str = "1e-4",
    lora_rank: int = 16,
    lora_alpha: int = 32,
    gradient_accumulation_steps: int = 8,
    max_steps: int = -1,
    max_length: int = 4096,
    save_steps: int = 20,
    eval_steps: int = 20,
    post_train_check: bool = True,
) -> dict[str, Any]:
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    output_root = OUTPUT_ROOT / model_id.replace("/", "__")
    output_root.mkdir(parents=True, exist_ok=True)
    _run(
        [
            "python",
            "/root/scripts/build_intron_sft_dataset.py",
            "--dataset",
            "/root/data/source/anole_refseq/gene_parse_records.jsonl",
            "--out-dir",
            str(DATA_ROOT),
            "--n-train",
            str(n_train),
            "--n-eval",
            str(n_eval),
            "--seed",
            str(seed),
        ]
    )

    env = {
        "CUDA_VISIBLE_DEVICES": ",".join(str(i) for i in range(nproc_per_node)),
        "NPROC_PER_NODE": str(nproc_per_node),
        "HF_TOKEN": os.environ["HF_TOKEN"],
    }
    swift_cmd = [
        "swift",
        "sft",
        "--model",
        model_id,
        "--use_hf",
        "true",
        "--do_train",
        "true",
        "--dataset",
        str(DATA_ROOT / "train.jsonl"),
        "--val_dataset",
        str(DATA_ROOT / "eval.jsonl"),
        "--torch_dtype",
        "bfloat16",
        "--num_train_epochs",
        str(num_train_epochs),
        "--per_device_train_batch_size",
        "1",
        "--per_device_eval_batch_size",
        "1",
        "--gradient_accumulation_steps",
        str(gradient_accumulation_steps),
        "--learning_rate",
        learning_rate,
        "--lora_rank",
        str(lora_rank),
        "--lora_alpha",
        str(lora_alpha),
        "--target_modules",
        "all-linear",
        "--eval_steps",
        str(eval_steps),
        "--save_steps",
        str(save_steps),
        "--save_total_limit",
        "2",
        "--logging_steps",
        "1",
        "--max_length",
        str(max_length),
        "--warmup_ratio",
        "0.05",
        "--dataloader_num_workers",
        "1",
        "--dataset_num_proc",
        "1",
        "--save_only_model",
        "true",
        "--output_dir",
        str(output_root),
        "--attn_impl",
        "sdpa",
    ]
    if use_deepspeed:
        swift_cmd.extend(["--deepspeed", "zero3"])
    if use_liger_kernel:
        swift_cmd.extend(["--use_liger_kernel", "true"])
    if max_steps > 0:
        swift_cmd.extend(["--max_steps", str(max_steps)])
    _run(swift_cmd, env=env)

    result: dict[str, Any] = {
        "model": model_id,
        "output_dir": str(output_root),
        "train_rows": n_train,
        "eval_rows": n_eval,
        "max_steps": max_steps,
    }
    if post_train_check:
        result["post_train_check"] = _post_train_generation_check(
            model_id=model_id,
            output_root=output_root,
            n_train=n_train,
            n_eval=n_eval,
            seed=seed,
        )
    volume.commit()
    print(json.dumps(result, indent=2), flush=True)
    return result


@app.function(
    gpu="H100:8",
    timeout=60 * 60 * 24,
    secrets=[modal.Secret.from_name("huggingface-secret")],
    volumes={str(VOLUME_ROOT): volume},
)
def train_sft(
    n_train: int = 20,
    n_eval: int = 5,
    seed: int = 17,
    num_train_epochs: float = 1.0,
    learning_rate: str = "1e-4",
    lora_rank: int = 16,
    lora_alpha: int = 32,
    gradient_accumulation_steps: int = 8,
    max_steps: int = -1,
    max_length: int = 4096,
    save_steps: int = 20,
    eval_steps: int = 20,
    post_train_check: bool = True,
) -> dict[str, Any]:
    return _train_sft_impl(
        model_id=MODEL_ID,
        nproc_per_node=8,
        use_deepspeed=True,
        use_liger_kernel=True,
        n_train=n_train,
        n_eval=n_eval,
        seed=seed,
        num_train_epochs=num_train_epochs,
        learning_rate=learning_rate,
        lora_rank=lora_rank,
        lora_alpha=lora_alpha,
        gradient_accumulation_steps=gradient_accumulation_steps,
        max_steps=max_steps,
        max_length=max_length,
        save_steps=save_steps,
        eval_steps=eval_steps,
        post_train_check=post_train_check,
    )


@app.function(
    gpu="A10G",
    timeout=60 * 60 * 4,
    secrets=[modal.Secret.from_name("huggingface-secret")],
    volumes={str(VOLUME_ROOT): volume},
)
def train_sft_smoke(
    n_train: int = 5,
    n_eval: int = 2,
    seed: int = 17,
    num_train_epochs: float = 1.0,
    max_steps: int = 5,
    post_train_check: bool = True,
) -> dict[str, Any]:
    return _train_sft_impl(
        model_id=SMOKE_MODEL_ID,
        nproc_per_node=1,
        use_deepspeed=False,
        use_liger_kernel=False,
        n_train=n_train,
        n_eval=n_eval,
        seed=seed,
        num_train_epochs=num_train_epochs,
        gradient_accumulation_steps=1,
        max_steps=max_steps,
        max_length=4096,
        save_steps=max(1, max_steps),
        eval_steps=max(1, max_steps),
        post_train_check=post_train_check,
    )


@app.local_entrypoint()
def main(
    n_train: int = 20,
    n_eval: int = 5,
    seed: int = 17,
    num_train_epochs: float = 1.0,
    gradient_accumulation_steps: int = 8,
    max_steps: int = -1,
    smoke: bool = False,
    post_train_check: bool = True,
) -> None:
    if smoke:
        result = train_sft_smoke.remote(
            n_train=n_train,
            n_eval=n_eval,
            seed=seed,
            num_train_epochs=num_train_epochs,
            max_steps=max_steps if max_steps > 0 else 5,
            post_train_check=post_train_check,
        )
    else:
        result = train_sft.remote(
            n_train=n_train,
            n_eval=n_eval,
            seed=seed,
            num_train_epochs=num_train_epochs,
            gradient_accumulation_steps=gradient_accumulation_steps,
            max_steps=max_steps,
            post_train_check=post_train_check,
        )
    print(json.dumps(result, indent=2))
