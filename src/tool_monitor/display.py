# display.py
# All terminal output for the Merkle-CFI harness demo.
#
# This module owns presentation entirely. harness.py never formats strings —
# it calls named functions here. Swap this file to change the entire UI.
#
# Colour language:
#   cyan    — scaffolding / routing events
#   blue    — model calls and responses
#   yellow  — verification checkpoints
#   green   — success / confirmed
#   red     — failures, halts, integrity breaches
#   magenta — ReACT internals (Thought / Action / Observation)

import json

from rich import box
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from tool_monitor.models import ExecutionRecord, Plan

console = Console()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _label(tag: str, color: str) -> Text:
    t = Text()
    t.append(f" {tag} ", style=f"bold white on {color}")
    return t


def _mono(value: str, max_len: int = 120) -> str:
    if len(value) > max_len:
        return value[:max_len] + "…"
    return value


# ---------------------------------------------------------------------------
# Pipeline entry
# ---------------------------------------------------------------------------


def banner(user_model: str, tool_model: str) -> None:
    console.print()
    console.print(
        Panel.fit(
            "[bold cyan]Merkle-CFI Agentic Harness[/bold cyan]\n"
            "[dim]Control-Flow Integrity via Plan-then-Execute + SHA-256 Merkle Binding[/dim]\n\n"
            f"[dim]User model :[/dim] [white]{user_model}[/white]\n"
            f"[dim]Tool model :[/dim] [white]{tool_model}[/white]",
            border_style="cyan",
            padding=(1, 4),
        )
    )


def prompt_received(prompt: str) -> None:
    console.print()
    console.print(Rule("[cyan]NEW REQUEST[/cyan]", style="cyan"))
    console.print(
        Panel(
            f"[white]{prompt}[/white]",
            title=_label("USER PROMPT", "cyan"),
            border_style="cyan",
            padding=(0, 2),
        )
    )


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------


def calling_user_model() -> None:
    console.print()
    console.print(_label("SCAFFOLD", "cyan"), "[cyan] → Forwarding prompt to user model…[/cyan]")


def pte_detected() -> None:
    console.print()
    console.print(
        Panel(
            "[bold white]<planthenexecute>[/bold white] token detected in user model response.\n"
            "[dim]Routing to tool model. User model will be blind until execution completes.[/dim]",
            title=_label("SCAFFOLD: PtE DETECTED", "cyan"),
            border_style="cyan",
            padding=(0, 2),
        )
    )


def direct_response_path() -> None:
    console.print()
    console.print(
        _label("SCAFFOLD", "cyan"),
        "[cyan] No[/cyan] [bold white]<planthenexecute>[/bold white]"
        "[cyan] token — returning direct response to user.[/cyan]",
    )


# ---------------------------------------------------------------------------
# Plan display
# ---------------------------------------------------------------------------


def plan_parsed(plan: Plan) -> None:
    console.print()
    table = Table(
        box=box.SIMPLE_HEAVY,
        border_style="cyan",
        show_header=True,
        header_style="bold cyan",
        padding=(0, 1),
    )
    table.add_column("ID", justify="center", width=4)
    table.add_column("Tool", style="bold white", width=12)
    table.add_column("Args", style="dim white", width=32)
    table.add_column("Description", style="white")

    for step in plan.steps:
        table.add_row(
            str(step.id),
            step.tool,
            _mono(json.dumps(step.args), 30),
            step.description,
        )

    console.print(
        Panel(
            table,
            title=_label("SCAFFOLD: PLAN PARSED", "cyan"),
            subtitle=f"[dim]Goal: {plan.goal}[/dim]",
            border_style="cyan",
            padding=(0, 1),
        )
    )


# ---------------------------------------------------------------------------
# Merkle tree
# ---------------------------------------------------------------------------


def merkle_committed(root: str, leaves: list[str]) -> None:
    console.print()

    leaf_table = Table(box=box.SIMPLE, show_header=True, header_style="bold yellow", padding=(0, 1))
    leaf_table.add_column("Step", justify="center", width=6)
    leaf_table.add_column("Leaf Hash (SHA-256)", style="yellow")

    for i, leaf in enumerate(leaves):
        leaf_table.add_row(str(i), leaf)

    console.print(
        Panel(
            f"[bold yellow]Root:[/bold yellow] [white]{root}[/white]\n\n" + "",
            title=_label("SCAFFOLD: MERKLE TREE COMMITTED", "yellow"),
            border_style="yellow",
            padding=(0, 2),
        )
    )
    console.print(leaf_table)
    console.print(
        "[dim yellow]  Plan is now cryptographically bound. "
        "Any mutation will be detected before execution.[/dim yellow]"
    )


# ---------------------------------------------------------------------------
# Safety gate
# ---------------------------------------------------------------------------


def safety_gate_start() -> None:
    console.print()
    console.print(
        _label("SCAFFOLD", "cyan"),
        "[cyan] → Dispatching plan to tool model for safety inspection…[/cyan]",
    )
    console.print("[dim]  Evaluating: harmful actions / unknown tools / over-scoped steps[/dim]")


def safety_gate_pass() -> None:
    console.print()
    console.print(
        Panel(
            "[bold green]Plan passed safety inspection.[/bold green]\n"
            "[dim]No harmful, over-scoped, or unregistered tool calls detected.[/dim]",
            title=_label("SAFETY GATE: PASS ✓", "green"),
            border_style="green",
            padding=(0, 2),
        )
    )


def safety_gate_fail(reason: str) -> None:
    console.print()
    console.print(
        Panel(
            f"[bold red]Plan rejected.[/bold red]\n\n[white]{reason}[/white]",
            title=_label("SAFETY GATE: FAIL ✗", "red"),
            border_style="red",
            padding=(0, 2),
        )
    )


# ---------------------------------------------------------------------------
# Execution loop
# ---------------------------------------------------------------------------


def execution_start(total: int) -> None:
    console.print()
    console.print(Rule(f"[cyan]EXECUTION LOOP — {total} step(s)[/cyan]", style="cyan"))


def step_start(index: int, total: int, description: str) -> None:
    console.print()
    console.print(
        f"[bold cyan]  STEP [{index + 1}/{total}][/bold cyan]  [white]{description}[/white]"
    )


def hash_verifying(index: int) -> None:
    console.print(
        f"  [yellow]↳ Verifying Merkle leaf[/yellow] [dim yellow]index={index}[/dim yellow]…"
    )


def hash_verified(index: int, leaf: str) -> None:
    console.print(f"  [bold green]✓ Hash verified[/bold green]  [dim]{leaf[:24]}…{leaf[-8:]}[/dim]")


def hash_failed(index: int) -> None:
    console.print()
    console.print(
        Panel(
            f"[bold red]Leaf hash mismatch at index {index}.[/bold red]\n"
            "[white]Plan integrity cannot be confirmed. Execution halted immediately.[/white]\n"
            "[dim]This may indicate a prompt injection attempt modified the plan post-commit.[/dim]",
            title=_label("INTEGRITY BREACH ✗", "red"),
            border_style="red",
            padding=(0, 2),
        )
    )


def react_thought(thought: str) -> None:
    console.print(f"  [magenta]Thought[/magenta]  [dim white]{_mono(thought, 200)}[/dim white]")


def react_action(tool: str, args: dict) -> None:
    console.print(
        f"  [magenta]Action[/magenta]   [bold white]{tool}[/bold white]"
        f"  [dim]{json.dumps(args)}[/dim]"
    )


def react_observation(observation: str) -> None:
    console.print(f"  [magenta]Observe[/magenta]  [white]{_mono(observation, 140)}[/white]")


def tool_not_found(tool_name: str) -> None:
    console.print(
        Panel(
            f"[bold red]Tool [white]{tool_name!r}[/white] is not registered.[/bold red]\n"
            "[dim]Tool model requested an action outside the permit list. Halting.[/dim]",
            title=_label("TOOL NOT FOUND ✗", "red"),
            border_style="red",
            padding=(0, 2),
        )
    )


# ---------------------------------------------------------------------------
# Post-execution verification
# ---------------------------------------------------------------------------


def post_verification_start() -> None:
    console.print()
    console.print(Rule("[yellow]POST-EXECUTION VERIFICATION[/yellow]", style="yellow"))
    console.print(
        "[yellow]  Recomputing Merkle root from executed plan "
        "and comparing against committed root…[/yellow]"
    )


def post_verification_pass(root: str) -> None:
    console.print(
        f"  [bold green]✓ Root confirmed:[/bold green] [dim]{root}[/dim]\n"
        "  [green]Plan was not mutated during execution. "
        "Releasing trace to user model.[/green]"
    )


def post_verification_fail() -> None:
    console.print(
        Panel(
            "[bold red]Post-execution root mismatch.[/bold red]\n"
            "[white]The plan state after execution does not match the committed root.\n"
            "Results are discarded. This event should be logged and investigated.[/white]",
            title=_label("ROOT MISMATCH ✗", "red"),
            border_style="red",
            padding=(0, 2),
        )
    )


# ---------------------------------------------------------------------------
# Synthesis
# ---------------------------------------------------------------------------


def synthesis_start() -> None:
    console.print()
    console.print(Rule("[cyan]SYNTHESIS[/cyan]", style="cyan"))
    console.print(
        "[cyan]  Passing verified execution trace back to user model "
        "for final response synthesis…[/cyan]"
    )


def execution_summary(log: list[ExecutionRecord]) -> None:
    console.print()
    table = Table(
        box=box.SIMPLE_HEAVY,
        border_style="dim",
        show_header=True,
        header_style="bold dim",
        padding=(0, 1),
    )
    table.add_column("Step", justify="center", width=6)
    table.add_column("Tool", width=12)
    table.add_column("Verified", justify="center", width=10)
    table.add_column("Observation", style="dim white")

    for record in log:
        verified = (
            "[bold green]✓[/bold green]" if record.hash_verified else "[bold red]✗[/bold red]"
        )
        table.add_row(
            str(record.step_id),
            record.tool,
            verified,
            _mono(record.observation, 60),
        )

    console.print(
        Panel(
            table,
            title="[dim]EXECUTION SUMMARY[/dim]",
            border_style="dim",
            padding=(0, 1),
        )
    )


# ---------------------------------------------------------------------------
# Final result
# ---------------------------------------------------------------------------


def final_result(result: str) -> None:
    console.print()
    console.print(
        Panel(
            f"[white]{result}[/white]",
            title=_label("RESULT", "green"),
            border_style="green",
            padding=(1, 2),
        )
    )
    console.print()


def halt(reason: str) -> None:
    console.print()
    console.print(
        Panel(
            f"[bold white]{reason}[/bold white]",
            title=_label("HALT", "red"),
            border_style="red",
            padding=(0, 2),
        )
    )
    console.print()
