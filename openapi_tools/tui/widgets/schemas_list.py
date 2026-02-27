"""Schemas list and schema detail widgets."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

import openapi_pydantic.v3.v3_0 as _v30
import openapi_pydantic.v3.v3_1 as _v31
from textual.app import ComposeResult
from textual.binding import Binding
from textual.message import Message
from textual.widget import Widget
from textual.widgets import ListItem, ListView, Markdown, Static

from ..._parser import NamedSchema, OpenAPIParser, Schema

_REFERENCE_TYPES = (_v30.Reference, _v31.Reference)


@runtime_checkable
class _SchemaLinkRouter(Protocol):
    def action_view_schema(self, name: str) -> None: ...


def _schema_type_markup(schema: _v30.Schema | _v31.Schema) -> str:
    if schema.allOf:
        return "[dim]allOf[/dim]"
    if schema.oneOf:
        return "[dim]oneOf[/dim]"
    if schema.anyOf:
        return "[dim]anyOf[/dim]"
    t = schema.type
    if t is None:
        return "[dim]any[/dim]"

    t = t[0] if isinstance(t, list) else t
    type_str = t.value if t else "object"
    return f"[dim]{type_str}[/dim]"


def _prop_type_str(
    openapi: OpenAPIParser,
    prop_schema: _v30.Reference | _v31.Reference | _v30.Schema | _v31.Schema,
) -> str:
    if isinstance(prop_schema, _REFERENCE_TYPES):
        ref_name = prop_schema.ref.split("/")[-1]
        return f"[{ref_name}](schema:{ref_name})"

    if prop_schema.allOf:
        parts = [_prop_type_str(openapi, s) for s in prop_schema.allOf]
        return "allOf(" + ", ".join(parts) + ")"
    if prop_schema.oneOf:
        parts = [_prop_type_str(openapi, s) for s in prop_schema.oneOf]
        return "oneOf(" + ", ".join(parts) + ")"
    if prop_schema.anyOf:
        parts = [_prop_type_str(openapi, s) for s in prop_schema.anyOf]
        return "anyOf(" + ", ".join(parts) + ")"

    t = prop_schema.type
    t = t[0] if isinstance(t, list) else t

    if t is not None and t.value == "array":
        items = prop_schema.items
        if items is None:
            return "array"
        if isinstance(items, _REFERENCE_TYPES):
            item_name = items.ref.split("/")[-1]
            return f"array of [{item_name}](schema:{item_name})"
        item_type = items.type
        if item_type is None:
            return "array"
        item_type = item_type[0] if isinstance(item_type, list) else item_type
        return f"array of `{item_type.value}`"

    if t is None:
        return "*unspecified*"

    fmt = prop_schema.schema_format
    return f"`{t.value}`" + (f" ({fmt})" if fmt else "")


def _prop_constraints(schema: Schema) -> str:
    parts: list[str] = []
    if schema.minimum is not None:
        parts.append(f"min: {schema.minimum}")
    if schema.maximum is not None:
        parts.append(f"max: {schema.maximum}")
    if schema.exclusiveMinimum is not None:
        parts.append(f"excl. min: {schema.exclusiveMinimum}")
    if schema.exclusiveMaximum is not None:
        parts.append(f"excl. max: {schema.exclusiveMaximum}")
    if schema.multipleOf is not None:
        parts.append(f"multiple of: {schema.multipleOf}")
    if schema.minLength is not None:
        parts.append(f"minLen: {schema.minLength}")
    if schema.maxLength is not None:
        parts.append(f"maxLen: {schema.maxLength}")
    if schema.pattern is not None:
        parts.append(f"pattern: `{schema.pattern}`")
    if schema.minItems is not None:
        parts.append(f"minItems: {schema.minItems}")
    if schema.maxItems is not None:
        parts.append(f"maxItems: {schema.maxItems}")
    if schema.uniqueItems:
        parts.append("unique")
    if schema.enum:
        values = ", ".join(f"`{v}`" for v in schema.enum)
        parts.append(f"enum: {values}")
    return ", ".join(parts)


def _schema_to_markdown(
    openapi: OpenAPIParser, schema: _v30.Schema | _v31.Schema
) -> str:
    """Render a Schema as Markdown content."""
    lines: list[str] = []

    if schema.description:
        lines.append(schema.description.strip())
        lines.append("")

    properties = schema.properties or {}
    required_fields = set(schema.required or [])

    if properties:
        lines.append("### Properties")
        lines.append("")
        lines.append("| Property | Req | Type | Constraints | Description |")
        lines.append("| --- | --- | --- | --- | --- |")
        for prop_name, prop_schema in properties.items():
            req = "✱" if prop_name in required_fields else ""
            type_str = _prop_type_str(openapi, prop_schema)

            resolved_schema: Schema
            if isinstance(prop_schema, _REFERENCE_TYPES):
                resolved_schema = openapi.resolve_reference(prop_schema)
            else:
                resolved_schema = prop_schema

            constraints = _prop_constraints(resolved_schema)
            desc = (
                (resolved_schema.description or "")
                .replace("|", "\\|")
                .replace("\n", " ")
                .strip()
            )
            lines.append(
                f"| **{prop_name}** | {req} | {type_str} | {constraints} | {desc} |"
            )
        lines.append("")

    for combiner_name, combiner_list in [
        ("allOf", schema.allOf),
        ("oneOf", schema.oneOf),
        ("anyOf", schema.anyOf),
    ]:
        if not combiner_list:
            continue
        lines.append(f"### {combiner_name}")
        lines.append("")
        for sub in combiner_list:
            if isinstance(sub, _REFERENCE_TYPES):
                ref_name = sub.ref.split("/")[-1]
                lines.append(f"- [{ref_name}](schema:{ref_name})")
            else:
                t = sub.type
                t = t[0] if isinstance(t, list) else t
                lines.append(f"- `{t.value if t else 'any'}`")
        lines.append("")

    if schema.enum:
        lines.append("### Enum Values")
        lines.append("")
        for val in schema.enum:
            lines.append(f"- `{val}`")
        lines.append("")

    if not lines:
        return "*No details available*"

    return "\n".join(lines)


class SchemaItem(ListItem):
    """A list item representing a single schema."""

    DEFAULT_CSS = """
    SchemaItem {
        padding: 0 1;
    }
    SchemaItem:hover {
        background: $accent 15%;
    }
    SchemaItem.--highlight {
        background: $accent 25%;
    }
    """

    def __init__(self, schema: NamedSchema) -> None:
        super().__init__()
        self.schema = schema

    def compose(self) -> ComposeResult:
        name, schema = self.schema
        type_markup = (
            _schema_type_markup(schema)
            if isinstance(schema, (_v30.Schema, _v31.Schema))
            else ""
        )
        yield Static(
            f"[bold]{name}[/bold]  {type_markup}",
            markup=True,
        )


class SchemaDetail(Widget):
    """Shows the details of a selected schema, with navigation history."""

    can_focus = True

    BINDINGS = [
        Binding("b", "back", "← Back", show=False),
    ]

    DEFAULT_CSS = """
    SchemaDetail {
        width: 2fr;
        height: 1fr;
        border: round $primary-darken-2;
        overflow-y: auto;
    }
    SchemaDetail #schema-placeholder {
        height: 1fr;
        content-align: center middle;
        color: $text-muted;
    }
    SchemaDetail Markdown {
        background: transparent;
        padding: 1 2;
        display: none;
    }
    """

    class PanelClosed(Message):
        """Posted when the endpoint-schema panel is closed via back."""

    def __init__(
        self,
        openapi: OpenAPIParser,
        in_endpoint_screen: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.openapi = openapi
        self.in_endpoint_screen = in_endpoint_screen
        self._schema: NamedSchema | None = None
        self._history: list[NamedSchema] = []

    def on_mount(self) -> None:
        self.border_title = "Schema"

    def compose(self) -> ComposeResult:
        yield Static(
            "[dim]Select a schema from the list[/dim]",
            id="schema-placeholder",
            markup=True,
        )
        yield Markdown("", id="schema-markdown", open_links=False)

    def on_markdown_link_clicked(self, event: Markdown.LinkClicked) -> None:
        """Route schema: links to the appropriate panel."""
        if event.href.startswith("schema:"):
            schema_name = event.href[len("schema:") :]
            screen = self.screen
            if isinstance(screen, _SchemaLinkRouter):
                screen.action_view_schema(schema_name)
            event.prevent_default()

    def show_schema(self, schema: NamedSchema) -> None:
        """Navigate directly (clears history — used by SchemasList selection)."""
        self._history.clear()
        self._schema = schema
        self._refresh_display()

    def reload(self, openapi: OpenAPIParser) -> None:
        self.openapi = openapi
        self.reset()

    def reset(self) -> None:
        """Clear history and current schema (used when closing the panel)."""
        self._history.clear()
        self._schema = None
        self.border_title = "Schema"
        self.border_subtitle = ""
        self.query_one("#schema-placeholder").display = True
        self.query_one("#schema-markdown", Markdown).display = False

    def navigate_to(self, schema: NamedSchema) -> None:
        """Navigate to schema while pushing the current one onto history."""
        if self._schema is not None:
            self._history.append(self._schema)
        self._schema = schema
        self._refresh_display()

    def action_back(self) -> None:
        """Go back in history, or close/clear the panel if history is empty."""
        if self._history:
            self._schema = self._history.pop()
            self._refresh_display()
        elif self.in_endpoint_screen:
            self._schema = None
            self.display = False
            self.border_subtitle = ""
            self.post_message(self.PanelClosed())

    def _refresh_display(self) -> None:
        if self._schema is None:
            return

        name, schema = self._schema

        self.query_one("#schema-placeholder").display = False

        type_markup = (
            _schema_type_markup(schema)
            if isinstance(schema, (_v30.Schema, _v31.Schema))
            else ""
        )
        self.border_title = f"[bold]{name}[/bold] {type_markup}"
        if self._history:
            trail = " › ".join(s[0] for s in self._history) + f" › {name}"
            self.border_subtitle = f"{trail}  b: back"
        elif self.in_endpoint_screen:
            self.border_subtitle = f"{name}  b: close"
        else:
            self.border_subtitle = ""

        md = self.query_one("#schema-markdown", Markdown)
        md.display = True
        if isinstance(schema, (_v30.Schema, _v31.Schema)):
            md.update(_schema_to_markdown(self.openapi, schema))


class SchemasList(Widget):
    """Widget showing all schemas from the OpenAPI spec."""

    DEFAULT_CSS = """
    SchemasList {
        width: 1fr;
        height: 1fr;
        border: round $primary-darken-2;
        margin: 0 1 0 0;
    }
    SchemasList > ListView {
        height: 1fr;
        border: none;
        background: $surface;
        padding: 0;
    }
    """

    class SchemaSelected(Message):
        """Posted when the user selects a schema."""

        def __init__(self, schema: NamedSchema) -> None:
            super().__init__()
            self.schema = schema

    def __init__(self, openapi: OpenAPIParser) -> None:
        super().__init__()
        self.openapi = openapi

    def compose(self) -> ComposeResult:
        yield ListView(id="schemas-list")

    def on_mount(self) -> None:
        self.border_title = "Schemas"
        self._rebuild_list()

    def reload(self, openapi: OpenAPIParser) -> None:
        self.openapi = openapi
        self._rebuild_list()

    def _rebuild_list(self) -> None:
        list_view = self.query_one("#schemas-list", ListView)
        list_view.clear()
        for name, schema in self.openapi.schemas:
            list_view.append(SchemaItem((name, schema)))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if isinstance(event.item, SchemaItem):
            self.post_message(self.SchemaSelected(event.item.schema))

    def select_schema(self, name: str) -> None:
        """Move the list cursor to the schema with the given name (if visible)."""
        list_view = self.query_one("#schemas-list", ListView)
        for idx, item in enumerate(list_view.children):
            if isinstance(item, SchemaItem) and item.schema[0] == name:
                list_view.index = idx
                break
