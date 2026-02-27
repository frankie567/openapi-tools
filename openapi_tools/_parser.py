import functools
import json
import pathlib
import typing
from enum import StrEnum

import httpx
import openapi_pydantic
import yaml

OpenAPI = openapi_pydantic.v3.v3_1.OpenAPI
Operation = openapi_pydantic.v3.v3_1.Operation
Schema = openapi_pydantic.v3.v3_1.Schema
Parameter = openapi_pydantic.v3.v3_1.Parameter
Reference = openapi_pydantic.v3.v3_1.Reference
RequestBody = openapi_pydantic.v3.v3_1.RequestBody
Responses = openapi_pydantic.v3.v3_1.Responses
Response = openapi_pydantic.v3.v3_1.Response
Info = openapi_pydantic.v3.v3_1.Info


class Method(StrEnum):
    GET = "get"
    POST = "post"
    PUT = "put"
    PATCH = "patch"
    DELETE = "delete"
    HEAD = "head"
    OPTIONS = "options"
    TRACE = "trace"


type Endpoint = tuple[str, Method, Operation]
type NamedSchema = tuple[str, Schema]


def _load_from_url(url: str) -> dict[str, typing.Any]:
    response = httpx.get(url, follow_redirects=True, timeout=30)
    response.raise_for_status()
    content_type = response.headers.get("content-type", "")
    text = response.text
    if "yaml" in content_type or url.endswith((".yaml", ".yml")):
        return yaml.safe_load(text)
    return json.loads(text)


def _load_from_file(path: str) -> dict[str, typing.Any]:
    with open(path, encoding="utf-8") as f:
        content = f.read()
    if path.endswith((".yaml", ".yml")):
        return yaml.safe_load(content)
    return json.loads(content)


class OpenAPIParser:
    def __init__(self, openapi: OpenAPI) -> None:
        self.openapi = openapi

    @classmethod
    def from_source(cls, source: str | pathlib.Path) -> typing.Self:
        """Load an OpenAPI spec from a file path or URL."""
        if isinstance(source, pathlib.Path):
            raw = _load_from_file(str(source))
        elif source.startswith("http://") or source.startswith("https://"):
            raw = _load_from_url(source)
        else:
            raw = _load_from_file(source)
        spec = typing.cast(OpenAPI, openapi_pydantic.parse_obj(raw))
        return cls(spec)

    @property
    def info(self) -> Info:
        """Return the Info object from the OpenAPI spec."""
        return self.openapi.info

    @functools.cached_property
    def endpoints(self) -> list[Endpoint]:
        """Return a list of all endpoints in the spec as (path, method, operation) tuples."""
        endpoints: list[Endpoint] = []
        paths = self.openapi.paths or {}

        for path, path_item in paths.items():
            path_level_params = path_item.parameters or []
            for method, operation in [
                (Method.GET, path_item.get),
                (Method.POST, path_item.post),
                (Method.PUT, path_item.put),
                (Method.PATCH, path_item.patch),
                (Method.DELETE, path_item.delete),
                (Method.HEAD, path_item.head),
                (Method.OPTIONS, path_item.options),
                (Method.TRACE, path_item.trace),
            ]:
                if operation is None:
                    continue
                if path_level_params:
                    op_param_names = {
                        (p.name if isinstance(p, Parameter) else p.ref)
                        for p in (operation.parameters or [])
                    }
                    inherited = [
                        p
                        for p in path_level_params
                        if (p.name if isinstance(p, Parameter) else p.ref)
                        not in op_param_names
                    ]
                    if inherited:
                        merged_params = list(inherited) + list(
                            operation.parameters or []
                        )
                        operation = operation.model_copy(
                            update={"parameters": merged_params}
                        )
                endpoints.append((path, method, operation))
        return endpoints

    @functools.cached_property
    def schemas(self) -> list[NamedSchema]:
        """Return a list of all schemas in the spec as (name, schema) tuples."""
        components = self.openapi.components
        if not components or not components.schemas:
            return []
        return list(components.schemas.items())

    def resolve_reference(self, ref: Reference) -> typing.Any:
        """Resolve a Reference object to its actual value."""
        ref_path = ref.ref.split("/")
        if len(ref_path) < 3 or ref_path[0] != "#" or ref_path[1] != "components":
            raise ValueError(f"Unsupported reference format: {ref.ref}")  # noqa: TRY003
        _, _, category, name = ref_path
        components = self.openapi.components
        if not components:
            raise ValueError("No components defined in the OpenAPI spec")  # noqa: TRY003
        category_dict = getattr(components, category, None)
        if not category_dict:
            raise ValueError(f"No such component category: {category}")  # noqa: TRY003
        resolved = category_dict.get(name)
        if not resolved:
            raise ValueError(  # noqa: TRY003
                f"No such component named '{name}' in category '{category}'"
            )
        return resolved


__all__ = [
    "OpenAPIParser",
    "Endpoint",
    "Parameter",
    "Reference",
    "Method",
    "NamedSchema",
    "RequestBody",
    "Responses",
    "Response",
]
