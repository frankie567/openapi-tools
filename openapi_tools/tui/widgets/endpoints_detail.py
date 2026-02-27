from typing import Protocol, cast, runtime_checkable

import openapi_pydantic.v3.v3_0 as _v30
import openapi_pydantic.v3.v3_1 as _v31
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Markdown, Static, TabbedContent, TabPane

from openapi_tools.tui._utils import get_method_color

from ..._parser import (
    Endpoint,
    Method,
    OpenAPIParser,
    Parameter,
    RequestBody,
    Response,
    Responses,
    Schema,
)

_REFERENCE_TYPES = (_v30.Reference, _v31.Reference)


@runtime_checkable
class _SchemaLinkRouter(Protocol):
    def action_view_schema(self, name: str) -> None: ...


def _method_markup_title(method: Method) -> str:
    color = get_method_color(method)
    return f"[bold {color}]{method.upper()}[/]"


def _schema_summary_md(schema: Schema | _v30.Reference | _v31.Reference | None) -> str:
    if schema is None:
        return "any"
    if isinstance(schema, _REFERENCE_TYPES):
        name = schema.ref.split("/")[-1]
        return f"[{name}](schema:{name})"

    if schema.enum:
        values = ", ".join(f"`{v}`" for v in schema.enum)
        return f"enum({values})"
    if schema.allOf:
        return "allOf(" + ", ".join(_schema_summary_md(s) for s in schema.allOf) + ")"
    if schema.oneOf:
        return "oneOf(" + ", ".join(_schema_summary_md(s) for s in schema.oneOf) + ")"
    if schema.anyOf:
        return "anyOf(" + ", ".join(_schema_summary_md(s) for s in schema.anyOf) + ")"

    t = schema.type
    if t is None:
        return "any"

    t = t[0] if isinstance(t, list) else t

    if t.value == "array":
        return f"array of {_schema_summary_md(schema.items)}"
    if t.value == "object" or schema.properties:
        return "object"
    return f"`{t.value}`"


def _render_info_md(endpoint: Endpoint) -> str:
    _, _, operation = endpoint
    lines: list[str] = []
    if operation.description:
        lines.append(operation.description.strip())
        lines.append("")
    if operation.operationId:
        lines.append(f"**Endpoint ID:** `{operation.operationId}`  ")
    if operation.tags:
        lines.append(f"**Tags:** {', '.join(f'`{t}`' for t in operation.tags)}  ")
    if operation.deprecated:
        lines.append("")
        lines.append("**⚠ DEPRECATED**")
    if not lines:
        return "*No additional information available*"
    return "\n".join(lines)


def _render_parameters_md(
    openapi: OpenAPIParser,
    parameters: list[Parameter | _v30.Reference | _v31.Reference] | None,
    location: str,
) -> str:
    matching_parameters: list[Parameter] = []
    for parameter in parameters or []:
        resolved_parameter: Parameter
        if isinstance(parameter, _REFERENCE_TYPES):
            resolved_parameter = openapi.resolve_reference(parameter)
        else:
            resolved_parameter = parameter
        if resolved_parameter.param_in.value == location:
            matching_parameters.append(resolved_parameter)

    if not matching_parameters:
        return f"*No {location} parameters*"
    lines = [
        "| Name | Req | Type | Description |",
        "| --- | --- | --- | --- |",
    ]
    for parameter in matching_parameters:
        req = "✱" if parameter.required else ""
        type_str = _schema_summary_md(parameter.param_schema)
        desc = (
            (parameter.description or "").replace("|", "\\|").replace("\n", " ").strip()
        )
        lines.append(f"| `{parameter.name}` | {req} | {type_str} | {desc} |")
    return "\n".join(lines)


def _render_responses_md(openapi: OpenAPIParser, responses: Responses | None) -> str:
    if not responses:
        return "*No responses defined*"
    lines = [
        "| Code | Description | Content Type | Schema |",
        "| --- | --- | --- | --- |",
    ]
    for code, response in responses.items():
        resolved_response: Response
        if isinstance(response, _REFERENCE_TYPES):
            resolved_response = openapi.resolve_reference(response)
        else:
            resolved_response = response

        desc = (
            (resolved_response.description or "")
            .replace("|", "\\|")
            .replace("\n", " ")
            .strip()
        )
        if not resolved_response.content:
            lines.append(f"| **{code}** | {desc} | | |")
        else:
            for media_type, media_obj in resolved_response.content.items():
                schema = media_obj.media_type_schema
                schema_str = _schema_summary_md(schema) if schema else ""
                mt = media_type.replace("|", "\\|")
                lines.append(f"| **{code}** | {desc} | `{mt}` | {schema_str} |")
    return "\n".join(lines)


def _render_request_body_md(
    openapi: OpenAPIParser,
    request_body: RequestBody | _v30.Reference | _v31.Reference | None,
) -> str:
    if request_body is None:
        return "*No request body*"

    resolved_request_body: RequestBody
    if isinstance(request_body, _REFERENCE_TYPES):
        resolved_request_body = openapi.resolve_reference(request_body)
    else:
        resolved_request_body = request_body

    lines: list[str] = []
    if resolved_request_body.description:
        lines.append(resolved_request_body.description)
        lines.append("")
    if resolved_request_body.required:
        lines.append("**Required**")
        lines.append("")
    for media_type, media_obj in (resolved_request_body.content or {}).items():
        schema = media_obj.media_type_schema
        lines.append(f"**{media_type}**")
        lines.append("")
        if schema:
            lines.append(_schema_summary_md(schema))
            lines.append("")
    return "\n".join(lines) if lines else "*No request body*"


class EndpointDetail(Widget):
    """Right-panel widget showing details for a selected endpoint."""

    DEFAULT_CSS = """
    EndpointDetail {
        width: 1fr;
        height: 1fr;
        border: round $primary-darken-2;
    }
    EndpointDetail #endpoint-placeholder {
        height: 1fr;
        content-align: center middle;
        color: $text-muted;
    }
    EndpointDetail TabbedContent {
        height: 1fr;
        display: none;
    }
    EndpointDetail TabbedContent.-has-endpoint {
        display: block;
    }
    EndpointDetail TabPane {
        padding: 1 2;
        overflow-y: auto;
    }
    EndpointDetail Markdown {
        background: transparent;
        height: auto;
    }
    """

    def on_mount(self) -> None:
        self.border_title = "Endpoint"

    def compose(self) -> ComposeResult:
        yield Static(
            "[dim]Select an endpoint from the list[/dim]",
            id="endpoint-placeholder",
            markup=True,
        )
        with TabbedContent(id="endpoint-tabs"):
            with TabPane("Info", id="tab-info"):
                yield Markdown("", id="tab-info-content", open_links=False)
            with TabPane("Path", id="tab-path"):
                yield Markdown("", id="tab-path-content", open_links=False)
            with TabPane("Query", id="tab-query"):
                yield Markdown("", id="tab-query-content", open_links=False)
            with TabPane("Headers", id="tab-headers"):
                yield Markdown("", id="tab-headers-content", open_links=False)
            with TabPane("Body", id="tab-body"):
                yield Markdown("", id="tab-body-content", open_links=False)
            with TabPane("Responses", id="tab-responses"):
                yield Markdown("", id="tab-responses-content", open_links=False)

    def on_markdown_link_clicked(self, event: Markdown.LinkClicked) -> None:
        """Route schema: links to the schema panel."""
        if event.href.startswith("schema:"):
            schema_name = event.href[len("schema:") :]
            screen = self.screen
            if isinstance(screen, _SchemaLinkRouter):
                screen.action_view_schema(schema_name)
            event.prevent_default()

    def reset(self) -> None:
        self.border_title = "Endpoint"
        self.border_subtitle = ""
        self.query_one("#endpoint-placeholder").display = True
        tabs = self.query_one("#endpoint-tabs", TabbedContent)
        tabs.remove_class("-has-endpoint")

    def show_endpoint(self, openapi: OpenAPIParser, endpoint: Endpoint) -> None:
        """Update the panel to show details for the given endpoint."""
        path, method, operation = endpoint

        deprecated = (
            "  [bold red][DEPRECATED][/bold red]" if operation.deprecated else ""
        )
        self.border_title = f"{_method_markup_title(method)}  {path}{deprecated}"
        if operation.summary:
            self.border_subtitle = operation.summary

        self.query_one("#endpoint-placeholder").display = False
        tabs = self.query_one("#endpoint-tabs", TabbedContent)
        tabs.add_class("-has-endpoint")

        self.query_one("#tab-info-content", Markdown).update(_render_info_md(endpoint))
        parameters = cast(
            list[Parameter | _v30.Reference | _v31.Reference] | None,
            operation.parameters,
        )
        self.query_one("#tab-path-content", Markdown).update(
            _render_parameters_md(openapi, parameters, "path")
        )
        self.query_one("#tab-query-content", Markdown).update(
            _render_parameters_md(openapi, parameters, "query")
        )
        self.query_one("#tab-headers-content", Markdown).update(
            _render_parameters_md(openapi, parameters, "header")
        )
        self.query_one("#tab-body-content", Markdown).update(
            _render_request_body_md(openapi, operation.requestBody)
        )
        self.query_one("#tab-responses-content", Markdown).update(
            _render_responses_md(openapi, operation.responses)
        )
