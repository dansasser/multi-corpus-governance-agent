#!/usr/bin/env python3
"""
Multi-Corpus Governance Agent CLI
Main command-line interface for the MCG Agent
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional

import click
import uvicorn
from rich.console import Console
from rich.table import Table

from mcg_agent.config import settings
from mcg_agent.cli.smoke_tests import run_comprehensive_smoke_test
from mcg_agent.security.jwt_auth import create_access_token

console = Console()


@click.group()
@click.version_option()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.pass_context
def cli(ctx: click.Context, verbose: bool) -> None:
    """Multi-Corpus Governance Agent CLI
    
    A governed AI assistant that connects to multiple corpora (personal, social, published)
    and routes them through a five-agent pipeline: Ideator → Drafter → Critic → Revisor → Summarizer.
    """
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    
    if verbose:
        console.print("🚀 Multi-Corpus Governance Agent CLI", style="bold blue")


@cli.command("mint-token")
@click.option('--user-id', required=True, help='Subject (user id) for the JWT')
@click.option('--minutes', default=60, type=int, help='Expiration in minutes (<=0 for default)')
def mint_token(user_id: str, minutes: int) -> None:
    """Mint a JWT for development/testing.

    Example:
        mcg-agent mint-token --user-id alice --minutes 120
    """
    from datetime import timedelta
    exp = None if minutes <= 0 else timedelta(minutes=minutes)
    token = create_access_token(user_id, expires_delta=exp)
    console.print(token)


@cli.command()
@click.option('--host', default='0.0.0.0', help='Host to bind to')
@click.option('--port', default=8000, type=int, help='Port to bind to')
@click.option('--workers', default=1, type=int, help='Number of worker processes')
@click.option('--reload', is_flag=True, help='Enable auto-reload for development')
@click.option('--log-level', default='info', 
              type=click.Choice(['critical', 'error', 'warning', 'info', 'debug']),
              help='Log level')
@click.pass_context
def serve(ctx: click.Context, host: str, port: int, workers: int, reload: bool, log_level: str) -> None:
    """Start the MCG Agent server
    
    Examples:
        mcg-agent serve --reload                    # Development server with hot reload
        mcg-agent serve --workers 4                # Production server with 4 workers
        mcg-agent serve --host 0.0.0.0 --port 8080 # Custom host and port
    """
    verbose = ctx.obj.get('verbose', False)
    
    if verbose:
        console.print(f"Starting server on {host}:{port}", style="green")
        console.print(f"Workers: {workers}, Reload: {reload}, Log Level: {log_level}")
    
    # Import here to avoid circular imports
    try:
        from mcg_agent.app import app
    except ImportError as e:
        console.print(f"❌ Failed to import application: {e}", style="red")
        console.print("Make sure the package is installed: pip install -e .", style="yellow")
        sys.exit(1)
    
    # Configure uvicorn
    config = {
        'app': 'mcg_agent.app:app',
        'host': host,
        'port': port,
        'log_level': log_level,
    }
    
    if reload:
        # Development mode
        config.update({
            'reload': True,
            'reload_dirs': ['src/mcg_agent'],
            'reload_excludes': ['*.pyc', '__pycache__'],
        })
        console.print("🔧 Development mode: Auto-reload enabled", style="yellow")
    else:
        # Production mode
        if workers > 1:
            console.print("⚠️  Multiple workers specified. Use Gunicorn for production deployment.", style="yellow")
            console.print("Example: gunicorn mcg_agent.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker", style="dim")
    
    try:
        uvicorn.run(**config)
    except KeyboardInterrupt:
        console.print("\n👋 Server stopped", style="yellow")
    except Exception as e:
        console.print(f"❌ Server error: {e}", style="red")
        sys.exit(1)


@cli.command()
@click.argument('prompt', required=False)
@click.option('--corpus', multiple=True, 
              type=click.Choice(['personal', 'social', 'published']),
              help='Limit search to specific corpus')
@click.option('--format', 'output_format', default='text',
              type=click.Choice(['text', 'json', 'markdown']),
              help='Output format')
@click.pass_context
def query(ctx: click.Context, prompt: Optional[str], corpus: tuple, output_format: str) -> None:
    """Query the MCG Agent pipeline
    
    Examples:
        mcg-agent query "What are my thoughts on AI?"
        mcg-agent query --corpus personal --format json "Recent conversations"
    """
    verbose = ctx.obj.get('verbose', False)
    
    if not prompt:
        prompt = click.prompt("Enter your query")
    
    if verbose:
        console.print(f"Processing query: {prompt}", style="blue")
        if corpus:
            console.print(f"Limited to corpus: {', '.join(corpus)}", style="dim")
    
    # In-process query through pipeline (bypasses auth)
    try:
        from mcg_agent.routing.pipeline import GovernedAgentPipeline
        async def _run():
            pipeline = GovernedAgentPipeline()
            return await pipeline.process_request(prompt)
        result = asyncio.run(_run())
        if output_format == 'json':
            import json as _json
            console.print(_json.dumps({
                'task_id': result.task_id,
                'agent_role': result.agent_role,
                'content': result.content,
                'metadata': result.metadata,
            }, ensure_ascii=False, indent=2))
        elif output_format == 'markdown':
            console.print(f"### Task: {result.task_id}")
            console.print(f"**Role:** {result.agent_role}")
            req_id = (result.metadata or {}).get('request_id')
            if req_id:
                console.print(f"**Request ID:** {req_id}")
            console.print("\n---\n")
            console.print(result.content)
        else:
            console.print(f"\n[bold]Task:[/bold] {result.task_id}")
            console.print(f"[bold]Role:[/bold] {result.agent_role}")
            console.print("\n[bold]Output:[/bold]")
            console.print(result.content)
            if result.metadata:
                console.print("\n[dim]Metadata:[/dim]")
                console.print(result.metadata)
    except Exception as e:
        console.print(f"❌ Query error: {e}", style="red")
        sys.exit(1)


@cli.command()
@click.option('--quick', is_flag=True, help='Run quick smoke test only')
@click.pass_context
def test(ctx: click.Context, quick: bool) -> None:
    """Run smoke tests to verify system functionality
    
    Examples:
        mcg-agent test           # Full smoke test
        mcg-agent test --quick   # Quick connectivity test
    """
    verbose = ctx.obj.get('verbose', False)
    
    if verbose:
        console.print("Running smoke tests...", style="blue")
    
    try:
        result = asyncio.run(run_comprehensive_smoke_test(quick=quick, verbose=verbose))
        if result:
            console.print("✅ All smoke tests passed", style="green")
        else:
            console.print("❌ Some smoke tests failed", style="red")
            sys.exit(1)
    except Exception as e:
        console.print(f"❌ Smoke test error: {e}", style="red")
        sys.exit(1)


@cli.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show system status and configuration
    
    Displays current configuration, database status, and system health.
    """
    verbose = ctx.obj.get('verbose', False)
    
    # Create status table
    table = Table(title="MCG Agent Status", show_header=True, header_style="bold magenta")
    table.add_column("Component", style="cyan", no_wrap=True)
    table.add_column("Status", style="green")
    table.add_column("Details", style="dim")
    
    # Check database
    try:
        from mcg_agent.db.session import get_session
        with get_session() as session:
            session.execute('SELECT 1')
        table.add_row("Database", "✅ Connected", f"URL: {settings.postgres_url}")
    except Exception as e:
        table.add_row("Database", "❌ Error", str(e))
    
    # Check Redis
    try:
        # TODO: Implement Redis check
        table.add_row("Redis", "🚧 Not implemented", f"URL: {settings.redis_url}")
    except Exception as e:
        table.add_row("Redis", "❌ Error", str(e))
    
    # Check configuration
    table.add_row("Environment", "ℹ️  Loaded", f"JWT configured: {'Yes' if settings.JWT_SECRET_KEY else 'No'}")
    
    console.print(table)
    
    if verbose:
        console.print("\n📋 Configuration Details:", style="bold")
        console.print(f"Database Host: {settings.POSTGRES_HOST}")
        console.print(f"Database Port: {settings.POSTGRES_PORT}")
        console.print(f"Redis Host: {settings.REDIS_HOST}")
        console.print(f"Redis Port: {settings.REDIS_PORT}")


@cli.command()
@click.option('--source', type=click.Choice(['openai_chatgpt', 'discord', 'twitter']),
              help='Data source type')
@click.option('--path', type=click.Path(exists=True), help='Path to data file')
@click.option('--corpus', type=click.Choice(['personal', 'social', 'published']),
              help='Target corpus for import')
@click.pass_context
def import_data(ctx: click.Context, source: Optional[str], path: Optional[str], corpus: Optional[str]) -> None:
    """Import data into the MCG Agent corpora
    
    Examples:
        mcg-agent import-data --source openai_chatgpt --path conversations.json --corpus personal
        mcg-agent import-data --source twitter --path tweets.json --corpus social
    """
    verbose = ctx.obj.get('verbose', False)
    
    if not source:
        source = click.prompt("Data source", type=click.Choice(['openai_chatgpt', 'discord', 'twitter']))
    
    if not path:
        path = click.prompt("Path to data file", type=click.Path(exists=True))
    
    if not corpus:
        corpus = click.prompt("Target corpus", type=click.Choice(['personal', 'social', 'published']))
    
    if verbose:
        console.print(f"Importing {source} data from {path} to {corpus} corpus", style="blue")
    
    try:
        # TODO: Implement actual data import
        console.print("🚧 Data import not yet implemented", style="yellow")
        console.print(f"Source: {source}")
        console.print(f"Path: {path}")
        console.print(f"Corpus: {corpus}")
    except Exception as e:
        console.print(f"❌ Import error: {e}", style="red")
        sys.exit(1)


@cli.command()
@click.option('--output', '-o', type=click.Path(), help='Output file path')
@click.option('--format', 'export_format', default='json',
              type=click.Choice(['json', 'csv', 'markdown']),
              help='Export format')
@click.option('--corpus', type=click.Choice(['personal', 'social', 'published']),
              help='Corpus to export')
@click.pass_context
def export_data(ctx: click.Context, output: Optional[str], export_format: str, corpus: Optional[str]) -> None:
    """Export data from the MCG Agent corpora
    
    Examples:
        mcg-agent export-data --corpus personal --format json --output personal_data.json
        mcg-agent export-data --corpus social --format csv --output social_posts.csv
    """
    verbose = ctx.obj.get('verbose', False)
    
    if not corpus:
        corpus = click.prompt("Corpus to export", type=click.Choice(['personal', 'social', 'published']))
    
    if not output:
        output = f"{corpus}_export.{export_format}"
    
    if verbose:
        console.print(f"Exporting {corpus} corpus to {output} in {export_format} format", style="blue")
    
    try:
        # TODO: Implement actual data export
        console.print("🚧 Data export not yet implemented", style="yellow")
        console.print(f"Corpus: {corpus}")
        console.print(f"Format: {export_format}")
        console.print(f"Output: {output}")
    except Exception as e:
        console.print(f"❌ Export error: {e}", style="red")
        sys.exit(1)


def main() -> None:
    """Main CLI entry point"""
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n👋 Goodbye!", style="yellow")
        sys.exit(0)
    except Exception as e:
        console.print(f"❌ Unexpected error: {e}", style="red")
        if '--verbose' in sys.argv or '-v' in sys.argv:
            raise
        sys.exit(1)


if __name__ == '__main__':
    main()
