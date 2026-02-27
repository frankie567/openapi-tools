from pathlib import Path

import openapi_pydantic.v3.v3_0 as _v30
import openapi_pydantic.v3.v3_1 as _v31
import pytest

from openapi_tools._parser import (
    Method,
    OpenAPIParser,
    Schema,
)

Reference = _v31.Reference
_PARAMETER_TYPES = (_v30.Parameter, _v31.Parameter)

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def parser_3_1() -> OpenAPIParser:
    return OpenAPIParser.from_source(FIXTURES / "petstore_3_1.yaml")


@pytest.fixture
def parser_3_0() -> OpenAPIParser:
    return OpenAPIParser.from_source(FIXTURES / "petstore_3_0.yaml")


@pytest.mark.parametrize("parser", ["parser_3_1", "parser_3_0"])
def test_resolve_reference(parser: str, request: pytest.FixtureRequest):
    p: OpenAPIParser = request.getfixturevalue(parser)
    pet_reference = Reference.model_validate({"$ref": "#/components/schemas/Pet"})
    pet_schema = p.resolve_reference(pet_reference)
    assert isinstance(pet_schema, Schema)


@pytest.mark.parametrize("parser", ["parser_3_1", "parser_3_0"])
def test_info(parser: str, request: pytest.FixtureRequest):
    p: OpenAPIParser = request.getfixturevalue(parser)
    assert p.info.title == "Pet Store"
    assert p.info.version == "1.0.0"


@pytest.mark.parametrize("parser", ["parser_3_1", "parser_3_0"])
def test_endpoints(parser: str, request: pytest.FixtureRequest):
    p: OpenAPIParser = request.getfixturevalue(parser)
    endpoints = p.endpoints
    paths = {path for path, _, _ in endpoints}
    methods = {(path, method) for path, method, _ in endpoints}

    assert "/pets" in paths
    assert "/pets/{petId}" in paths
    assert "/orders" in paths

    assert (("/pets", Method.GET)) in methods
    assert (("/pets", Method.POST)) in methods
    assert (("/pets/{petId}", Method.GET)) in methods
    assert (("/pets/{petId}", Method.DELETE)) in methods
    assert (("/orders", Method.GET)) in methods


@pytest.mark.parametrize("parser", ["parser_3_1", "parser_3_0"])
def test_path_level_parameters_are_inherited(
    parser: str, request: pytest.FixtureRequest
):
    p: OpenAPIParser = request.getfixturevalue(parser)
    get_pet = next(
        op
        for path, method, op in p.endpoints
        if path == "/pets/{petId}" and method == Method.GET
    )
    assert any(
        isinstance(param, _PARAMETER_TYPES) and param.name == "petId"
        for param in (get_pet.parameters or [])
    )


@pytest.mark.parametrize("parser", ["parser_3_1", "parser_3_0"])
def test_schemas(parser: str, request: pytest.FixtureRequest):
    p: OpenAPIParser = request.getfixturevalue(parser)
    schema_names = {name for name, _ in p.schemas}
    assert "Pet" in schema_names
    assert "NewPet" in schema_names
    assert "Order" in schema_names


@pytest.mark.parametrize("parser", ["parser_3_1", "parser_3_0"])
def test_resolve_reference_invalid_format(parser: str, request: pytest.FixtureRequest):
    p: OpenAPIParser = request.getfixturevalue(parser)
    bad_ref = Reference.model_validate({"$ref": "#/invalid/ref"})
    with pytest.raises(ValueError, match="Unsupported reference format"):
        p.resolve_reference(bad_ref)


@pytest.mark.parametrize("parser", ["parser_3_1", "parser_3_0"])
def test_resolve_reference_missing_component(
    parser: str, request: pytest.FixtureRequest
):
    p: OpenAPIParser = request.getfixturevalue(parser)
    missing_ref = Reference.model_validate(
        {"$ref": "#/components/schemas/DoesNotExist"}
    )
    with pytest.raises(ValueError, match="No such component named"):
        p.resolve_reference(missing_ref)
