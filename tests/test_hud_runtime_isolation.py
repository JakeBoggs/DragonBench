import asyncio
import importlib.util
from typing import Any

from dragonbench.hud_runtime_isolation import install_hud_runtime_isolation


def test_hud_runtime_isolation_skips_grade_for_marked_agent_failure():
    if importlib.util.find_spec("hud") is None:
        return

    install_hud_runtime_isolation()

    from hud.eval.run import Run

    class ExplodingGradeClient:
        async def start_task(self, task_id: str, args: dict[str, Any]) -> dict[str, Any]:
            return {"prompt": "prompt"}

        async def grade(self, payload: dict[str, Any]) -> dict[str, Any]:
            raise AssertionError("tasks.grade should not be called")

        async def cancel(self) -> None:
            raise AssertionError("tasks.cancel should not be called")

    async def drive() -> Run:
        run = Run(ExplodingGradeClient(), "task", {})  # type: ignore[arg-type]
        async with run:
            run.trace.status = "error"
            run.trace.content = "partial agent output that is not valid JSON"
            run.trace.extra["skip_grade_reason"] = "agent loop failed before a final answer"
        return run

    run = asyncio.run(drive())

    assert run.trace.status == "error"
    assert run.reward == 0.0
    assert run.grade.is_error is True
    assert run.grade.info["phase"] == "agent loop"
