import os

from textual import events
from textual.app import App
from textual.binding import Binding

from .._parser import OpenAPIParser
from ._diff_service import DiffService
from .screens.endpoints import EndpointsScreen
from .screens.schemas import SchemasScreen


class OpenAPITUIApp(App[None]):
    """A TUI application for exploring OpenAPI schemas."""

    TITLE = "openapi-tui"

    BINDINGS = [
        Binding("ctrl+c,q", "quit", "Quit", priority=True),
        Binding("e", "switch_mode('endpoints')", "Endpoints", show=True),
        Binding("s", "switch_mode('schemas')", "Schemas", show=True),
        Binding("d", "toggle_diff_only", "Toggle diff-only", show=True),
        Binding("ctrl+r", "reload", "Reload", show=True),
    ]

    def __init__(
        self,
        openapi: OpenAPIParser,
        source: str = "",
        base_parser: OpenAPIParser | None = None,
    ) -> None:
        super().__init__()
        self.openapi = openapi
        self.source = source
        self.diff_service = DiffService(base_parser, openapi)
        self._modes = {
            "endpoints": lambda: EndpointsScreen(self.openapi, self.diff_service),
            "schemas": lambda: SchemasScreen(self.openapi, self.diff_service),
        }

    def on_mount(self) -> None:
        info = self.openapi.info
        self.sub_title = self._build_sub_title(info.title, info.version)
        self.switch_mode("endpoints")

    def on_key(self, event: events.Key) -> None:
        """Handle key events to update subtitle with diff info."""
        if self.diff_service.is_diff_available():
            diff_info = self.diff_service.get_diff_summary()
            if diff_info:
                info = self.openapi.info
                base_title = self._build_sub_title(info.title, info.version)
                mode = " (diff-only)" if self.diff_service.is_diff_only_mode() else ""
                self.sub_title = f"{base_title} | {diff_info}{mode}"

    def _build_sub_title(self, title: str, version: str) -> str:
        source_label = ""
        if self.source and not self.source.startswith("http"):
            source_label = os.path.basename(self.source)
        elif self.source:
            source_label = self.source
        parts = [f"{title} {version}"]
        if source_label:
            parts.append(source_label)
        return " · ".join(parts)

    def action_reload(self) -> None:
        if not self.source:
            self.notify("No source to reload", severity="warning")
            return
        try:
            self.openapi = OpenAPIParser.from_source(self.source)
        except Exception as exc:  # noqa: BLE001
            self.notify(f"Reload failed: {exc}", severity="error")
            return

        for screen in self.screen_stack:
            if isinstance(screen, EndpointsScreen):
                screen.reload(self.openapi)
            elif isinstance(screen, SchemasScreen):
                screen.reload(self.openapi)

        self.notify("Schema reloaded", severity="information")

    def action_toggle_diff_only(self) -> None:
        """Toggle diff-only mode."""
        self.diff_service.toggle_diff_only()
        mode = "diff-only" if self.diff_service.is_diff_only_mode() else "all"
        self.notify(f"Showing {mode} items", severity="information")

        # Refresh current screen to apply filtering
        for screen in self.screen_stack:
            if isinstance(screen, EndpointsScreen):
                screen.apply_diff_filtering()
            elif isinstance(screen, SchemasScreen):
                screen.apply_diff_filtering()
