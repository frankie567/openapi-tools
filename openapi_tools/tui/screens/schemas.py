from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Footer, Header

from ..._parser import NamedSchema, OpenAPIParser
from .._diff_service import DiffService
from ..widgets.schemas_list import SchemaDetail, SchemasList


class SchemasScreen(Screen[None]):
    """Screen for browsing API schemas."""

    CSS = """
    SchemasScreen {
        layout: horizontal;
    }
    """

    def __init__(self, openapi: OpenAPIParser, diff_service: DiffService) -> None:
        super().__init__()
        self.openapi = openapi
        self.diff_service = diff_service

    def compose(self) -> ComposeResult:
        yield Header()
        yield SchemasList(self.openapi, self.diff_service)
        yield SchemaDetail(
            self.openapi, diff_service=self.diff_service, id="schemas-panel"
        )
        yield Footer()

    def action_view_schema(self, name: str) -> None:
        schema: NamedSchema | None = next(
            (s for s in self.openapi.schemas if s[0] == name), None
        )
        if schema is None:
            self.app.notify(f"Schema '{name}' not found", severity="warning")
            return
        detail = self.query_one("#schemas-panel", SchemaDetail)
        detail.navigate_to(schema)
        self.query_one(SchemasList).select_schema(name)

    def on_schemas_list_schema_selected(
        self, event: SchemasList.SchemaSelected
    ) -> None:
        self.query_one("#schemas-panel", SchemaDetail).show_schema(event.schema)

    def reload(self, openapi: OpenAPIParser) -> None:
        self.openapi = openapi
        self.query_one(SchemasList).reload(openapi)
        self.query_one("#schemas-panel", SchemaDetail).reload(openapi)

    def apply_diff_filtering(self) -> None:
        """Apply diff filtering to the schemas list."""
        self.query_one(SchemasList).apply_diff_filtering()
