"""Octopus CLI — the terminal interface to your 8-armed AI assistant."""

from __future__ import annotations

import sys
from typing import Any

import click
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

console = Console()

OCTOPUS_LOGO = r"""[bold cyan]
   ___      _
  / _ \  __| |_ ___  _ __  _   _ ___
 | | | |/ _` __/ _ \| '_ \| | | / __|
 | |_| | (_| || (_) | |_) | |_| \__ \
  \___/ \__,_|\___/| .__/ \__,_|___/
                   |_|
[/bold cyan][dim]Your 8-armed AI personal assistant[/dim]
"""


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx: click.Context) -> None:
    """Octopus — 8-armed AI personal assistant for the terminal."""
    if ctx.invoked_subcommand is None:
        console.print(OCTOPUS_LOGO)
        console.print("  [bold]Commands:[/bold]")
        console.print("    [cyan]octopus review[/cyan]     — Review and approve staged actions")
        console.print("    [cyan]octopus chat[/cyan]       — Chat with your assistant")
        console.print("    [cyan]octopus run[/cyan]        — Run a workflow manually")
        console.print("    [cyan]octopus poll[/cyan]       — Start the background email poller")
        console.print("    [cyan]octopus memory[/cyan]     — Query the memory bank")
        console.print("    [cyan]octopus workflows[/cyan]  — List available workflows")
        console.print("    [cyan]octopus config[/cyan]     — Show current configuration")
        console.print()


@main.command()
@click.option("--workflow", "-w", default=None, help="Filter by workflow name")
def review(workflow: str | None) -> None:
    """Review and approve staged actions in the sandbox queue."""
    from octopus.security.sandbox import ActionSandbox

    sandbox = ActionSandbox()
    sandbox.expire_old()
    grouped = sandbox.all_pending_by_workflow()

    if not grouped:
        console.print("[green]✓ No pending actions.[/green]")
        return

    for wf_id, actions in grouped.items():
        if workflow and actions[0].workflow_name.lower() != workflow.lower():
            continue

        wf_name = actions[0].workflow_name
        triggered_by = actions[0].triggered_by

        console.print()
        console.print(Panel(
            f"[bold yellow]WORKFLOW: {wf_name}[/bold yellow]\n"
            f"[dim]Triggered by: {triggered_by}[/dim]",
            border_style="yellow",
        ))

        # Display each proposed action
        for action in actions:
            _render_action(action)

        console.print()
        choice = Prompt.ask(
            "  [bold]\\[Y][/bold] Approve & Execute  [bold]\\[E][/bold] Edit  [bold]\\[N][/bold] Reject",
            choices=["y", "Y", "e", "E", "n", "N"],
            default="N",
            show_choices=False,
        )

        if choice.upper() == "Y":
            _execute_workflow(sandbox, wf_id, actions)
        elif choice.upper() == "E":
            _edit_workflow(sandbox, wf_id, actions)
        else:
            sandbox.reject_workflow(wf_id)
            console.print("[red]✗ Rejected and cleared.[/red]")


def _render_action(action) -> None:
    from octopus.models import ActionType

    icon = {
        ActionType.SEND_EMAIL: "✉",
        ActionType.REPLY_EMAIL: "↩",
        ActionType.CREATE_CALENDAR_EVENT: "📅",
        ActionType.HOLD_CALENDAR_SLOTS: "🔒",
        ActionType.CREATE_TASK: "✅",
        ActionType.UPDATE_TASK: "✏",
        ActionType.SEND_NOTIFICATION: "🔔",
    }.get(action.action_type, "•")

    payload = action.payload
    action_type = action.action_type.value.replace("_", " ").title()

    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    table.add_column(style="dim", width=12)
    table.add_column()

    if action.action_type in (ActionType.SEND_EMAIL, ActionType.REPLY_EMAIL):
        table.add_row("To", payload.get("to", ""))
        table.add_row("Subject", payload.get("subject", ""))
        body = payload.get("body", "")
        preview = body[:120].replace("\n", " ") + ("…" if len(body) > 120 else "")
        table.add_row("Preview", f"[dim]{preview}[/dim]")
    elif action.action_type in (ActionType.CREATE_CALENDAR_EVENT, ActionType.HOLD_CALENDAR_SLOTS):
        table.add_row("Title", payload.get("title", ""))
        table.add_row("Start", str(payload.get("start", "")))
        table.add_row("End", str(payload.get("end", "")))
    elif action.action_type in (ActionType.CREATE_TASK, ActionType.UPDATE_TASK):
        table.add_row("Task", payload.get("title", ""))
        table.add_row("Project", payload.get("project", ""))

    console.print(f"  [bold]{icon} {action_type}[/bold]")
    console.print(table)


def _execute_workflow(sandbox, wf_id: str, actions) -> None:
    from octopus.arms.arm1_email import EmailPoller
    from octopus.arms.arm3_scheduler import SlotScheduler
    from octopus.arms.arm5_tasks import TaskManager
    from octopus.models import ActionType

    email_arm = None
    cal_arm = None
    task_arm = None

    for action in actions:
        try:
            if action.action_type in (ActionType.SEND_EMAIL, ActionType.REPLY_EMAIL):
                if email_arm is None:
                    email_arm = EmailPoller()
                p = action.payload
                email_arm.send_reply(p["to"], p["subject"], p["body"], p.get("thread_id"))
                console.print(f"  [green]✓ Email sent to {p['to']}[/green]")

            elif action.action_type in (ActionType.CREATE_TASK, ActionType.UPDATE_TASK):
                if task_arm is None:
                    task_arm = TaskManager()
                p = action.payload
                task_id = task_arm.create(p["title"], p.get("project", "Inbox"), p.get("priority", "Normal"))
                console.print(f"  [green]✓ Task created: {p['title']} [{task_id}][/green]")

            sandbox.approve(action.id)

        except Exception as exc:
            console.print(f"  [red]✗ Failed: {exc}[/red]")
            sandbox.reject(action.id)

    console.print("[green]✓ Workflow executed.[/green]")


def _edit_workflow(sandbox, wf_id: str, actions) -> None:
    import tempfile, os, subprocess

    for action in actions:
        if "body" in action.payload:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False, prefix="octopus_draft_"
            ) as f:
                f.write(action.payload["body"])
                tmp = f.name

            editor = os.environ.get("EDITOR", "vi")
            subprocess.call([editor, tmp])

            with open(tmp) as f:
                action.payload["body"] = f.read()
            os.unlink(tmp)
            console.print("[cyan]Draft updated.[/cyan]")

    console.print("Run [bold]octopus review[/bold] again to approve the edited actions.")


@main.command()
@click.argument("message", nargs=-1)
def chat(message: tuple[str, ...]) -> None:
    """Chat with Octopus directly. Type your message or start an interactive session."""
    from octopus.agent.brain import Brain

    try:
        brain = Brain()
    except RuntimeError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    if message:
        response = brain.chat(" ".join(message))
        console.print(response)
    else:
        console.print("[dim]Interactive chat — type 'exit' to quit[/dim]\n")
        history: list[dict] = []
        while True:
            try:
                user_input = Prompt.ask("[bold cyan]You[/bold cyan]")
            except (EOFError, KeyboardInterrupt):
                console.print("\n[dim]Goodbye.[/dim]")
                break
            if user_input.strip().lower() in ("exit", "quit", "q"):
                break
            history.append({"role": "user", "content": user_input})
            response = brain.chat(user_input, history=history[:-1])
            history.append({"role": "assistant", "content": response})
            console.print(f"\n[bold green]Octopus[/bold green]: {response}\n")


@main.command("run")
@click.argument("workflow_name")
@click.option("--sender", default="manual@octopus.local", help="Simulated trigger sender")
@click.option("--subject", default="Manual trigger", help="Simulated email subject")
@click.option("--body", default="", help="Simulated email body")
def run_workflow(workflow_name: str, sender: str, subject: str, body: str) -> None:
    """Manually trigger a workflow by name."""
    from octopus.agent.brain import Brain
    from octopus.workflows import WorkflowEngine

    try:
        brain = Brain()
    except RuntimeError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    engine = WorkflowEngine(brain=brain)
    trigger_data = {
        "sender": sender,
        "sender_name": sender.split("@")[0],
        "subject": subject,
        "body": body,
        "message_id": "manual",
        "thread_id": None,
        "requested_date": "",
    }

    with console.status(f"Running workflow [bold]{workflow_name}[/bold]..."):
        try:
            run = engine.run(workflow_name, trigger_data, trigger_source=sender)
        except FileNotFoundError as e:
            console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)

    if run.status == "paused":
        console.print(f"[yellow]⏸ Workflow paused. Run [bold]octopus review[/bold] to approve actions.[/yellow]")
    else:
        console.print(f"[green]✓ Workflow completed.[/green]")


@main.command()
@click.option("--max", "max_results", default=20, help="Max emails to process per cycle")
def poll(max_results: int) -> None:
    """Start the background email poller (blocks; run in a separate terminal)."""
    from octopus.agent.brain import Brain
    from octopus.agent.dispatcher import Dispatcher
    from octopus.arms.arm1_email import EmailPoller

    console.print("[cyan]Starting Octopus email poller…[/cyan] Press Ctrl+C to stop.\n")

    try:
        brain = Brain()
    except RuntimeError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    dispatcher = Dispatcher(brain=brain)
    poller = EmailPoller()

    def on_email(msg):
        console.print(f"[dim][Arm 1][/dim] New email from [bold]{msg.sender}[/bold]: {msg.subject}")
        run_ids = dispatcher.dispatch_email(msg)
        if run_ids:
            console.print(f"  → Triggered {len(run_ids)} workflow(s). Run [bold]octopus review[/bold] to approve.")
        poller.mark_read(msg.message_id)

    try:
        poller.poll_loop(on_email)
    except KeyboardInterrupt:
        console.print("\n[dim]Poller stopped.[/dim]")


@main.command()
@click.argument("query")
@click.option("--entity", "-e", default=None, help="Filter by entity name")
@click.option("--top", "-k", default=5, help="Number of results")
def memory(query: str, entity: str | None, top: int) -> None:
    """Query the memory bank (Arm 7)."""
    from octopus.arms.arm7_memory import MemoryBank

    bank = MemoryBank()
    entries = bank.recall(query, entity=entity, top_k=top)

    if not entries:
        console.print("[dim]No memories found.[/dim]")
        return

    table = Table(title=f"Memory results for: {query!r}", box=box.ROUNDED)
    table.add_column("Entity", style="cyan")
    table.add_column("Content")
    table.add_column("Date", style="dim")

    for e in entries:
        table.add_row(e.entity, e.content[:80], e.created_at.strftime("%Y-%m-%d"))

    console.print(table)


@main.command()
def workflows() -> None:
    """List all available workflows."""
    from octopus.workflows import list_workflows, load_workflow

    names = list_workflows()
    if not names:
        console.print("[dim]No workflows found.[/dim]")
        return

    table = Table(title="Available Workflows", box=box.ROUNDED)
    table.add_column("Name", style="cyan")
    table.add_column("Mode")
    table.add_column("Trigger")
    table.add_column("Description")

    for name in names:
        try:
            wf = load_workflow(name)
            trigger = wf.get("trigger", {})
            trigger_str = trigger.get("type", "manual")
            if trigger.get("keywords"):
                trigger_str += f" ({', '.join(trigger['keywords'][:2])}…)"
            mode = wf.get("mode", "deterministic")
            desc = (wf.get("description") or "").strip()[:60]
            table.add_row(name, mode, trigger_str, desc)
        except Exception as exc:
            table.add_row(name, "?", "?", f"[red]Error: {exc}[/red]")

    console.print(table)


@main.command("ui")
@click.option("--port", default=7842, help="Port to bind (default: 7842)")
@click.option("--no-browser", is_flag=True, help="Don't open browser automatically")
def launch_ui(port: int, no_browser: bool) -> None:
    """Launch the Octopus graphical dashboard in a browser window."""
    try:
        from flask import Flask
    except ImportError:
        console.print("[red]Error:[/red] Flask is required for the UI. Run: pip install flask")
        sys.exit(1)

    from octopus.gui.server import create_app

    app = create_app()
    url = f"http://localhost:{port}"

    console.print(f"[cyan]Starting Octopus UI at[/cyan] [bold]{url}[/bold]")

    if not no_browser:
        import threading, webbrowser
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()

    import logging
    log = logging.getLogger("werkzeug")
    log.setLevel(logging.ERROR)

    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)


@main.command()
def config() -> None:
    """Show the current Octopus configuration."""
    from octopus.config import load_config, _config_paths

    cfg = load_config()

    for path in _config_paths():
        if path.exists():
            console.print(f"[dim]Config file: {path}[/dim]\n")
            break

    table = Table(title="Octopus Configuration", box=box.ROUNDED)
    table.add_column("Section", style="cyan")
    table.add_column("Key")
    table.add_column("Value")

    for section_name, section in cfg.model_dump().items():
        for key, value in section.items():
            if "key" in key.lower() or "pass" in key.lower() or "token" in key.lower():
                value = "***" if value else "(not set)"
            table.add_row(section_name, key, str(value))

    console.print(table)
