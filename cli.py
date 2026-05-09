from __future__ import annotations

import asyncio
import json
import os
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

from backend.extractor_replay import replay_fixture, test_platform_fixtures
from backend.indexer import IndexerService
from backend.interest import InterestEngine
from backend.llm_clients import (
    GROQ_MODEL,
    GEMINI_MODEL,
    check_gemini_connectivity,
    check_groq_connectivity,
    providers_snapshot,
)
from backend.doctor import run_doctor
from backend.migrate import run_migrations
from backend.native_accel import status as native_status
from backend.runtime_config import is_public_bind_host, load_runtime_config
from backend.searcher import Searcher
from backend.store import DATA_DIR, Store
from memoryfeed.__version__ import __version__

console = Console()


def _validate_public_bind_or_exit(host: str, port: int) -> None:
    cfg = load_runtime_config()
    if not is_public_bind_host(host):
        return
    if not cfg.public_mode:
        console.print("[red]Refusing public bind while MEMORYFEED_PUBLIC_MODE is false.[/red]")
        console.print("Set MEMORYFEED_PUBLIC_MODE=true and retry.")
        sys.exit(1)
    if not cfg.admin_token:
        console.print("[red]Refusing public bind without MEMORYFEED_ADMIN_TOKEN.[/red]")
        console.print("Set MEMORYFEED_ADMIN_TOKEN to a long random value and retry.")
        sys.exit(1)
    os.environ["MEMORYFEED_BIND_HOST"] = host
    os.environ["MEMORYFEED_BIND_PORT"] = str(port)


@click.group()
def cli() -> None:
    """MemoryFeed CLI."""


@cli.command()
@click.option("--host", default="127.0.0.1", show_default=True)
@click.option("--port", default=7749, show_default=True, type=int)
def serve(host: str, port: int) -> None:
    """Start backend server."""
    _validate_public_bind_or_exit(host, port)
    os.environ["MEMORYFEED_BIND_HOST"] = host
    os.environ["MEMORYFEED_BIND_PORT"] = str(port)
    uvicorn.run("backend.server:app", host=host, port=port, reload=False)


@cli.command("serve-web")
@click.option("--host", default="0.0.0.0", show_default=True)
@click.option("--port", default=7749, show_default=True, type=int)
@click.option("--skip-frontend-install", is_flag=True, help="Skip npm install in frontend/")
@click.option("--skip-build", is_flag=True, help="Skip frontend build step")
def serve_web(host: str, port: int, skip_frontend_install: bool, skip_build: bool) -> None:
    """Build frontend and serve public web app via FastAPI."""
    _validate_public_bind_or_exit(host, port)
    os.environ["MEMORYFEED_BIND_HOST"] = host
    os.environ["MEMORYFEED_BIND_PORT"] = str(port)
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


@cli.command("migrate")
@click.option("--target-version", default=None, type=int, help="Run migrations up to target version")
def migrate_command(target_version: int | None) -> None:
    """Run schema migrations."""
    report = run_migrations(target_version=target_version)
    table = Table(title="MemoryFeed Migrations")
    table.add_column("Before")
    table.add_column("After")
    table.add_column("Latest")
    table.add_row(str(report["before"]), str(report["after"]), str(report["latest"]))
    console.print(table)
    if report["applied"]:
        for step in report["applied"]:
            console.print(f"- applied #{step['revision']}: {step['name']}")
    else:
        console.print("No pending migrations.")


@cli.command("replay")
@click.argument("fixture_html", type=click.Path(exists=True, dir_okay=False))
@click.option("--expected", "expected_snapshot", default=None, help="Optional expected snapshot JSON")
@click.option("--json-output", is_flag=True, help="Print JSON output")
def replay_command(fixture_html: str, expected_snapshot: str | None, json_output: bool) -> None:
    """Replay extractor against saved fixture HTML."""
    result = replay_fixture(fixture_html, expected_snapshot=expected_snapshot)
    payload = {
        "fixture": result.fixture,
        "platform": result.platform,
        "extracted": result.extracted,
        "selector_used": result.selector_used,
        "missing_fields": result.missing_fields,
        "quality_flags": result.quality_flags,
        "matches_expected": result.matches_expected,
        "mismatch_keys": result.mismatch_keys,
    }
    if json_output:
        console.print_json(json.dumps(payload, ensure_ascii=False))
        return

    console.print(f"fixture: {result.fixture}")
    console.print(f"platform: {result.platform}")
    console.print(f"matches_expected: {result.matches_expected}")
    console.print(f"selector_used: {json.dumps(result.selector_used, ensure_ascii=False)}")
    console.print(f"missing_fields: {', '.join(result.missing_fields) if result.missing_fields else '(none)'}")
    console.print(f"quality_flags: {', '.join(result.quality_flags) if result.quality_flags else '(none)'}")
    console.print(f"extracted: {json.dumps(result.extracted, ensure_ascii=False)}")


@cli.group("extractor")
def extractor_group() -> None:
    """Extractor diagnostics and fixture tests."""


@extractor_group.command("test")
@click.argument("platform", type=click.Choice(["facebook", "twitter", "youtube", "linkedin", "tiktok"], case_sensitive=False))
@click.option("--json-output", is_flag=True, help="Print JSON output")
def extractor_test_command(platform: str, json_output: bool) -> None:
    """Run fixture-based extractor tests by platform."""
    report = test_platform_fixtures(platform.lower())
    if json_output:
        console.print_json(json.dumps(report, ensure_ascii=False))
        return
    console.print(
        f"platform={report['platform']} fixtures={report['fixtures']} passed={report['passed']} failed={report['failed']}"
    )
    for row in report["results"]:
        status = "PASS" if row["matches_expected"] else "FAIL"
        console.print(
            f"[{status}] {Path(str(row['fixture'])).name} missing={row['missing_fields']} mismatch={row['mismatch_keys']}"
        )


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
@click.option("--limit", default=10, show_default=True, type=int)
@click.option(
    "--mode",
    default="default",
    type=click.Choice(["default", "focus", "light", "explore"], case_sensitive=False),
    show_default=True,
)
def feed(limit: int, mode: str) -> None:
    """Show active feed ranked by personal memory heat."""
    store = Store()
    indexer = IndexerService(store)
    searcher = Searcher(store, indexer)
    interest = InterestEngine(store, searcher)

    async def _run() -> list[dict]:
        return await interest.active_feed(limit=limit, mode=mode)

    rows = asyncio.run(_run())
    if not rows:
        console.print("[yellow]No feed items yet.[/yellow]")
        return

    table = Table(title=f"Active Feed ({mode})")
    table.add_column("Heat", style="red")
    table.add_column("Reason", style="cyan")
    table.add_column("Platform")
    table.add_column("Text")
    table.add_column("URL", style="blue")
    for item in rows:
        table.add_row(
            f"{float(item.get('heat', 0.0)):.2f}",
            str(item.get("surface_reason", "")),
            item["platform"],
            (item.get("text_excerpt") or item.get("text_content") or "")[:90],
            item["url"],
        )
    console.print(table)


@cli.command()
@click.argument("context", nargs=1)
@click.option("--limit", default=5, show_default=True, type=int)
@click.option("--no-bump", is_flag=True, help="Return suggestions without updating heat/surfaced metadata")
def resurface(context: str, limit: int, no_bump: bool) -> None:
    """Surface memories related to current context."""
    store = Store()
    indexer = IndexerService(store)
    searcher = Searcher(store, indexer)
    interest = InterestEngine(store, searcher)

    async def _run() -> list[dict]:
        return await interest.resurface_context(context=context, limit=limit, bump_heat=not no_bump)

    rows = asyncio.run(_run())
    if not rows:
        console.print("[yellow]No related memories found.[/yellow]")
        return

    table = Table(title="Resurfaced Memories")
    table.add_column("Heat", style="red")
    table.add_column("Platform")
    table.add_column("Text")
    table.add_column("URL", style="blue")
    for item in rows:
        table.add_row(
            f"{float(item.get('heat', 0.0)):.2f}",
            item["platform"],
            (item.get("text_excerpt") or item.get("text_content") or "")[:100],
            item["url"],
        )
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
    """Check Gemini + Groq provider connectivity."""
    snapshot = providers_snapshot()
    gemini_enabled = bool(snapshot["gemini"]["enabled"])
    groq_enabled = bool(snapshot["groq"]["enabled"])
    gemini_ok, gemini_reason = check_gemini_connectivity(timeout_s=6.0) if gemini_enabled else (True, snapshot["gemini"]["reason"])
    groq_ok, groq_reason = check_groq_connectivity(timeout_s=6.0) if groq_enabled else (True, snapshot["groq"]["reason"])

    table = Table(title="LLM Providers")
    table.add_column("Provider")
    table.add_column("Model")
    table.add_column("Configured")
    table.add_column("Reachable")
    table.add_column("Details")

    table.add_row(
        "Gemini",
        GEMINI_MODEL,
        "yes" if gemini_enabled else "no",
        "yes" if gemini_enabled and gemini_ok else ("n/a" if not gemini_enabled else "no"),
        gemini_reason,
    )
    table.add_row(
        "Groq (Qwen)",
        GROQ_MODEL,
        "yes" if groq_enabled else "no",
        "yes" if groq_enabled and groq_ok else ("n/a" if not groq_enabled else "no"),
        groq_reason,
    )
    console.print(table)


@cli.command()
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"], case_sensitive=False),
    default="text",
    show_default=True,
)
def doctor(output_format: str) -> None:
    """Run local diagnostics for security and runtime readiness."""
    report = run_doctor()
    if output_format.lower() == "json":
        console.print_json(json.dumps(report, ensure_ascii=False))
        return

    console.print(f"[bold]MemoryFeed Doctor[/bold] v{__version__}")
    console.print(f"Status: [cyan]{report['status']}[/cyan]")
    for check in report["checks"]:
        mark = "[green]OK[/green]" if check["ok"] else ("[yellow]WARN[/yellow]" if check["severity"] == "warning" else "[red]FAIL[/red]")
        console.print(f"- {mark} {check['name']}: {check['message']}")
        if (not check["ok"]) and check.get("suggested_fix"):
            console.print(f"  fix: {check['suggested_fix']}")

    cfg = report["config"]
    console.print(
        f"Config: offline_only={cfg['offline_only']} ai_provider={cfg['ai_provider']} "
        f"public_mode={cfg['public_mode']} admin_token_configured={cfg['admin_token_configured']}"
    )


@cli.command()
@click.option("--base-url", default="http://127.0.0.1:7749", show_default=True)
def perf(base_url: str) -> None:
    """Show runtime performance diagnostics from backend."""
    url = base_url.rstrip("/") + "/api/perf"
    try:
        resp = httpx.get(url, timeout=10.0)
        resp.raise_for_status()
    except Exception as exc:
        console.print(f"[red]Cannot read perf endpoint:[/red] {exc}")
        sys.exit(1)

    console.print_json(json.dumps(resp.json(), ensure_ascii=False))


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
