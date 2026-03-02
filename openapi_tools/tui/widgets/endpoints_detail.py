from typing import Protocol, cast, runtime_checkable

import openapi_pydantic.v3.v3_0 as _v30
import openapi_pydantic.v3.v3_1 as _v31
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Markdown, Static, TabbedContent, TabPane

from openapi_tools.tui._utils import get_method_color

from ..._diff import ChangeType
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
from .._diff_service import DiffService

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
    diff_service: DiffService,
    parameters: list[Parameter | _v30.Reference | _v31.Reference] | None,
    location: str,
    endpoint: Endpoint | None = None,
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

    # Get parameter changes if diff is available
    param_changes = {}
    if endpoint and diff_service.is_diff_available():
        endpoint_changes = diff_service.get_endpoint_changes(endpoint)
        if endpoint_changes:
            for pc in endpoint_changes.parameter_changes:
                if pc.location == location:
                    param_changes[pc.name] = pc

    for parameter in matching_parameters:
        param_change = param_changes.get(parameter.name)

        # Apply diff highlighting
        name_color = ""
        if param_change:
            if param_change.change_type == ChangeType.ADDED:
                name_color = "green"
            elif param_change.change_type == ChangeType.REMOVED:
                name_color = "red"
            elif param_change.change_type == ChangeType.MODIFIED:
                name_color = "orange"

        name_markup = (
            f"[{name_color}]{parameter.name}[/{name_color}]"
            if name_color
            else f"`{parameter.name}`"
        )

        req = "✱" if parameter.required else ""
        type_str = _schema_summary_md(parameter.param_schema)
        desc = (
            (parameter.description or "").replace("|", "\\|").replace("\n", " ").strip()
        )

        # Add change indicator for modified parameters
        change_indicator = ""
        if param_change and param_change.change_type == ChangeType.MODIFIED:
            change_details = []
            for fc in param_change.field_changes:
                if fc.field == "required":
                    change_details.append(f"required: {fc.old_value} → {fc.new_value}")
                elif fc.field == "description":
                    change_details.append("description changed")
                elif fc.field.startswith("schema."):
                    change_details.append(f"type: {fc.old_value} → {fc.new_value}")
            if change_details:
                change_indicator = f"  ([orange]{', '.join(change_details)}[/orange])"

        lines.append(
            f"| {name_markup} | {req} | {type_str} | {desc}{change_indicator} |"
        )
    return "\n".join(lines)


def _render_responses_md(
    openapi: OpenAPIParser,
    diff_service: DiffService,
    responses: Responses | None,
    endpoint: Endpoint | None = None,
) -> str:
    if not responses:
        return "*No responses defined*"
    lines = [
        "| Code | Description | Content Type | Schema |",
        "| --- | --- | --- | --- |",
    ]

    # Get response changes if diff is available
    response_changes = {}
    if diff_service and endpoint and diff_service.is_diff_available():
        endpoint_changes = diff_service.get_endpoint_changes(endpoint)
        if endpoint_changes:
            for rc in endpoint_changes.response_changes:
                response_changes[rc.status_code] = rc

    for code, response in responses.items():
        resolved_response: Response
        if isinstance(response, _REFERENCE_TYPES):
            resolved_response = openapi.resolve_reference(response)
        else:
            resolved_response = response

        # Apply diff highlighting
        code_color = ""
        response_change = response_changes.get(code)
        if response_change:
            if response_change.change_type == ChangeType.ADDED:
                code_color = "green"
            elif response_change.change_type == ChangeType.REMOVED:
                code_color = "red"
            elif response_change.change_type == ChangeType.MODIFIED:
                code_color = "orange"

        code_markup = (
            f"[{code_color}]{code}[/{code_color}]" if code_color else f"**{code}**"
        )

        desc = (
            (resolved_response.description or "")
            .replace("|", "\\|")
            .replace("\n", " ")
            .strip()
        )

        # Add change indicator for modified responses
        change_indicator = ""
        if (
            response_change is not None
            and response_change.change_type == ChangeType.MODIFIED
        ):
            change_details = []
            for fc in response_change.field_changes:
                if fc.field == "description":
                    change_details.append("description changed")
                elif fc.field.startswith("content."):
                    change_details.append("content type changed")
                elif fc.field.endswith(".schema"):
                    change_details.append("schema changed")
            if change_details:
                change_indicator = f"  ([orange]{', '.join(change_details)}[/orange])"

        if not resolved_response.content:
            lines.append(f"| {code_markup} | {desc} | | {change_indicator}")
        else:
            for media_type, media_obj in resolved_response.content.items():
                schema = media_obj.media_type_schema
                schema_str = _schema_summary_md(schema) if schema else ""
                mt = media_type.replace("|", "\\|")
                lines.append(
                    f"| {code_markup} | {desc} | `{mt}` | {schema_str} {change_indicator}"
                )
    return "\n".join(lines)


def _render_request_body_md(
    openapi: OpenAPIParser,
    diff_service: DiffService,
    request_body: RequestBody | _v30.Reference | _v31.Reference | None,
    endpoint: Endpoint | None = None,
) -> str:
    if request_body is None:
        return "*No request body*"

    resolved_request_body: RequestBody
    if isinstance(request_body, _REFERENCE_TYPES):
        resolved_request_body = openapi.resolve_reference(request_body)
    else:
        resolved_request_body = request_body

    # Get request body changes if diff is available
    rb_change = None
    if endpoint and diff_service.is_diff_available():
        endpoint_changes = diff_service.get_endpoint_changes(endpoint)
        if endpoint_changes and endpoint_changes.request_body_change:
            rb_change = endpoint_changes.request_body_change

    lines: list[str] = []

    # Add diff indicator
    if rb_change and diff_service is not None:
        icon = diff_service.get_change_icon(rb_change.change_type)
        lines.append(f"{icon} **Request Body**")
        lines.append("")

    if resolved_request_body.description:
        lines.append(resolved_request_body.description)
        lines.append("")
    if resolved_request_body.required:
        lines.append("**Required**")
        lines.append("")

    # Add change details for modified request bodies
    if rb_change and rb_change.change_type == ChangeType.MODIFIED:
        change_details = []
        for fc in rb_change.field_changes:
            if fc.field == "required":
                change_details.append(f"required: {fc.old_value} → {fc.new_value}")
            elif fc.field == "description":
                change_details.append("description changed")
            elif fc.field.startswith("content."):
                change_details.append(f"content type: {fc.old_value} → {fc.new_value}")
        if change_details:
            lines.append(f"[orange]Changes: {', '.join(change_details)}[/orange]")
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

    def __init__(self, diff_service: DiffService) -> None:
        super().__init__()
        self.diff_service = diff_service

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

        # Add diff indicator if available
        diff_indicator = ""
        if self.diff_service.is_diff_available():
            change_type = self.diff_service.get_endpoint_change_type(endpoint)
            if change_type:
                icon = self.diff_service.get_change_icon(change_type)
                diff_indicator = f"  {icon}"

        self.border_title = (
            f"{_method_markup_title(method)}  {path}{deprecated}{diff_indicator}"
        )
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
            _render_parameters_md(
                openapi, self.diff_service, parameters, "path", endpoint
            )
        )
        self.query_one("#tab-query-content", Markdown).update(
            _render_parameters_md(
                openapi, self.diff_service, parameters, "query", endpoint
            )
        )
        self.query_one("#tab-headers-content", Markdown).update(
            _render_parameters_md(
                openapi, self.diff_service, parameters, "header", endpoint
            )
        )
        self.query_one("#tab-body-content", Markdown).update(
            _render_request_body_md(
                openapi, self.diff_service, operation.requestBody, endpoint
            )
        )
        self.query_one("#tab-responses-content", Markdown).update(
            _render_responses_md(
                openapi, self.diff_service, operation.responses, endpoint
            )
        )
