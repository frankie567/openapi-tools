"""CLI entry point for openapi-tools."""

from __future__ import annotations

import sys

import click

from ._diff import compare, to_json, to_markdown
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


@main.command()
@click.argument("base_schema", metavar="BASE")
@click.argument("head_schema", metavar="HEAD")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "markdown"], case_sensitive=False),
    default="markdown",
    show_default=True,
    help="Output format.",
)
def diff(base_schema: str, head_schema: str, output_format: str) -> None:
    """Compare two OpenAPI schemas and output the differences.

    BASE and HEAD can each be a local file path (JSON or YAML) or a URL.
    """
    try:
        base_parser = OpenAPIParser.from_source(base_schema)
    except FileNotFoundError:
        click.echo(f"Error: file not found: {base_schema}", err=True)
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        click.echo(f"Error loading base schema: {exc}", err=True)
        sys.exit(1)

    try:
        head_parser = OpenAPIParser.from_source(head_schema)
    except FileNotFoundError:
        click.echo(f"Error: file not found: {head_schema}", err=True)
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        click.echo(f"Error loading head schema: {exc}", err=True)
        sys.exit(1)

    result = compare(base_parser, head_parser)

    if output_format == "json":
        click.echo(to_json(result))
    else:
        click.echo(to_markdown(result))
