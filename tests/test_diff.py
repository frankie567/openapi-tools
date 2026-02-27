from pathlib import Path

import pytest

from openapi_tools._diff import (
    APIDiff,
    ChangeType,
    RequestBodyChange,
    ResponseChange,
    compare,
    to_json,
    to_markdown,
)
from openapi_tools._parser import OpenAPIParser

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def base_parser() -> OpenAPIParser:
    return OpenAPIParser.from_source(FIXTURES / "petstore_3_1.yaml")


@pytest.fixture
def head_parser() -> OpenAPIParser:
    return OpenAPIParser.from_source(FIXTURES / "petstore_3_1_v2.yaml")


@pytest.fixture
def diff(base_parser: OpenAPIParser, head_parser: OpenAPIParser) -> APIDiff:
    return compare(base_parser, head_parser)


def test_compare_returns_apidiff(diff: APIDiff) -> None:
    assert isinstance(diff, APIDiff)


def test_removed_operations(diff: APIDiff) -> None:
    removed = [c for c in diff.operation_changes if c.change_type == ChangeType.REMOVED]
    paths_methods = {(c.path, c.method) for c in removed}
    assert ("/orders", "get") in paths_methods
    assert ("/pets/{petId}", "delete") in paths_methods


def test_added_operations(diff: APIDiff) -> None:
    added = [c for c in diff.operation_changes if c.change_type == ChangeType.ADDED]
    paths_methods = {(c.path, c.method) for c in added}
    assert ("/pets/{petId}/vaccinations", "get") in paths_methods


def test_modified_operation_parameter_added(diff: APIDiff) -> None:
    modified = next(
        c
        for c in diff.operation_changes
        if c.path == "/pets"
        and c.method == "get"
        and c.change_type == ChangeType.MODIFIED
    )
    added_params = [
        p for p in modified.parameter_changes if p.change_type == ChangeType.ADDED
    ]
    param_names = {p.name for p in added_params}
    assert "filter" in param_names


def test_modified_operation_parameter_changed(diff: APIDiff) -> None:
    modified = next(
        c
        for c in diff.operation_changes
        if c.path == "/pets"
        and c.method == "get"
        and c.change_type == ChangeType.MODIFIED
    )
    changed_params = [
        p for p in modified.parameter_changes if p.change_type == ChangeType.MODIFIED
    ]
    limit_change = next(p for p in changed_params if p.name == "limit")
    assert limit_change.location == "query"
    required_change = next(
        fc for fc in limit_change.field_changes if fc.field == "required"
    )
    assert required_change.old_value is False
    assert required_change.new_value is True


def test_removed_schema(diff: APIDiff) -> None:
    removed = [c for c in diff.schema_changes if c.change_type == ChangeType.REMOVED]
    names = {c.name for c in removed}
    assert "Order" in names


def test_added_schema(diff: APIDiff) -> None:
    added = [c for c in diff.schema_changes if c.change_type == ChangeType.ADDED]
    names = {c.name for c in added}
    assert "Vaccination" in names


def test_modified_schema_property_added(diff: APIDiff) -> None:
    pet_change = next(
        c
        for c in diff.schema_changes
        if c.name == "Pet" and c.change_type == ChangeType.MODIFIED
    )
    added_props = [
        p for p in pet_change.property_changes if p.change_type == ChangeType.ADDED
    ]
    prop_names = {p.name for p in added_props}
    assert "breed" in prop_names


def test_modified_schema_property_required_changed(diff: APIDiff) -> None:
    pet_change = next(
        c
        for c in diff.schema_changes
        if c.name == "Pet" and c.change_type == ChangeType.MODIFIED
    )
    tag_change = next(
        p
        for p in pet_change.property_changes
        if p.name == "tag" and p.change_type == ChangeType.MODIFIED
    )
    required_fc = next(fc for fc in tag_change.field_changes if fc.field == "required")
    assert required_fc.old_value is False
    assert required_fc.new_value is True


def test_identical_schemas_produce_no_changes(base_parser: OpenAPIParser) -> None:
    result = compare(base_parser, base_parser)
    assert result.operation_changes == []
    assert result.schema_changes == []


def test_to_json(diff: APIDiff) -> None:
    import json

    output = to_json(diff)
    parsed = json.loads(output)
    assert "operation_changes" in parsed
    assert "schema_changes" in parsed


def test_to_markdown_contains_sections(diff: APIDiff) -> None:
    output = to_markdown(diff)
    assert "# API Diff" in output
    assert "## Operations" in output
    assert "## Schemas" in output


def test_to_markdown_added_icon(diff: APIDiff) -> None:
    output = to_markdown(diff)
    assert "🔼" in output


def test_to_markdown_removed_icon(diff: APIDiff) -> None:
    output = to_markdown(diff)
    assert "🔽" in output


def test_to_markdown_modified_icon(diff: APIDiff) -> None:
    output = to_markdown(diff)
    assert "🔀" in output


def test_to_markdown_no_changes() -> None:
    empty = APIDiff()
    output = to_markdown(empty)
    assert "# API Diff" in output
    assert "## Operations" not in output
    assert "## Schemas" not in output


def test_enum_value_added_in_schema_property(diff: APIDiff) -> None:
    newpet_change = next(
        c
        for c in diff.schema_changes
        if c.name == "NewPet" and c.change_type == ChangeType.MODIFIED
    )
    size_change = next(
        p
        for p in newpet_change.property_changes
        if p.name == "size" and p.change_type == ChangeType.MODIFIED
    )
    enum_fc = next(fc for fc in size_change.field_changes if fc.field == "enum")
    assert "extra_large" not in (enum_fc.old_value or [])
    assert "extra_large" in (enum_fc.new_value or [])


def test_request_body_required_changed(diff: APIDiff) -> None:
    post_change = next(
        c
        for c in diff.operation_changes
        if c.path == "/pets"
        and c.method == "post"
        and c.change_type == ChangeType.MODIFIED
    )
    assert post_change.request_body_change is not None
    assert post_change.request_body_change.change_type == ChangeType.MODIFIED
    required_fc = next(
        fc
        for fc in post_change.request_body_change.field_changes
        if fc.field == "required"
    )
    assert required_fc.old_value is True
    assert required_fc.new_value is False


def test_response_removed(diff: APIDiff) -> None:
    get_pets_change = next(
        c
        for c in diff.operation_changes
        if c.path == "/pets"
        and c.method == "get"
        and c.change_type == ChangeType.MODIFIED
    )
    removed_responses = [
        r
        for r in get_pets_change.response_changes
        if r.change_type == ChangeType.REMOVED
    ]
    assert any(r.status_code == "400" for r in removed_responses)


def test_response_added(diff: APIDiff) -> None:
    get_pets_change = next(
        c
        for c in diff.operation_changes
        if c.path == "/pets"
        and c.method == "get"
        and c.change_type == ChangeType.MODIFIED
    )
    added_responses = [
        r for r in get_pets_change.response_changes if r.change_type == ChangeType.ADDED
    ]
    assert any(r.status_code == "429" for r in added_responses)


def test_response_modified_description(diff: APIDiff) -> None:
    get_pet_change = next(
        c
        for c in diff.operation_changes
        if c.path == "/pets/{petId}"
        and c.method == "get"
        and c.change_type == ChangeType.MODIFIED
    )
    modified_responses = [
        r
        for r in get_pet_change.response_changes
        if r.change_type == ChangeType.MODIFIED
    ]
    response_200 = next(r for r in modified_responses if r.status_code == "200")
    desc_fc = next(fc for fc in response_200.field_changes if fc.field == "description")
    assert desc_fc.old_value == "A pet"
    assert desc_fc.new_value == "The requested pet"


def test_request_body_change_is_instance(diff: APIDiff) -> None:
    post_change = next(
        c for c in diff.operation_changes if c.path == "/pets" and c.method == "post"
    )
    assert isinstance(post_change.request_body_change, RequestBodyChange)


def test_response_change_is_instance(diff: APIDiff) -> None:
    get_pets_change = next(
        c for c in diff.operation_changes if c.path == "/pets" and c.method == "get"
    )
    assert all(isinstance(r, ResponseChange) for r in get_pets_change.response_changes)


def test_to_markdown_includes_request_body_change(diff: APIDiff) -> None:
    output = to_markdown(diff)
    assert "Request body" in output


def test_to_markdown_includes_response_change(diff: APIDiff) -> None:
    output = to_markdown(diff)
    assert "Response" in output
