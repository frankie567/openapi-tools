from .._parser import Method


def get_method_color(method: Method) -> str:
    match method:
        case Method.GET:
            return "#61afef"
        case Method.POST:
            return "#98c379"
        case Method.PUT:
            return "#e5c07b"
        case Method.PATCH:
            return "#d19a66"
        case Method.DELETE:
            return "#e06c75"
        case Method.HEAD:
            return "#c678dd"
        case Method.OPTIONS:
            return "#56b6c2"
        case Method.TRACE:
            return "#abb2bf"


__all__ = [
    "get_method_color",
]
