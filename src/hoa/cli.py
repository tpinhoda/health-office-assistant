"""CLI entry point for Health Office Assistant."""
import click


@click.group()
def main():
    """Health Office Assistant - stay healthy at work."""
    pass


@main.command()
def run():
    """Run the background health reminder daemon."""
    click.echo("Not implemented yet.")


@main.command()
def tui():
    """Launch the TUI dashboard."""
    click.echo("Not implemented yet.")


@main.command()
def status():
    """Show current progress."""
    click.echo("Not implemented yet.")


@main.command()
def config():
    """Show current configuration."""
    click.echo("Not implemented yet.")
