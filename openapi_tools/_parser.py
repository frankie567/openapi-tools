import functools
import json
import pathlib
import typing
from enum import StrEnum

import httpx
import openapi_pydantic.v3.v3_0 as _v30
import openapi_pydantic.v3.v3_1 as _v31
import yaml
from openapi_pydantic import parse_obj

OpenAPI = _v30.OpenAPI | _v31.OpenAPI
Operation = _v30.Operation | _v31.Operation
Schema = _v30.Schema | _v31.Schema
Parameter = _v30.Parameter | _v31.Parameter
Reference = _v30.Reference | _v31.Reference
RequestBody = _v30.RequestBody | _v31.RequestBody
Responses = _v30.Responses | _v31.Responses
Response = _v30.Response | _v31.Response
Info = _v30.Info | _v31.Info


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
type NamedSchema = tuple[str, Schema | Reference]


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


def _param_key(
    p: _v30.Parameter | _v31.Parameter | _v30.Reference | _v31.Reference,
) -> str:
    if isinstance(p, (_v30.Parameter, _v31.Parameter)):
        return p.name
    return p.ref


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
        spec = parse_obj(raw)
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
                        _param_key(p) for p in (operation.parameters or [])
                    }
                    inherited = [
                        p
                        for p in path_level_params
                        if _param_key(p) not in op_param_names
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
