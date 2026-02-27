from pathlib import Path

from openapi_tools._parser import OpenAPIParser, Reference, Schema


def test_parser():
    parser = OpenAPIParser.from_source(
        Path(__file__).parent / "fixtures" / "petstore.yaml"
    )

    pet_reference = Reference.model_validate({"$ref": "#/components/schemas/Pet"})
    pet_schema = parser.resolve_reference(pet_reference)
    assert isinstance(pet_schema, Schema)
