#!/usr/bin/env python3
from datetime import datetime
from pathlib import Path

import click
import yaml

from src.curation import SourceRegistry
from src.state import SourceStateManager
from src.storage import MarkdownStore, Deduplicator
from src.collection import Coordinator
from src.analysis import BriefGenerator


def get_config_dir() -> Path:
    import os
    return Path(os.environ.get("DAILY_BRIEF_CONFIG", "./config"))


def get_data_dir() -> Path:
    import os
    return Path(os.environ.get("DAILY_BRIEF_DATA", "./data"))


def load_settings() -> dict:
    config_dir = get_config_dir()
    with open(config_dir / "settings.yaml") as f:
        return yaml.safe_load(f)


def load_analysis_config() -> dict:
    config_dir = get_config_dir()
    with open(config_dir / "analysis.yaml") as f:
        return yaml.safe_load(f)


@click.group()
def cli():
    """Daily Brief - Personal intelligence briefing system."""
    pass


@cli.command()
@click.option("--source", "-s", help="Collect from specific source ID only")
@click.option("--force", "-f", is_flag=True, help="Ignore deduplication")
def collect(source: str, force: bool):
    """Collect content from configured sources."""
    config_dir = get_config_dir()
    data_dir = get_data_dir()
    settings = load_settings()

    registry = SourceRegistry(config_dir / "sources.yaml")
    state_manager = SourceStateManager(data_dir / "state")
    store = MarkdownStore(
        content_dir=data_dir / "content",
        briefs_dir=data_dir / "briefs",
    )
    deduplicator = Deduplicator(data_dir / "state" / "dedup_index.json")

    coordinator = Coordinator(
        source_registry=registry,
        state_manager=state_manager,
        store=store,
        deduplicator=deduplicator,
        max_age_days=settings.get("collection", {}).get("max_age_days", 7),
    )

    if source:
        click.echo(f"Collecting from source: {source}")
        stats = coordinator.collect_by_id(source, force=force)
        if stats is None:
            click.echo(f"Source '{source}' not found", err=True)
            raise SystemExit(1)
    else:
        click.echo("Collecting from all enabled sources...")
        stats = coordinator.collect_all(force=force)

    click.echo(f"\nCollection complete:")
    click.echo(f"  Sources processed: {stats.sources_processed}")
    click.echo(f"  Items fetched: {stats.items_fetched}")
    click.echo(f"  Items stored: {stats.items_stored}")
    click.echo(f"  Duplicates skipped: {stats.items_skipped_duplicate}")
    if stats.errors:
        click.echo(f"  Errors: {stats.errors}")


@cli.command()
@click.option("--source", "-s", help="Show detailed status for specific source")
def status(source: str):
    """Show source status and diagnostics."""
    config_dir = get_config_dir()
    data_dir = get_data_dir()

    registry = SourceRegistry(config_dir / "sources.yaml")
    state_manager = SourceStateManager(data_dir / "state")
    states = state_manager.get_all_states()
    sources = registry.get_all_sources()

    if source:
        src = registry.get_source_by_id(source)
        if not src:
            click.echo(f"Source '{source}' not found", err=True)
            raise SystemExit(1)

        state = states.get(source)
        click.echo(f"\nSource: {src.name} ({src.id})")
        click.echo(f"  Type: {src.type.value}")
        click.echo(f"  URL: {src.url}")
        click.echo(f"  Enabled: {src.enabled}")

        if state:
            click.echo(f"\n  Last attempt: {state.last_fetch_attempt or 'Never'}")
            click.echo(f"  Last success: {state.last_successful_fetch or 'Never'}")
            click.echo(f"  Status: {'OK' if state.last_fetch_success else 'FAILING'}")
            if state.last_error:
                click.echo(f"  Last error: {state.last_error}")
            click.echo(f"  Items (last run): {state.items_fetched_last_run}")
            click.echo(f"  Items (total): {state.total_items_fetched}")
            click.echo(f"  Consecutive failures: {state.consecutive_failures}")

            if state.fetch_history:
                click.echo(f"\n  Recent history:")
                for entry in state.fetch_history[:5]:
                    status_mark = "OK" if entry.success else "FAIL"
                    click.echo(f"    {entry.timestamp}: {status_mark} ({entry.items_fetched} items, {entry.duration_seconds}s)")
        else:
            click.echo("\n  No fetch history yet")
        return

    click.echo("\nDaily Brief - Source Status")
    click.echo("=" * 60)
    click.echo(f"{'Source':<20} {'Last Success':<20} {'Status':<10} {'Items (24h)':<10}")
    click.echo("-" * 60)

    healthy = 0
    needs_attention = 0

    for src in sources:
        state = states.get(src.id)
        if state:
            last_success = state.last_successful_fetch[:10] if state.last_successful_fetch else "Never"
            status_str = "OK" if state.last_fetch_success else "FAILING"
            items = str(state.items_fetched_last_run)

            if state.last_fetch_success:
                healthy += 1
            else:
                needs_attention += 1
                status_str = "FAILING"
        else:
            last_success = "Never"
            status_str = "NEW"
            items = "0"

        status_icon = "+" if status_str == "OK" else ("?" if status_str == "NEW" else "!")
        click.echo(f"{src.id:<20} {last_success:<20} {status_icon} {status_str:<7} {items:<10}")

        if state and state.last_error:
            click.echo(f"  Error: {state.last_error[:50]}...")

    click.echo("-" * 60)
    click.echo(f"Total: {len(sources)} sources, {healthy} healthy, {needs_attention} need attention")


@cli.command()
def sources():
    """List configured sources."""
    config_dir = get_config_dir()
    registry = SourceRegistry(config_dir / "sources.yaml")

    click.echo("\nConfigured Sources:")
    click.echo("-" * 60)

    for src in registry.get_all_sources():
        status = "enabled" if src.enabled else "disabled"
        click.echo(f"  {src.id}")
        click.echo(f"    Name: {src.name}")
        click.echo(f"    Type: {src.type.value}")
        click.echo(f"    Category: {src.category}")
        click.echo(f"    Status: {status}")
        click.echo(f"    URL: {src.url}")
        click.echo()


@cli.command()
@click.option("--since", "-s", default="24h", help="Content window (e.g., 24h, 48h)")
@click.option("--dry-run", is_flag=True, help="Show what would be analyzed")
def analyze(since: str, dry_run: bool):
    """Generate a brief from recent content."""
    config_dir = get_config_dir()
    data_dir = get_data_dir()
    analysis_config = load_analysis_config()

    hours = int(since.replace("h", ""))

    store = MarkdownStore(
        content_dir=data_dir / "content",
        briefs_dir=data_dir / "briefs",
    )

    llm_config = analysis_config.get("llm", {})
    analysis_settings = analysis_config.get("analysis", {})

    generator = BriefGenerator(
        store=store,
        system_prompt=analysis_settings.get("system_prompt", ""),
        model=llm_config.get("model", "claude-sonnet-4-20250514"),
        max_tokens=llm_config.get("max_tokens", 8000),
        content_window_hours=hours,
    )

    if dry_run:
        click.echo(f"Dry run: analyzing content from last {hours} hours...")
        generator.generate(dry_run=True)
        return

    click.echo(f"Generating brief from content in last {hours} hours...")
    brief_path = generator.generate()

    if brief_path:
        click.echo(f"\nBrief generated: {brief_path}")
    else:
        click.echo("\nNo content found to analyze")


@cli.command()
@click.option("--port", "-p", default=3000, help="Port to run server on")
@click.option("--host", "-h", default="127.0.0.1", help="Host to bind to")
def serve(port: int, host: str):
    """Start the web UI server."""
    from src.ui.server import create_app

    app = create_app()
    click.echo(f"Starting server at http://{host}:{port}")
    app.run(host=host, port=port, debug=True)


if __name__ == "__main__":
    cli()
