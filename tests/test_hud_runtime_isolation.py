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


def test_hud_runtime_isolation_grades_submitted_tool_answer():
    if importlib.util.find_spec("hud") is None:
        return

    install_hud_runtime_isolation()

    from hud.agents.types import ToolStep
    from hud.eval.run import Run
    from hud.types import MCPToolCall

    class CapturingGradeClient:
        def __init__(self):
            self.payload = None

        async def start_task(self, task_id: str, args: dict[str, Any]) -> dict[str, Any]:
            return {"prompt": "prompt"}

        async def grade(self, payload: dict[str, Any]) -> dict[str, Any]:
            self.payload = payload
            return {
                "score": 0.75,
                "content": "graded submitted answer",
                "info": {"graded": True},
            }

        async def cancel(self) -> None:
            return None

    async def drive() -> tuple[Run, CapturingGradeClient]:
        client = CapturingGradeClient()
        run = Run(client, "task", {})  # type: ignore[arg-type]
        async with run:
            run.trace.content = "ungraded assistant prose"
            run.trace.record(
                ToolStep(
                    call=MCPToolCall(
                        name="submit_answer",
                        arguments={"answer_json": '{"introns":[{"start":1,"end":4}]}'},
                    )
                )
            )
        return run, client

    run, client = asyncio.run(drive())

    assert run.reward == 0.75
    assert client.payload == {"answer": {"introns": [{"start": 1, "end": 4}]}}
    assert run.trace.content == "ungraded assistant prose"


def test_hud_runtime_isolation_rejects_missing_tool_submission():
    if importlib.util.find_spec("hud") is None:
        return

    install_hud_runtime_isolation()

    from hud.eval.run import Run

    class CapturingGradeClient:
        def __init__(self):
            self.payload = None

        async def start_task(self, task_id: str, args: dict[str, Any]) -> dict[str, Any]:
            return {"prompt": "prompt"}

        async def grade(self, payload: dict[str, Any]) -> dict[str, Any]:
            self.payload = payload
            return {
                "score": 1.0,
                "content": "should not grade",
                "info": {"graded": True},
            }

        async def cancel(self) -> None:
            return None

    async def drive() -> tuple[Run, CapturingGradeClient]:
        client = CapturingGradeClient()
        run = Run(client, "task", {})  # type: ignore[arg-type]
        async with run:
            run.trace.content = '{"introns":[]}'
        return run, client

    run, client = asyncio.run(drive())

    assert run.reward == 0.0
    assert run.trace.status == "error"
    assert run.trace.extra["skip_grade_reason"] == "agent finished without calling submit_answer"
    assert client.payload is None
