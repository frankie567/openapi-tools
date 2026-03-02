from collections import defaultdict

from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Tree

from ..._parser import Endpoint, Method, OpenAPIParser
from .._diff_service import DiffService
from .._utils import get_method_color


def _method_markup(method: Method) -> str:
    color = get_method_color(method)
    return f"[bold {color}]{method.upper():<7}[/]"


def _get_endpoint_markup(endpoint: Endpoint, diff_service: DiffService) -> str:
    """Get markup for an endpoint with diff highlighting."""
    path, method, _ = endpoint

    if diff_service.is_diff_available():
        change_type = diff_service.get_endpoint_change_type(endpoint)
        if change_type:
            icon = diff_service.get_change_icon(change_type)
            return f"{icon} {_method_markup(method)} {path}"

    return f"{_method_markup(method)} {path}"


class EndpointsList(Widget):
    """Left-panel widget listing API endpoints grouped by tag in a Tree."""

    DEFAULT_CSS = """
    EndpointsList {
        width: 1fr;
        height: 1fr;
        border: round $primary-darken-2;
        margin: 0 1 0 0;
    }
    EndpointsList > Tree {
        height: 1fr;
        border: none;
        background: $surface;
        padding: 0 0 0 1;
    }
    """

    class EndpointSelected(Message):
        """Posted when the user selects an endpoint."""

        def __init__(self, endpoint: Endpoint) -> None:
            super().__init__()
            self.endpoint = endpoint

    def __init__(self, openapi: OpenAPIParser, diff_service: DiffService) -> None:
        super().__init__()
        self.openapi = openapi
        self.diff_service = diff_service

    def compose(self) -> ComposeResult:
        yield Tree("Endpoints", id="endpoints-tree")

    def on_mount(self) -> None:
        self.border_title = "Endpoints"
        tree = self.query_one("#endpoints-tree", Tree)
        tree.show_root = False
        tree.show_guides = True
        self._rebuild_tree()

    def reload(self, openapi: OpenAPIParser) -> None:
        self.openapi = openapi
        self._rebuild_tree()

    def apply_diff_filtering(self) -> None:
        """Apply diff filtering to the endpoints list."""
        self._rebuild_tree()

    def _rebuild_tree(self) -> None:
        tree: Tree[Endpoint] = self.query_one("#endpoints-tree", Tree)
        tree.root.remove_children()

        endpoints_by_tag: defaultdict[str, list[Endpoint]] = defaultdict(list)
        for endpoint in self.openapi.endpoints:
            path, method, operation = endpoint
            for tag in operation.tags or ["default"]:
                endpoints_by_tag[tag].append(endpoint)

        for tag in sorted(endpoints_by_tag):
            tag_node = tree.root.add(
                f"[bold $accent]{tag}[/]",
                data=None,
                expand=True,
            )
            for endpoint in endpoints_by_tag[tag]:
                if not self.diff_service.should_show_endpoint(endpoint):
                    continue
                _, _, operation = endpoint
                tag_node.add_leaf(
                    _get_endpoint_markup(endpoint, self.diff_service), data=endpoint
                )

    def on_tree_node_selected(self, event: Tree.NodeSelected[Endpoint]) -> None:
        endpoint = event.node.data
        if endpoint is not None:
            self.post_message(self.EndpointSelected(endpoint))
