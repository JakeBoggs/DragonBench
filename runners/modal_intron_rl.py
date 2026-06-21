"""Modal Training Gym launcher for DragonBench intron-span RL.

Run from Python 3.12:

    modal run runners/modal_intron_rl.py --smoke --no-eval-base --no-serve-trained --n-train 2 --n-eval 2 --num-rollout 2 --rollout-batch-size 1 --n-samples-per-prompt 2

The smoke path uses Qwen3-1.7B on one A100 to avoid RDMA requirements.
"""

from __future__ import annotations

import modal

from dragonbench.rl.intron_dataset import DragonBenchIntronDataset
from dragonbench.rl.intron_reward import intron_eval_response_fn, intron_rm
from modal_training_gym import (
    DeploymentConfig,
    EvalConfig,
    Qwen3_1_7B,
    Qwen3_6_35B,
    TrainConfig,
    list_checkpoints,
)
from modal_training_gym.deploy_recipes.sglang_recipe import (
    Qwen3_1_7b_SglangRecipe,
    Qwen3_6_35b_SglangRecipe,
)
from modal_training_gym.train_recipes.slime_recipe import (
    Qwen3_1_7b_Recipe,
    Qwen3_6_35b_Recipe,
)


app = modal.App("dragonbench-intron-rl")


def _require_huggingface_secret() -> None:
    try:
        modal.Secret.from_name("huggingface-secret").hydrate()
    except modal.exception.NotFoundError as exc:
        raise RuntimeError(
            "Missing Modal Secret 'huggingface-secret'. Create one at "
            "https://modal.com/secrets with an HF_TOKEN entry."
        ) from exc


def _dragonbench_image_overlay(image: modal.Image) -> modal.Image:
    return (
        image.add_local_dir("dragonbench", "/root/dragonbench", copy=True)
        .add_local_file("pyproject.toml", "/root/pyproject.toml", copy=True)
        .env({"PYTHONPATH": "/root"})
    )


@app.local_entrypoint()
def main(
    n_train: int = 20,
    n_eval: int = 5,
    seed: int = 17,
    eval_base: bool = True,
    train: bool = True,
    serve_trained: bool = True,
    num_rollout: int = 8,
    rollout_batch_size: int = 2,
    n_samples_per_prompt: int = 2,
    save_interval: int = 2,
    rollout_max_response_len: int = 128,
    rollout_temperature: float = 1.0,
    smoke: bool = False,
) -> None:
    """Launch a DragonBench intron-span GRPO run."""
    _require_huggingface_secret()

    dataset = DragonBenchIntronDataset(n_train=n_train, n_eval=n_eval, seed=seed)
    if smoke:
        model = Qwen3_1_7B()
        deployment_recipe_cls = Qwen3_1_7b_SglangRecipe
        train_recipe_cls = Qwen3_1_7b_Recipe
        model_slug = "qwen17b"
    else:
        model = Qwen3_6_35B()
        deployment_recipe_cls = Qwen3_6_35b_SglangRecipe
        train_recipe_cls = Qwen3_6_35b_Recipe
        model_slug = "qwen35b"

    eval_config = EvalConfig(
        dataset=dataset,
        eval_response_fn=intron_eval_response_fn,
        generate_kwargs={
            "chat_template_kwargs": {"enable_thinking": False},
            "temperature": 0.2,
            "max_tokens": rollout_max_response_len,
        },
    )

    if eval_base:
        base_deployment = DeploymentConfig(
            model=model,
            recipe=deployment_recipe_cls(),
            app_name=f"dragonbench-{model_slug}-intron-base-serve",
            served_model_name=f"dragonbench-{model_slug}-intron-base",
        ).serve()
        print(f"Base model URL: {base_deployment.url}")
        base_eval = eval_config.evaluate(base_deployment, debug=True)
        print(f"Base intron mean reward: {base_eval.mean:.3f}")

    if not train:
        print("Skipping training because --no-train was set.")
        return

    recipe = train_recipe_cls(
        gpu_type="A100" if smoke else "H100",
        actor_num_gpus_per_node=1 if smoke else 8,
        custom_rm_function=intron_rm,
        num_rollout=num_rollout,
        rollout_batch_size=rollout_batch_size,
        n_samples_per_prompt=n_samples_per_prompt,
        rollout_max_response_len=rollout_max_response_len,
        rollout_temperature=rollout_temperature,
        global_batch_size=(
            max(2, rollout_batch_size * n_samples_per_prompt)
            if smoke
            else max(8, rollout_batch_size)
        ),
        max_tokens_per_gpu=4096 if smoke else 8192,
        save_interval=save_interval,
        eval_interval=1 if smoke else None,
        apply_chat_template_kwargs='{"enable_thinking": false}',
        image_overlay=_dragonbench_image_overlay,
    )

    training_run = TrainConfig(
        model=model,
        dataset=dataset,
        recipe=recipe,
    )
    print("Starting DragonBench intron GRPO...")
    train_result = training_run.train()
    print(f"Training run id: {train_result.training_run_id}")

    if not serve_trained:
        return

    checkpoint = list_checkpoints(train_result.training_run_id)[-1]
    trained_deployment = DeploymentConfig(
        model=model,
        recipe=deployment_recipe_cls(),
        checkpoint=checkpoint,
        app_name=f"dragonbench-{model_slug}-intron-serve",
        served_model_name=f"dragonbench-{model_slug}-intron",
    ).serve()
    print(f"Trained model URL: {trained_deployment.url}")
    trained_eval = eval_config.evaluate(trained_deployment, debug=True)
    print(f"Trained intron mean reward: {trained_eval.mean:.3f}")
