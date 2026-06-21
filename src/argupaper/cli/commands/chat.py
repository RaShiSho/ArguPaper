"""Interactive LangGraph chat command."""

from __future__ import annotations

import asyncio
from contextlib import suppress

import typer
from prompt_toolkit import PromptSession
from prompt_toolkit.input.defaults import create_input
from prompt_toolkit.keys import Keys
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
    except KeyboardInterrupt:
        console.print("[dim]Bye.[/dim]")
    except Exception as exc:
        console.print(format_error(exc))
        raise typer.Exit(code=1)


async def _run_chat() -> None:
    config = load_config(require_pdf_api_key=False)
    console.print(
        Panel(
            "ArguPaper Chat Agent Runtime\n"
            "Commands: /papers, /use <paper-id-or-name>, /debate, /court, /exit\n"
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
                user_input = (
                    await prompt_session.prompt_async(
                        "argupaper> ",
                        set_exception_handler=False,
                    )
                ).strip()
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
    console.print("[dim]Running agent task. Press Esc to interrupt; other input is ignored.[/dim]")
    try:
        while True:
            done, _ = await asyncio.wait({task, esc_task}, return_when=asyncio.FIRST_COMPLETED)
            if task in done:
                await _cancel_task(esc_task)
                return await task
            if esc_task in done:
                value = await esc_task
                if value == ESC_RESULT:
                    console.print(format_warning("Interrupt requested. Cancelling current agent run..."))
                    task.cancel()
                    return await task
    finally:
        if not esc_task.done():
            await _cancel_task(esc_task)


async def _wait_for_escape() -> str:
    """Wait for Escape without starting a second prompt application."""

    loop = asyncio.get_running_loop()
    future: asyncio.Future[str] = loop.create_future()
    prompt_input = create_input()

    def input_ready() -> None:
        for key_press in prompt_input.read_keys():
            if key_press.key == Keys.Escape and not future.done():
                loop.call_soon_threadsafe(future.set_result, ESC_RESULT)

    with prompt_input.raw_mode(), prompt_input.attach(input_ready):
        return await future


async def _cancel_task(task: asyncio.Task[object]) -> None:
    task.cancel()
    with suppress(BaseException):
        await task


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
