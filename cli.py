from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import click
import httpx
import uvicorn
from rich.console import Console
from rich.prompt import Confirm
from rich.table import Table

from backend.indexer import IndexerService
from backend.native_accel import status as native_status
from backend.searcher import Searcher
from backend.store import DATA_DIR, Store

console = Console()


@click.group()
def cli() -> None:
    """MemoryFeed CLI."""


@cli.command()
@click.option("--host", default="127.0.0.1", show_default=True)
@click.option("--port", default=7749, show_default=True, type=int)
def serve(host: str, port: int) -> None:
    """Start backend server."""
    uvicorn.run("backend.server:app", host=host, port=port, reload=False)


@cli.command("serve-web")
@click.option("--host", default="0.0.0.0", show_default=True)
@click.option("--port", default=7749, show_default=True, type=int)
@click.option("--skip-frontend-install", is_flag=True, help="Skip npm install in frontend/")
@click.option("--skip-build", is_flag=True, help="Skip frontend build step")
def serve_web(host: str, port: int, skip_frontend_install: bool, skip_build: bool) -> None:
    """Build frontend and serve public web app via FastAPI."""
    frontend_dir = Path("frontend")
    if not frontend_dir.exists():
        console.print("[red]Missing frontend directory[/red]")
        sys.exit(1)

    if not skip_frontend_install:
        console.print("[cyan]Installing frontend dependencies...[/cyan]")
        try:
            subprocess.check_call(["npm", "install"], cwd=frontend_dir)
        except FileNotFoundError:
            console.print("[red]npm not found. Install Node.js 20+ first.[/red]")
            sys.exit(1)
        except subprocess.CalledProcessError as exc:
            console.print(f"[red]npm install failed:[/red] {exc}")
            sys.exit(exc.returncode)

    if not skip_build:
        console.print("[cyan]Building frontend (Vite)...[/cyan]")
        try:
            subprocess.check_call(["npm", "run", "build"], cwd=frontend_dir)
        except FileNotFoundError:
            console.print("[red]npm not found. Install Node.js 20+ first.[/red]")
            sys.exit(1)
        except subprocess.CalledProcessError as exc:
            console.print(f"[red]Frontend build failed:[/red] {exc}")
            sys.exit(exc.returncode)

    console.print(f"[green]Serving MemoryFeed at http://{host}:{port}[/green]")
    uvicorn.run("backend.server:app", host=host, port=port, reload=False)


@cli.command("mcp")
@click.option(
    "--transport",
    type=click.Choice(["stdio", "streamable-http", "http", "sse"], case_sensitive=False),
    default="stdio",
    show_default=True,
)
@click.option("--host", default="127.0.0.1", show_default=True)
@click.option("--port", default=7748, show_default=True, type=int)
@click.option("--path", default="/mcp", show_default=True)
def mcp_server(transport: str, host: str, port: int, path: str) -> None:
    """Run MemoryFeed MCP server for Claude/Cursor/agents."""
    try:
        from backend.mcp_server import run_mcp
    except Exception as exc:
        console.print(f"[red]Cannot load MCP server:[/red] {exc}")
        console.print("Install dependency: pip install \"mcp[cli]\"")
        sys.exit(1)

    run_mcp(transport=transport, host=host, port=port, path=path)


@cli.command()
@click.argument("query", nargs=1)
@click.option("--limit", default=10, show_default=True, type=int)
@click.option("--days-back", default=None, type=int)
def search(query: str, limit: int, days_back: int | None) -> None:
    """Search from terminal."""
    store = Store()
    indexer = IndexerService(store)
    searcher = Searcher(store, indexer)

    async def _run() -> list[dict]:
        return await searcher.search(query, limit=limit, days_back=days_back)

    results = asyncio.run(_run())
    if not results:
        console.print("[yellow]No results found.[/yellow]")
        return

    table = Table(title=f"Results: {query}")
    table.add_column("Platform", style="cyan")
    table.add_column("Text", style="white")
    table.add_column("Time", style="green")
    table.add_column("Star")
    table.add_column("URL", style="blue")
    for item in results:
        table.add_row(
            item["platform"],
            (item.get("text_excerpt") or item.get("text_content") or "")[:80],
            item["captured_at"],
            "yes" if item.get("starred") else "no",
            item["url"],
        )
    console.print(table)


@cli.command()
@click.option("--date", "date_str", default=None, help="YYYY-MM-DD")
def timeline(date_str: str | None) -> None:
    """Show captures by date from terminal."""
    selected = date_str or date.today().isoformat()
    store = Store()
    items = store.all_for_timeline(selected)
    if not items:
        console.print(f"[yellow]No data for {selected}[/yellow]")
        return

    table = Table(title=f"Timeline {selected}")
    table.add_column("Time", style="cyan")
    table.add_column("Platform")
    table.add_column("Text")
    table.add_column("Star")
    for item in items[:200]:
        hhmm = item["captured_at"][11:16] if len(item["captured_at"]) >= 16 else "--:--"
        text = (item.get("text_content") or "").replace("\n", " ")[:100]
        table.add_row(hhmm, item["platform"], text, "yes" if item.get("starred") else "no")
    console.print(table)


@cli.command()
@click.option("--platform", default=None, help="Filter by platform")
@click.option("--starred", is_flag=True, help="Only show starred items")
@click.option("--limit", default=30, show_default=True, type=int)
def items(platform: str | None, starred: bool, limit: int) -> None:
    """List recent items."""
    store = Store()
    rows = store.list_items(limit=limit, platform=platform, starred_only=starred)
    if not rows:
        console.print("[yellow]No items.[/yellow]")
        return
    table = Table(title="Recent Items")
    table.add_column("ID")
    table.add_column("Platform")
    table.add_column("Text")
    table.add_column("Star")
    for item in rows:
        table.add_row(item["id"][:8], item["platform"], (item.get("text_content") or "")[:80], "yes" if item.get("starred") else "no")
    console.print(table)


@cli.command()
def stats() -> None:
    """Show statistics."""
    store = Store()
    payload = store.stats()
    payload["native"] = native_status()
    console.print_json(json.dumps(payload, ensure_ascii=False))


@cli.command()
@click.option("--out", "out_file", default=None, help="Output JSON file path")
def export(out_file: str | None) -> None:
    """Export all data to JSON."""
    store = Store()
    items = store.export_items()
    export_dir = DATA_DIR / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    target = Path(out_file) if out_file else export_dir / f"memoryfeed-export-{date.today().isoformat()}.json"
    target.write_text(json.dumps({"items": items}, ensure_ascii=False, indent=2), encoding="utf-8")
    console.print(f"[green]Exported {len(items)} items to {target}[/green]")


@cli.command(name="import")
@click.option("--file", "in_file", required=True, help="Input JSON export file")
def import_items(in_file: str) -> None:
    """Import data from JSON export."""
    path = Path(in_file)
    if not path.exists():
        console.print(f"[red]File not found: {path}[/red]")
        sys.exit(1)
    payload = json.loads(path.read_text(encoding="utf-8"))
    items = payload.get("items", [])
    store = Store()
    inserted = 0
    duplicates = 0
    for item in items:
        ok, _ = store.insert_item(item)
        if ok:
            inserted += 1
        else:
            duplicates += 1
    console.print(f"[green]Import done.[/green] inserted={inserted}, duplicates={duplicates}")


@cli.command()
def reset() -> None:
    """Delete all data with confirmation."""
    if not Confirm.ask("Delete all MemoryFeed data?"):
        console.print("[yellow]Cancelled.[/yellow]")
        return
    store = Store()
    store.delete_all()
    console.print("[green]All data removed.[/green]")


@cli.command()
def models() -> None:
    """Check ollama models availability."""
    try:
        resp = httpx.get("http://localhost:11434/api/tags", timeout=5.0)
        resp.raise_for_status()
    except Exception as exc:
        console.print(f"[red]Cannot connect to Ollama:[/red] {exc}")
        sys.exit(1)

    data = resp.json()
    names = [m.get("name", "") for m in data.get("models", [])]
    required = ["qwen2.5:7b", "llava:7b"]

    table = Table(title="Ollama Models")
    table.add_column("Model")
    table.add_column("Installed")
    for model in required:
        table.add_row(model, "yes" if any(name.startswith(model) for name in names) else "no")
    console.print(table)


@cli.command("build-native")
def build_native() -> None:
    """Build optional C++ acceleration module."""
    build_script = Path("native/build_native.py")
    if not build_script.exists():
        console.print("[red]Missing native/build_native.py[/red]")
        sys.exit(1)
    try:
        subprocess.check_call([sys.executable, str(build_script)])
        console.print("[green]Native module built successfully.[/green]")
    except subprocess.CalledProcessError as exc:
        console.print(f"[red]Native build failed:[/red] {exc}")
        console.print("Install Visual Studio C++ Build Tools on Windows, then retry.")
        sys.exit(exc.returncode)


@cli.command("build-frontend")
def build_frontend() -> None:
    """Build React frontend for production serving via FastAPI."""
    frontend_dir = Path("frontend")
    if not frontend_dir.exists():
        console.print("[red]Missing frontend directory[/red]")
        sys.exit(1)
    try:
        subprocess.check_call(["npm", "run", "build"], cwd=frontend_dir)
        console.print("[green]Frontend built: frontend/dist[/green]")
    except subprocess.CalledProcessError as exc:
        console.print(f"[red]Frontend build failed:[/red] {exc}")
        sys.exit(exc.returncode)


if __name__ == "__main__":
    cli()
