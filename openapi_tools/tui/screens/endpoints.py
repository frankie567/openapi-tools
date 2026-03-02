from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Footer, Header

from ..._parser import NamedSchema, OpenAPIParser
from .._diff_service import DiffService
from ..widgets.endpoints_detail import EndpointDetail
from ..widgets.endpoints_list import EndpointsList
from ..widgets.schemas_list import SchemaDetail


class EndpointsScreen(Screen[None]):
    """Screen for browsing API endpoints."""

    CSS = """
    EndpointsScreen {
        layout: horizontal;
    }
    #endpoints-right {
        layout: vertical;
        width: 2fr;
        height: 1fr;
    }
    #endpoint-schema-panel {
        display: none;
        width: 1fr;
        height: 1fr;
        margin-top: 1;
    }
    """

    def __init__(self, openapi: OpenAPIParser, diff_service: DiffService) -> None:
        super().__init__()
        self.openapi = openapi
        self.diff_service = diff_service

    def compose(self) -> ComposeResult:
        yield Header()
        yield EndpointsList(self.openapi, self.diff_service)
        with Container(id="endpoints-right"):
            yield EndpointDetail(self.diff_service)
            yield SchemaDetail(
                self.openapi,
                in_endpoint_screen=True,
                diff_service=self.diff_service,
                id="endpoint-schema-panel",
            )
        yield Footer()

    def action_view_schema(self, name: str) -> None:
        schema: NamedSchema | None = next(
            (s for s in self.openapi.schemas if s[0] == name), None
        )
        if schema is None:
            self.app.notify(f"Schema '{name}' not found", severity="warning")
            return
        panel = self.query_one("#endpoint-schema-panel", SchemaDetail)
        panel.display = True
        panel.navigate_to(schema)
        self.call_after_refresh(panel.focus)

    def on_schema_detail_panel_closed(self, _event: SchemaDetail.PanelClosed) -> None:
        try:
            self.query_one(EndpointDetail).focus()
        except Exception:
            pass

    def on_endpoints_list_endpoint_selected(
        self, event: EndpointsList.EndpointSelected
    ) -> None:
        panel = self.query_one("#endpoint-schema-panel", SchemaDetail)
        if panel.display:
            panel.display = False
            panel.reset()
        self.query_one(EndpointDetail).show_endpoint(self.openapi, event.endpoint)

    def reload(self, openapi: OpenAPIParser) -> None:
        self.openapi = openapi
        self.query_one(EndpointsList).reload(openapi)
        self.query_one(EndpointDetail).reset()
        self.query_one("#endpoint-schema-panel", SchemaDetail).reload(openapi)

    def apply_diff_filtering(self) -> None:
        """Apply diff filtering to the endpoints list."""
        self.query_one(EndpointsList).apply_diff_filtering()
