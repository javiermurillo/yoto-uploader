"""Command-line interface for yoto-uploader.

Exposes two main commands:

- ``upload``: create a new playlist and upload local audio files.
- ``icons``: randomize icons for an existing playlist given its edit URL.
"""

from typing import Optional

import typer

from . import __version__
from .workflow import run_playwright


app = typer.Typer(help="CLI helper for uploading audio to Yoto 'My Cards'.")


@app.callback()
def version_callback(  # pragma: no cover - trivial
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        callback=lambda v: _print_version(v),
        is_eager=True,
        help="Show yoto-uploader version and exit.",
    ),
) -> None:
    """Global callback to support ``--version`` flag."""


def _print_version(value: Optional[bool]) -> None:
    if value:
        typer.echo(f"yoto-uploader {__version__}")
        raise typer.Exit()


@app.command()
def upload(
    playlist: str = typer.Option(
        "", "--playlist", "-p", help="Playlist name (will be asked if omitted)."
    ),
    folder: str = typer.Option(
        "",
        "--folder",
        "-f",
        help="Folder containing audio files (will be asked if omitted).",
    ),
    chunk_size: int = typer.Option(
        3,
        "--chunk-size",
        min=1,
        help="Number of files to upload per batch.",
    ),
    # INVERTED LOGIC: Default is headless=True (hidden). Flag is --visible.
    visible: bool = typer.Option(
        False,
        "--visible",
        help="Run browser in visible mode (default is headless).",
    ),
):
    """Upload all audio files in a folder into a new Yoto playlist."""

    # For now we keep prompts inside the workflow; in future we can wire
    # these options to skip interactive inputs.
    _ = playlist
    _ = folder
    
    # run_playwright expects 'headless', so visible=True -> headless=False
    run_playwright(target_url=None, chunk_size=chunk_size, headless=not visible)


@app.command()
def icons(
    url: str = typer.Argument(..., help="Yoto playlist edit URL (…/card/XXXXX/edit)."),
    visible: bool = typer.Option(
        False,
        "--visible",
        help="Run browser in visible mode (default is headless).",
    ),
):
    """Randomize icons for tracks in an existing playlist."""

    run_playwright(target_url=url, headless=not visible)


def main() -> None:  # pragma: no cover - thin wrapper
    app()
