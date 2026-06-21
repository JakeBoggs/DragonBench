from __future__ import annotations

import json
from typing import Any


def _extract_submit_answer(trace: Any) -> Any | None:
    for step in reversed(getattr(trace, "steps", [])):
        call = getattr(step, "call", None)
        if call is None or getattr(call, "name", None) != "submit_answer":
            continue
        arguments = getattr(call, "arguments", None)
        if not isinstance(arguments, dict):
            continue
        answer_json = arguments.get("answer_json")
        if isinstance(answer_json, str) and answer_json.strip():
            try:
                parsed_answer = json.loads(answer_json)
            except json.JSONDecodeError:
                return answer_json
            return parsed_answer if isinstance(parsed_answer, dict) else answer_json
    return None


def _error_grade(reason: str):
    from hud.eval.run import Grade

    return Grade(
        reward=0.0,
        done=True,
        content=reason,
        info={"reason": reason, "phase": "agent loop"},
        is_error=True,
        raw={
            "score": 0.0,
            "done": True,
            "content": reason,
            "info": {"reason": reason, "phase": "agent loop"},
            "isError": True,
        },
    )


def install_hud_runtime_isolation() -> None:
    """Patch local HUD rollouts so agent-loop failures do not poison grading.

    HUD's local runner grades on ``Run.__aexit__``. If a provider stream fails
    inside the tool-agent loop, the SDK records a system error but can still try
    to grade whatever partial content the model emitted. For DragonBench's
    direct-JSON answer contract, that partial content is non-gradable and may
    be much larger than the grade transport should carry.
    """
    try:
        from hud.agents.tool_agent import ToolAgent
        from hud.eval.run import Run
    except ImportError:
        return

    if getattr(Run, "_dragonbench_grade_isolation_installed", False):
        return

    original_loop = ToolAgent._loop
    original_exit = Run.__aexit__

    async def isolated_loop(self: Any, run: Any, state: Any, **kwargs: Any) -> None:
        await original_loop(self, run, state, **kwargs)
        submitted_answer = _extract_submit_answer(run.trace)
        if submitted_answer is not None:
            run.trace.extra["submitted_answer"] = submitted_answer
        if run.trace.extra.get("skip_grade_reason"):
            return
        if run.trace.status != "error":
            return
        for step in reversed(run.trace.steps):
            if step.source == "system" and step.error:
                run.trace.extra["skip_grade_reason"] = (
                    f"agent loop failed before a final answer: {step.error}"
                )
                return

    async def isolated_exit(self: Any, exc_type: Any, exc: Any, tb: Any) -> bool:
        skip_grade_reason = self.trace.extra.get("skip_grade_reason")
        if skip_grade_reason:
            reason = str(skip_grade_reason)
            self.trace.status = "error"
            self.grade = _error_grade(reason)
            return False
        submitted_answer = self.trace.extra.get("submitted_answer")
        if submitted_answer is None:
            submitted_answer = _extract_submit_answer(self.trace)
        if submitted_answer is not None:
            original_content = self.trace.content
            self.trace.content = submitted_answer
            try:
                return await original_exit(self, exc_type, exc, tb)
            finally:
                self.trace.content = original_content
        reason = "agent finished without calling submit_answer"
        self.trace.status = "error"
        self.grade = _error_grade(reason)
        self.trace.extra["skip_grade_reason"] = reason
        return False

    ToolAgent._loop = isolated_loop
    Run.__aexit__ = isolated_exit
    Run._dragonbench_grade_isolation_installed = True
