"""Interactive LangGraph chat command."""

from __future__ import annotations

import asyncio

import typer
from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from rich.markdown import Markdown
from rich.panel import Panel

from argupaper.agents.chat import ChatAgentRuntime, ChatTurnResult
from argupaper.cli.commands.common import console
from argupaper.cli.formatters import format_error, format_info, format_warning
from argupaper.config import load_config

ESC_RESULT = "__ARGUPAPER_ESC__"


def chat() -> None:
    """Start the LangGraph-powered research chat agent."""

    try:
        asyncio.run(_run_chat())
    except Exception as exc:
        console.print(format_error(exc))
        raise typer.Exit(code=1)


async def _run_chat() -> None:
    config = load_config(require_pdf_api_key=False)
    console.print(
        Panel(
            "ArguPaper Chat Agent Runtime\n"
            "Commands: /papers, /use <paper-id-or-name>, /analyze, /exit\n"
            "Natural language uses Planner + ReAct tools when LLM is configured.",
            title="[bold]argupaper chat[/bold]",
            border_style="cyan",
            expand=False,
        )
    )

    def progress_callback(message: str) -> None:
        console.print(f"[dim]{message}[/dim]")

    runtime = ChatAgentRuntime(config, progress_callback=progress_callback)
    prompt_session: PromptSession[str] = PromptSession()
    try:
        while True:
            try:
                user_input = (await prompt_session.prompt_async("argupaper> ")).strip()
            except (EOFError, KeyboardInterrupt):
                console.print("[dim]Bye.[/dim]")
                return
            if not user_input:
                continue
            if user_input.lower() == "/exit":
                console.print("[dim]Bye.[/dim]")
                return

            result = await _run_turn_with_interrupt(runtime, user_input)
            _render_turn_result(result)
    finally:
        await runtime.close()


async def _run_turn_with_interrupt(runtime: ChatAgentRuntime, user_input: str) -> ChatTurnResult:
    task = asyncio.create_task(runtime.run_turn(user_input))
    esc_task = asyncio.create_task(_wait_for_escape())
    try:
        while True:
            done, _ = await asyncio.wait({task, esc_task}, return_when=asyncio.FIRST_COMPLETED)
            if task in done:
                esc_task.cancel()
                return await task
            if esc_task in done:
                value = await esc_task
                if value == ESC_RESULT:
                    console.print(format_warning("Interrupt requested. Cancelling current agent run..."))
                    task.cancel()
                    return await task
                console.print("[dim]Agent is running; queued input is ignored. Press Esc to interrupt.[/dim]")
                esc_task = asyncio.create_task(_wait_for_escape())
    finally:
        if not esc_task.done():
            esc_task.cancel()


async def _wait_for_escape() -> str:
    bindings = KeyBindings()

    @bindings.add("escape")
    def _handle_escape(event) -> None:  # type: ignore[no-untyped-def]
        event.app.exit(result=ESC_RESULT)

    running_session: PromptSession[str] = PromptSession(key_bindings=bindings)
    try:
        return await running_session.prompt_async("[running: Esc to interrupt] ")
    except (EOFError, KeyboardInterrupt):
        return ESC_RESULT


def _render_turn_result(result: ChatTurnResult) -> None:
    if result.interrupted:
        console.print(format_warning(result.response))
        return
    if result.selected_paper is not None:
        console.print(
            format_info(
                "Selected paper: "
                f"{result.selected_paper.paper_id} | {result.selected_paper.title}"
            )
        )
    for warning in result.warnings:
        console.print(format_warning(warning))
    console.print(Markdown(result.response))
    if result.log_path:
        console.print(f"[dim]Chat log: {result.log_path}[/dim]")


__all__ = ["chat"]
