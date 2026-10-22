"""The ReAct autonomous agent execution loop."""

from typing import Any, Callable, Optional
import time
import uuid

from local_coder.agent.agent_state import AgentSessionState, AgentStep, TaskStatus
from local_coder.agent.planner import TaskPlanner
from local_coder.agent.prompt_templates import CODING_AGENT_SYSTEM_PROMPT
from local_coder.neural.grammar_engine import parse_tool_call_json
from local_coder.neural.llama_runner import LlamaModelRunner
from local_coder.tools.base_tool import BaseAgentTool, ToolResult


class AgentExecutionLoop:
    """Orchestrates multi-step tool calls, observations, and reflection."""

    def __init__(
        self,
        runner: LlamaModelRunner,
        tools: list[BaseAgentTool],
        planner: Optional[TaskPlanner] = None,
        max_steps: int = 14,
    ) -> None:
        self.runner = runner
        self.tools: dict[str, BaseAgentTool] = {}
        for t in tools:
            self.tools[t.name] = t
            if t.name == "apply_search_replace_patch":
                self.tools["apply_patch"] = t
            elif t.name == "run_terminal_command":
                self.tools["run_terminal"] = t
            elif t.name == "list_directory":
                self.tools["list_dir"] = t
        self.planner = planner or TaskPlanner(runner)
        self.max_steps = max_steps

    def execute_task(
        self,
        user_goal: str,
        rules_context: str = "",
        on_step_callback: Optional[Callable[[AgentStep], None]] = None,
    ) -> AgentSessionState:
        """Runs the autonomous ReAct loop until the user goal is satisfied or max steps reached."""
        session = AgentSessionState(
            session_id=str(uuid.uuid4())[:8],
            user_goal=user_goal,
            status=TaskStatus.IN_PROGRESS,
        )

        # Step 1: Formulate checklist plan with repository awareness
        session.plan_checklist = self.planner.create_plan(user_goal, repo_summary=rules_context)

        # Step 2: Begin ReAct execution loop
        step_idx = 0
        duplicate_count = 0
        conversation_history: list[str] = [
            f"User Goal: {user_goal}",
            f"Checklist Plan:\n" + "\n".join(f"- {s}" for s in session.plan_checklist),
        ]
        if rules_context:
            conversation_history.append(f"Repository Rules:\n{rules_context}")

        while step_idx < self.max_steps:
            step_idx += 1
            step_start = time.perf_counter()

            # Format active prompt
            prompt = "\n\n".join(conversation_history) + "\n\nDecide next tool call or output final answer:"
            res = self.runner.generate(
                prompt=prompt,
                system_prompt=CODING_AGENT_SYSTEM_PROMPT,
                max_tokens=1024,
                temperature=0.2,
            )

            raw_output = res.content.strip()
            tool_name, tool_args = parse_tool_call_json(raw_output)

            # If no tool is called or model outputs a conclusion directly
            if not tool_name or tool_name not in self.tools:
                # Syntax Guard: Model attempted a tool call with malformed formatting
                if any(k in raw_output for k in ["write_file", "<write_file", '{"tool":', "'tool':"]):
                    conversation_history.append(
                        f"Step {step_idx} Format Notice: Your tool call format had a syntax issue. "
                        "To write a file, use format:\n<write_file path=\"path/to/file\">\ncode here\n</write_file>"
                    )
                    continue

                # Progress Guard: Model prematurely stopped before completing multi-file plan
                completed_count = len(session.completed_steps)
                if completed_count <= 1 and len(session.plan_checklist) >= 3 and step_idx < 4:
                    conversation_history.append(
                        f"Step {step_idx} Plan Notice: You have only created {completed_count} file(s). "
                        "Please continue by creating the next required file from the checklist."
                    )
                    continue

                session.status = TaskStatus.COMPLETED
                session.final_output = raw_output
                break

            # Prevent duplicate consecutive tool execution loops
            if session.completed_steps:
                prev_step = session.completed_steps[-1]
                if prev_step.action_tool == tool_name and prev_step.action_arguments == tool_args:
                    duplicate_count += 1
                    if duplicate_count >= 2:
                        session.status = TaskStatus.COMPLETED if prev_step.is_successful else TaskStatus.FAILED
                        session.final_output = f"Stopped after repeated action: {tool_name}."
                        break
                    else:
                        conversation_history.append(
                            f"System Notice: You already called {tool_name} with these arguments. "
                            "Do NOT repeat the same tool call. Proceed to the next step in your checklist plan."
                        )
                        continue
                else:
                    duplicate_count = 0

            # Execute the tool
            target_tool = self.tools[tool_name]
            try:
                tool_outcome: ToolResult = target_tool.execute(**tool_args)
            except Exception as exc:
                tool_outcome = ToolResult(is_success=False, output="", error_message=str(exc))

            raw_obs = tool_outcome.output if tool_outcome.is_success else f"Error: {tool_outcome.error_message}"
            obs = raw_obs if len(raw_obs) <= 800 else raw_obs[:790] + "... [truncated]"

            step = AgentStep(
                step_number=step_idx,
                thought=raw_output[:120],
                action_tool=tool_name,
                action_arguments=tool_args,
                observation=obs,
                is_successful=tool_outcome.is_success,
                elapsed_seconds=time.perf_counter() - step_start,
            )
            session.completed_steps.append(step)

            if on_step_callback:
                on_step_callback(step)

            conversation_history.append(f"Step {step_idx} Action: {tool_name}({tool_args})\nObservation:\n{obs}")

        if session.status != TaskStatus.COMPLETED:
            session.status = TaskStatus.COMPLETED if len(session.completed_steps) > 0 else TaskStatus.FAILED
            session.final_output = session.final_output or "Execution completed max iterations."

        return session
