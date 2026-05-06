"""CLI entry point for Health Office Assistant."""

import json
from dataclasses import asdict
from pathlib import Path

import click

from hoa.config import load_config
from hoa.daemon import DEFAULT_STATE_PATH, Daemon
from hoa.scheduler import calculate_daily_goal_ml
from hoa.state import load_state


@click.group()
def main():
    """Health Office Assistant - stay healthy at work."""
    pass


@main.command()
def run():
    """Run the background health reminder daemon."""
    daemon = Daemon()
    click.echo("Starting HOA daemon...")
    daemon.run()


@main.command()
def tui():
    """Launch the TUI dashboard."""
    from hoa.tui import run_tui

    run_tui()


@main.command()
def status():
    """Show current progress."""
    config = load_config()
    state = load_state(DEFAULT_STATE_PATH, config.max_snoozes)
    goal = calculate_daily_goal_ml(config.weight_kg)
    remaining = max(0, goal - state.consumed_ml)
    pct = min(100, int(state.consumed_ml / goal * 100)) if goal > 0 else 0

    click.echo(f"Date: {state.date}")
    click.echo(f"Water: {state.consumed_ml} / {goal} ml ({pct}%)")
    click.echo(f"Remaining: {remaining} ml")
    click.echo(f"Sedentary breaks: {state.sedentary_completions}")
    click.echo(f"Eye rests: {state.eye_rest_completions}")

    if remaining > 0:
        interval = config.water_interval_min
        click.echo(f"Next drink suggestion: ~{remaining // 4} ml in {interval} min")
    else:
        click.echo("Daily water goal reached!")


@main.command()
def config():
    """Show current configuration."""
    cfg = load_config()
    click.echo(json.dumps(asdict(cfg), indent=2))
