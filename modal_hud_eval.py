"""Run DragonBench HUD evals on Modal CPU workers.

This avoids HUD's hosted rollout scheduler while still keeping the eval driver
off the laptop. Model calls route through HUD Gateway via HUD_API_KEY.

Examples:
    modal run modal_hud_eval.py --models gpt-5.4-mini --task-ids 60 --wait
    modal run modal_hud_eval.py --models gpt-5.4,gpt-4o --all --max-concurrent 10
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import modal


APP_NAME = "dragonbench-hud-eval-runner"
APP_DIR = Path("/app")


def _ignore_repo_noise(path: Path) -> bool:
    parts = set(path.parts)
    return bool(
        parts.intersection(
            {
                ".git",
                ".hud",
                ".pytest_cache",
                "__pycache__",
                "reports",
                "logs",
                "fireworks_rft",
            }
        )
    )


image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install_from_requirements("requirements.txt")
    .pip_install("openai", "anthropic", "google-genai", "aiohttp")
    .add_local_dir("dragonbench", "/app/dragonbench", copy=True, ignore=_ignore_repo_noise)
    .add_local_dir("eval", "/app/eval", copy=True, ignore=_ignore_repo_noise)
    .add_local_file("tasks.py", "/app/tasks.py", copy=True)
    .add_local_file("requirements.txt", "/app/requirements.txt", copy=True)
)

app = modal.App(APP_NAME, image=image)


def _token_config_key(model: str) -> str:
    if model.startswith("claude-") or model.startswith("anthropic."):
        return "max_tokens"
    return "max_output_tokens"


@app.function(
    cpu=4,
    memory=8192,
    timeout=60 * 60 * 8,
    secrets=[modal.Secret.from_name("dragonbench-hud-eval")],
)
def run_hud_eval(
    model: str,
    *,
    task_ids: str = "",
    all_tasks: bool = False,
    max_concurrent: int = 10,
    max_steps: int = 2,
    max_output_tokens: int = 32768,
    extra_config: list[str] | None = None,
) -> dict[str, object]:
    os.chdir(APP_DIR)
    env = os.environ.copy()
    env.setdefault("DRAGONBENCH_SCORE_LOG", "0")
    env.setdefault("PYTHONUNBUFFERED", "1")

    cmd = [
        "hud",
        "eval",
        "tasks.py",
        model,
        "--gateway",
        "--max-concurrent",
        str(max_concurrent),
        "--max-steps",
        str(max_steps),
        "--config",
        f"{_token_config_key(model)}={max_output_tokens}",
        "-y",
    ]
    if all_tasks:
        cmd.append("--all")
    elif task_ids:
        cmd.extend(["--task-ids", task_ids])
    else:
        cmd.extend(["--task-ids", "0"])

    for item in extra_config or []:
        cmd.extend(["--config", item])

    proc = subprocess.run(
        cmd,
        cwd=APP_DIR,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    output = proc.stdout or ""
    print(output, end="")
    return {
        "model": model,
        "returncode": proc.returncode,
        "command": cmd,
        "output_tail": output[-12000:],
    }


@app.local_entrypoint()
def main(
    models: str,
    task_ids: str = "",
    all: bool = False,  # noqa: A002 - CLI flag name.
    max_concurrent: int = 10,
    max_steps: int = 2,
    max_output_tokens: int = 32768,
    config: str = "",
    wait: bool = False,
) -> None:
    extra_config = [item for item in config.split(",") if item]
    selected_models = [model.strip() for model in models.split(",") if model.strip()]
    calls = []
    for model in selected_models:
        kwargs = {
            "task_ids": task_ids,
            "all_tasks": all,
            "max_concurrent": max_concurrent,
            "max_steps": max_steps,
            "max_output_tokens": max_output_tokens,
            "extra_config": extra_config,
        }
        if wait:
            result = run_hud_eval.remote(model, **kwargs)
            print(json.dumps(result, indent=2))
        else:
            call = run_hud_eval.spawn(model, **kwargs)
            calls.append({"model": model, "function_call_id": getattr(call, "object_id", None)})

    if calls:
        print(json.dumps({"submitted": calls}, indent=2))
