"""Poll Fireworks managed RFT job status for the intron scaffold."""

from __future__ import annotations

import argparse
import json
from typing import Any

from fireworks import Fireworks, NotFoundError


DEFAULT_ACCOUNT_ID = "ibrahim-85ise3pg4gdg"
DEFAULT_RFT_JOB_ID = "ol1yhb6i"


def _job_id(value: str) -> str:
    return value.rstrip("/").split("/")[-1]


def _dump_model(value: Any) -> Any:
    if value is None or value == "":
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump(by_alias=True)
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--account-id", default=DEFAULT_ACCOUNT_ID)
    parser.add_argument("--kind", choices=["sft", "rft"], default="rft")
    parser.add_argument(
        "--job-id",
        default=None,
        help="Short job id or full Fireworks job resource name.",
    )
    args = parser.parse_args()

    client = Fireworks(account_id=args.account_id)
    job_id = args.job_id or DEFAULT_RFT_JOB_ID
    if args.kind == "sft":
        try:
            job = client.supervised_fine_tuning_jobs.get(_job_id(job_id))
        except NotFoundError:
            print(json.dumps({"kind": "sft", "job_id": _job_id(job_id), "state": "NOT_FOUND"}, indent=2))
            return
        payload = {
            "name": job.name,
            "state": job.state,
            "status": _dump_model(job.status),
            "dataset": job.dataset,
            "evaluation_dataset": job.evaluation_dataset,
            "base_model": job.base_model,
            "warm_start_from": job.warm_start_from,
            "output_model": job.output_model,
            "epochs": job.epochs,
            "learning_rate": job.learning_rate,
            "lora_rank": job.lora_rank,
            "batch_size_samples": job.batch_size_samples,
            "progress": _dump_model(job.job_progress),
            "estimated_cost": _dump_model(job.estimated_cost),
            "metrics_available": bool(job.metrics_file_signed_url),
            "trainer_logs_available": bool(job.trainer_logs_signed_url),
        }
    else:
        try:
            job = client.reinforcement_fine_tuning_jobs.get(_job_id(job_id))
        except NotFoundError:
            print(json.dumps({"kind": "rft", "job_id": _job_id(job_id), "state": "NOT_FOUND"}, indent=2))
            return
        payload = {
            "name": job.name,
            "state": job.state,
            "status": _dump_model(job.status),
            "dataset": job.dataset,
            "evaluator": job.evaluator,
            "training_config": _dump_model(job.training_config),
            "inference_parameters": _dump_model(job.inference_parameters),
            "progress": _dump_model(job.job_progress),
            "output_metrics": job.output_metrics,
            "output_stats": job.output_stats,
            "trainer_logs_available": bool(job.trainer_logs_signed_url),
        }

    print(json.dumps(payload, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
