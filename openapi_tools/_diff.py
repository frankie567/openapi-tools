"""OpenAPI schema diff utilities."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

import openapi_pydantic.v3.v3_0 as _v30
import openapi_pydantic.v3.v3_1 as _v31
from pydantic import BaseModel

from ._parser import OpenAPIParser

_REFERENCE_TYPES = (_v30.Reference, _v31.Reference)
_PARAMETER_TYPES = (_v30.Parameter, _v31.Parameter)
_SCHEMA_TYPES = (_v30.Schema, _v31.Schema)
_PARAMETER_COMPARABLE_FIELDS = ("required", "description", "deprecated")


class ChangeType(StrEnum):
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"


class FieldChange(BaseModel):
    field: str
    old_value: Any = None
    new_value: Any = None


class ParameterChange(BaseModel):
    name: str
    location: str
    change_type: ChangeType
    field_changes: list[FieldChange] = []


class RequestBodyChange(BaseModel):
    change_type: ChangeType
    field_changes: list[FieldChange] = []


class ResponseChange(BaseModel):
    status_code: str
    change_type: ChangeType
    field_changes: list[FieldChange] = []


class OperationChange(BaseModel):
    path: str
    method: str
    change_type: ChangeType
    parameter_changes: list[ParameterChange] = []
    request_body_change: RequestBodyChange | None = None
    response_changes: list[ResponseChange] = []


class SchemaPropertyChange(BaseModel):
    name: str
    change_type: ChangeType
    field_changes: list[FieldChange] = []


class SchemaChange(BaseModel):
    name: str
    change_type: ChangeType
    property_changes: list[SchemaPropertyChange] = []


class APIDiff(BaseModel):
    operation_changes: list[OperationChange] = []
    schema_changes: list[SchemaChange] = []


def _resolve_parameter(
    p: _v30.Parameter | _v31.Parameter | _v30.Reference | _v31.Reference,
    parser: OpenAPIParser,
) -> _v30.Parameter | _v31.Parameter | None:
    if isinstance(p, _REFERENCE_TYPES):
        resolved = parser.resolve_reference(p)
        if isinstance(resolved, _PARAMETER_TYPES):
            return resolved
        return None
    return p


def _compare_parameter_fields(
    base: _v30.Parameter | _v31.Parameter,
    head: _v30.Parameter | _v31.Parameter,
) -> list[FieldChange]:
    changes: list[FieldChange] = []
    for field in _PARAMETER_COMPARABLE_FIELDS:
        old_val = getattr(base, field, None)
        new_val = getattr(head, field, None)
        if old_val != new_val:
            changes.append(
                FieldChange(field=field, old_value=old_val, new_value=new_val)
            )
    base_schema = base.param_schema
    head_schema = head.param_schema
    if isinstance(base_schema, _SCHEMA_TYPES) and isinstance(
        head_schema, _SCHEMA_TYPES
    ):
        if base_schema.type != head_schema.type:
            changes.append(
                FieldChange(
                    field="schema.type",
                    old_value=str(base_schema.type)
                    if base_schema.type is not None
                    else None,
                    new_value=str(head_schema.type)
                    if head_schema.type is not None
                    else None,
                )
            )
    return changes


def _compare_parameters(
    base_params: list[Any],
    head_params: list[Any],
    base_parser: OpenAPIParser,
    head_parser: OpenAPIParser,
) -> list[ParameterChange]:
    changes: list[ParameterChange] = []

    base_resolved = [_resolve_parameter(p, base_parser) for p in base_params]
    head_resolved = [_resolve_parameter(p, head_parser) for p in head_params]

    base_dict = {(p.name, p.param_in.value): p for p in base_resolved if p is not None}
    head_dict = {(p.name, p.param_in.value): p for p in head_resolved if p is not None}

    for key in set(base_dict) - set(head_dict):
        p = base_dict[key]
        changes.append(
            ParameterChange(
                name=p.name,
                location=p.param_in.value,
                change_type=ChangeType.REMOVED,
            )
        )

    for key in set(head_dict) - set(base_dict):
        p = head_dict[key]
        changes.append(
            ParameterChange(
                name=p.name,
                location=p.param_in.value,
                change_type=ChangeType.ADDED,
            )
        )

    for key in set(base_dict) & set(head_dict):
        base_p = base_dict[key]
        head_p = head_dict[key]
        field_changes = _compare_parameter_fields(base_p, head_p)
        if field_changes:
            changes.append(
                ParameterChange(
                    name=base_p.name,
                    location=base_p.param_in.value,
                    change_type=ChangeType.MODIFIED,
                    field_changes=field_changes,
                )
            )

    return changes


def _compare_schema_properties(
    base: _v30.Schema | _v31.Schema,
    head: _v30.Schema | _v31.Schema,
) -> list[SchemaPropertyChange]:
    base_props = base.properties or {}
    head_props = head.properties or {}
    base_required = set(base.required or [])
    head_required = set(head.required or [])

    changes: list[SchemaPropertyChange] = []

    for name in set(base_props) - set(head_props):
        changes.append(SchemaPropertyChange(name=name, change_type=ChangeType.REMOVED))

    for name in set(head_props) - set(base_props):
        changes.append(SchemaPropertyChange(name=name, change_type=ChangeType.ADDED))

    for name in set(base_props) & set(head_props):
        base_prop = base_props[name]
        head_prop = head_props[name]
        field_changes: list[FieldChange] = []

        base_was_required = name in base_required
        head_is_required = name in head_required
        if base_was_required != head_is_required:
            field_changes.append(
                FieldChange(
                    field="required",
                    old_value=base_was_required,
                    new_value=head_is_required,
                )
            )

        if isinstance(base_prop, _SCHEMA_TYPES) and isinstance(
            head_prop, _SCHEMA_TYPES
        ):
            if base_prop.type != head_prop.type:
                field_changes.append(
                    FieldChange(
                        field="type",
                        old_value=str(base_prop.type)
                        if base_prop.type is not None
                        else None,
                        new_value=str(head_prop.type)
                        if head_prop.type is not None
                        else None,
                    )
                )
            if base_prop.description != head_prop.description:
                field_changes.append(
                    FieldChange(
                        field="description",
                        old_value=base_prop.description,
                        new_value=head_prop.description,
                    )
                )
            if base_prop.enum != head_prop.enum:
                field_changes.append(
                    FieldChange(
                        field="enum",
                        old_value=base_prop.enum,
                        new_value=head_prop.enum,
                    )
                )

        if field_changes:
            changes.append(
                SchemaPropertyChange(
                    name=name,
                    change_type=ChangeType.MODIFIED,
                    field_changes=field_changes,
                )
            )

    return changes


def _resolve_request_body(
    rb: _v30.RequestBody | _v31.RequestBody | _v30.Reference | _v31.Reference | None,
    parser: OpenAPIParser,
) -> _v30.RequestBody | _v31.RequestBody | None:
    if rb is None:
        return None
    if isinstance(rb, _REFERENCE_TYPES):
        resolved = parser.resolve_reference(rb)
        if isinstance(resolved, (_v30.RequestBody, _v31.RequestBody)):
            return resolved
        return None
    return rb


def _compare_request_body(
    base_rb: _v30.RequestBody
    | _v31.RequestBody
    | _v30.Reference
    | _v31.Reference
    | None,
    head_rb: _v30.RequestBody
    | _v31.RequestBody
    | _v30.Reference
    | _v31.Reference
    | None,
    base_parser: OpenAPIParser,
    head_parser: OpenAPIParser,
) -> RequestBodyChange | None:
    base = _resolve_request_body(base_rb, base_parser)
    head = _resolve_request_body(head_rb, head_parser)

    if base is None and head is None:
        return None
    if base is None:
        return RequestBodyChange(change_type=ChangeType.ADDED)
    if head is None:
        return RequestBodyChange(change_type=ChangeType.REMOVED)

    field_changes: list[FieldChange] = []
    if base.required != head.required:
        field_changes.append(
            FieldChange(
                field="required", old_value=base.required, new_value=head.required
            )
        )
    if base.description != head.description:
        field_changes.append(
            FieldChange(
                field="description",
                old_value=base.description,
                new_value=head.description,
            )
        )
    base_media_types = set(base.content or {})
    head_media_types = set(head.content or {})
    for mt in base_media_types - head_media_types:
        field_changes.append(
            FieldChange(field=f"content.{mt}", old_value=mt, new_value=None)
        )
    for mt in head_media_types - base_media_types:
        field_changes.append(
            FieldChange(field=f"content.{mt}", old_value=None, new_value=mt)
        )

    if not field_changes:
        return None
    return RequestBodyChange(
        change_type=ChangeType.MODIFIED, field_changes=field_changes
    )


def _resolve_response(
    r: _v30.Response | _v31.Response | _v30.Reference | _v31.Reference,
    parser: OpenAPIParser,
) -> _v30.Response | _v31.Response | None:
    if isinstance(r, _REFERENCE_TYPES):
        resolved = parser.resolve_reference(r)
        if isinstance(resolved, (_v30.Response, _v31.Response)):
            return resolved
        return None
    return r


def _compare_responses(
    base_responses: dict[str, Any] | None,
    head_responses: dict[str, Any] | None,
    base_parser: OpenAPIParser,
    head_parser: OpenAPIParser,
) -> list[ResponseChange]:
    base_dict = base_responses or {}
    head_dict = head_responses or {}
    changes: list[ResponseChange] = []

    for code in set(base_dict) - set(head_dict):
        changes.append(ResponseChange(status_code=code, change_type=ChangeType.REMOVED))

    for code in set(head_dict) - set(base_dict):
        changes.append(ResponseChange(status_code=code, change_type=ChangeType.ADDED))

    for code in set(base_dict) & set(head_dict):
        base_r = _resolve_response(base_dict[code], base_parser)
        head_r = _resolve_response(head_dict[code], head_parser)
        if base_r is None or head_r is None:
            continue
        field_changes: list[FieldChange] = []
        if base_r.description != head_r.description:
            field_changes.append(
                FieldChange(
                    field="description",
                    old_value=base_r.description,
                    new_value=head_r.description,
                )
            )
        base_media_types = set(base_r.content or {})
        head_media_types = set(head_r.content or {})
        for mt in base_media_types - head_media_types:
            field_changes.append(
                FieldChange(field=f"content.{mt}", old_value=mt, new_value=None)
            )
        for mt in head_media_types - base_media_types:
            field_changes.append(
                FieldChange(field=f"content.{mt}", old_value=None, new_value=mt)
            )
        for mt in base_media_types & head_media_types:
            base_schema = (base_r.content or {}).get(mt)
            head_schema = (head_r.content or {}).get(mt)
            if base_schema is not None and head_schema is not None:
                base_s = base_schema.media_type_schema
                head_s = head_schema.media_type_schema
                base_ref = base_s.ref if isinstance(base_s, _REFERENCE_TYPES) else None
                head_ref = head_s.ref if isinstance(head_s, _REFERENCE_TYPES) else None
                if base_ref != head_ref:
                    field_changes.append(
                        FieldChange(
                            field=f"content.{mt}.schema",
                            old_value=base_ref,
                            new_value=head_ref,
                        )
                    )
        if field_changes:
            changes.append(
                ResponseChange(
                    status_code=code,
                    change_type=ChangeType.MODIFIED,
                    field_changes=field_changes,
                )
            )

    return changes


def compare(base: OpenAPIParser, head: OpenAPIParser) -> APIDiff:
    """Compare two OpenAPI specs and return a structured diff."""
    base_ops = {(path, str(method)): op for path, method, op in base.endpoints}
    head_ops = {(path, str(method)): op for path, method, op in head.endpoints}

    operation_changes: list[OperationChange] = []

    for path, method in set(base_ops) - set(head_ops):
        operation_changes.append(
            OperationChange(path=path, method=method, change_type=ChangeType.REMOVED)
        )

    for path, method in set(head_ops) - set(base_ops):
        operation_changes.append(
            OperationChange(path=path, method=method, change_type=ChangeType.ADDED)
        )

    for path, method in set(base_ops) & set(head_ops):
        base_op = base_ops[(path, method)]
        head_op = head_ops[(path, method)]
        param_changes = _compare_parameters(
            base_op.parameters or [],
            head_op.parameters or [],
            base,
            head,
        )
        rb_change = _compare_request_body(
            base_op.requestBody, head_op.requestBody, base, head
        )
        resp_changes = _compare_responses(
            base_op.responses, head_op.responses, base, head
        )
        if param_changes or rb_change is not None or resp_changes:
            operation_changes.append(
                OperationChange(
                    path=path,
                    method=method,
                    change_type=ChangeType.MODIFIED,
                    parameter_changes=param_changes,
                    request_body_change=rb_change,
                    response_changes=resp_changes,
                )
            )

    base_schemas = dict(base.schemas)
    head_schemas = dict(head.schemas)

    schema_changes: list[SchemaChange] = []

    for name in set(base_schemas) - set(head_schemas):
        schema_changes.append(SchemaChange(name=name, change_type=ChangeType.REMOVED))

    for name in set(head_schemas) - set(base_schemas):
        schema_changes.append(SchemaChange(name=name, change_type=ChangeType.ADDED))

    for name in set(base_schemas) & set(head_schemas):
        base_schema = base_schemas[name]
        head_schema = head_schemas[name]

        if isinstance(base_schema, _REFERENCE_TYPES):
            base_schema = base.resolve_reference(base_schema)
        if isinstance(head_schema, _REFERENCE_TYPES):
            head_schema = head.resolve_reference(head_schema)

        if not isinstance(base_schema, _SCHEMA_TYPES) or not isinstance(
            head_schema, _SCHEMA_TYPES
        ):
            continue

        property_changes = _compare_schema_properties(base_schema, head_schema)
        if property_changes:
            schema_changes.append(
                SchemaChange(
                    name=name,
                    change_type=ChangeType.MODIFIED,
                    property_changes=property_changes,
                )
            )

    return APIDiff(
        operation_changes=operation_changes,
        schema_changes=schema_changes,
    )


def to_json(diff: APIDiff) -> str:
    """Serialize an APIDiff to a JSON string."""
    return diff.model_dump_json(indent=2)


def to_markdown(diff: APIDiff) -> str:
    """Render an APIDiff as a human-readable Markdown string."""
    lines: list[str] = ["# API Diff", ""]

    _ICONS = {
        ChangeType.ADDED: "🔼",
        ChangeType.REMOVED: "🔽",
        ChangeType.MODIFIED: "🔀",
    }

    if diff.operation_changes:
        lines.append("## Operations")
        lines.append("")
        for change in sorted(diff.operation_changes, key=lambda c: (c.path, c.method)):
            icon = _ICONS[change.change_type]
            lines.append(
                f"- {icon} `{change.method.upper()} {change.path}` ({change.change_type})"
            )
            for pc in change.parameter_changes:
                param_icon = _ICONS[pc.change_type]
                lines.append(
                    f"  - {param_icon} Parameter `{pc.name}` (in {pc.location}) {pc.change_type}"
                )
                for fc in pc.field_changes:
                    lines.append(
                        f"    - `{fc.field}`: `{fc.old_value}` → `{fc.new_value}`"
                    )
            if change.request_body_change is not None:
                rb_icon = _ICONS[change.request_body_change.change_type]
                lines.append(
                    f"  - {rb_icon} Request body {change.request_body_change.change_type}"
                )
                for fc in change.request_body_change.field_changes:
                    lines.append(
                        f"    - `{fc.field}`: `{fc.old_value}` → `{fc.new_value}`"
                    )
            for rc in sorted(change.response_changes, key=lambda r: r.status_code):
                resp_icon = _ICONS[rc.change_type]
                lines.append(
                    f"  - {resp_icon} Response `{rc.status_code}` {rc.change_type}"
                )
                for fc in rc.field_changes:
                    lines.append(
                        f"    - `{fc.field}`: `{fc.old_value}` → `{fc.new_value}`"
                    )
        lines.append("")

    if diff.schema_changes:
        lines.append("## Schemas")
        lines.append("")
        for schema_change in sorted(diff.schema_changes, key=lambda c: c.name):
            icon = _ICONS[schema_change.change_type]
            lines.append(
                f"- {icon} `{schema_change.name}` ({schema_change.change_type})"
            )
            for prop_change in schema_change.property_changes:
                prop_icon = _ICONS[prop_change.change_type]
                lines.append(
                    f"  - {prop_icon} Property `{prop_change.name}` {prop_change.change_type}"
                )
                for fc in prop_change.field_changes:
                    lines.append(
                        f"    - `{fc.field}`: `{fc.old_value}` → `{fc.new_value}`"
                    )
        lines.append("")

    return "\n".join(lines)


__all__ = [
    "APIDiff",
    "ChangeType",
    "FieldChange",
    "OperationChange",
    "ParameterChange",
    "RequestBodyChange",
    "ResponseChange",
    "SchemaChange",
    "SchemaPropertyChange",
    "compare",
    "to_json",
    "to_markdown",
]
