"""Diff service for comparing OpenAPI schemas in the TUI."""

from __future__ import annotations

from .._diff import (
    APIDiff,
    ChangeType,
    OperationChange,
    SchemaChange,
    SchemaPropertyChange,
    compare,
)
from .._parser import Endpoint, OpenAPIParser


class DiffService:
    """Service for calculating and managing diffs between OpenAPI schemas."""

    def __init__(self, base_parser: OpenAPIParser | None, head_parser: OpenAPIParser):
        self.base_parser = base_parser
        self.head_parser = head_parser
        self.diff = self._calculate_diff() if base_parser else None
        self.diff_only_mode = False

    def _calculate_diff(self) -> APIDiff:
        """Calculate the diff between base and head schemas."""
        assert self.base_parser is not None
        return compare(self.base_parser, self.head_parser)

    def is_diff_available(self) -> bool:
        """Check if diff comparison is available."""
        return self.diff is not None

    def toggle_diff_only(self) -> None:
        """Toggle diff-only mode."""
        self.diff_only_mode = not self.diff_only_mode

    def is_diff_only_mode(self) -> bool:
        """Check if diff-only mode is enabled."""
        return self.diff_only_mode

    def get_endpoint_change_type(self, endpoint: Endpoint) -> ChangeType | None:
        """Get the change type for a specific endpoint."""
        if not self.diff:
            return None

        path, method, _ = endpoint
        for change in self.diff.operation_changes:
            if change.path == path and change.method == method:
                return change.change_type
        return None

    def get_schema_change_type(self, schema_name: str) -> ChangeType | None:
        """Get the change type for a specific schema."""
        if not self.diff:
            return None

        for change in self.diff.schema_changes:
            if change.name == schema_name:
                return change.change_type
        return None

    def get_endpoint_changes(self, endpoint: Endpoint) -> OperationChange | None:
        """Get detailed changes for a specific endpoint."""
        if not self.diff:
            return None

        path, method, _ = endpoint
        for change in self.diff.operation_changes:
            if change.path == path and change.method == method:
                return change
        return None

    def get_schema_changes(self, schema_name: str) -> SchemaChange | None:
        """Get detailed changes for a specific schema."""
        if not self.diff:
            return None

        for change in self.diff.schema_changes:
            if change.name == schema_name:
                return change
        return None

    def get_property_change(
        self, schema_name: str, property_name: str
    ) -> SchemaPropertyChange | None:
        """Get the change type for a specific property in a schema."""
        schema_changes = self.get_schema_changes(schema_name)
        if not schema_changes:
            return None

        for prop_change in schema_changes.property_changes:
            if prop_change.name == property_name:
                return prop_change

        return None

    def should_show_endpoint(self, endpoint: Endpoint) -> bool:
        """Check if endpoint should be shown based on diff-only mode."""
        if not self.diff_only_mode:
            return True

        change_type = self.get_endpoint_change_type(endpoint)
        return change_type is not None

    def should_show_schema(self, schema_name: str) -> bool:
        """Check if schema should be shown based on diff-only mode."""
        if not self.diff_only_mode:
            return True

        change_type = self.get_schema_change_type(schema_name)
        return change_type is not None

    def get_change_icon(self, change_type: ChangeType | None) -> str:
        """Get the icon for a change type."""
        if change_type is None:
            return ""

        icons = {
            ChangeType.ADDED: "[green]+[/green]",
            ChangeType.REMOVED: "[red]-[/red]",
            ChangeType.MODIFIED: "[orange]~[/orange]",
        }
        return icons.get(change_type, "")

    def get_change_color(self, change_type: ChangeType | None) -> str:
        """Get the color for a change type."""
        if change_type is None:
            return ""

        colors = {
            ChangeType.ADDED: "green",
            ChangeType.REMOVED: "red",
            ChangeType.MODIFIED: "orange",
        }
        return colors.get(change_type, "")
