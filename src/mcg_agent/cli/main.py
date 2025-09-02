#!/usr/bin/env python3
"""
MCG Agent Main CLI Entry Point
"""

import typer
from typing import Optional

app = typer.Typer(
    name="mcg-agent",
    help="Multi-Corpus Governance Agent CLI",
    add_completion=False
)

@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Host to bind to"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to bind to"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload for development"),
    workers: Optional[int] = typer.Option(None, "--workers", "-w", help="Number of worker processes")
):
    """Start the MCG Agent FastAPI server."""
    try:
        import uvicorn
        from mcg_agent.api.app import app as fastapi_app
        
        if workers and workers > 1:
            # Use Gunicorn for multiple workers
            import subprocess
            import sys
            
            cmd = [
                sys.executable, "-m", "gunicorn",
                "mcg_agent.api.app:app",
                "--bind", f"{host}:{port}",
                "--workers", str(workers),
                "--worker-class", "uvicorn.workers.UvicornWorker"
            ]
            subprocess.run(cmd)
        else:
            # Use Uvicorn for single worker or development
            uvicorn.run(
                "mcg_agent.api.app:app",
                host=host,
                port=port,
                reload=reload,
                log_level="info"
            )
    except ImportError as e:
        typer.echo(f"Error: Missing dependency - {e}", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"Error starting server: {e}", err=True)
        raise typer.Exit(1)

@app.command()
def version():
    """Show version information."""
    try:
        import mcg_agent
        typer.echo(f"MCG Agent version: {mcg_agent.__version__}")
    except AttributeError:
        typer.echo("MCG Agent version: 1.0.0")

if __name__ == "__main__":
    app()