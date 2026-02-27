"""CLI entry point for openapi-tools."""

from __future__ import annotations

import sys

import click

from ._parser import OpenAPIParser
from .tui.app import OpenAPITUIApp


@click.group()
@click.version_option()
def main() -> None:
    """Python tools to work with OpenAPI schemas."""


@main.command()
@click.argument("schema", metavar="SCHEMA")
def view(schema: str) -> None:
    """Explore an OpenAPI schema in a terminal UI.

    SCHEMA can be a local file path (JSON or YAML) or a URL.
    """
    try:
        parser = OpenAPIParser.from_source(schema)
    except FileNotFoundError:
        click.echo(f"Error: file not found: {schema}", err=True)
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        click.echo(f"Error loading schema: {exc}", err=True)
        sys.exit(1)

    app = OpenAPITUIApp(parser, source=schema)
    app.run()
