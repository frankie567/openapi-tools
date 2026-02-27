# OpenAPI Tools

<p align="center">
    <em>Python tools to work with OpenAPI schemas</em>
</p>

[![build](https://github.com/frankie567/openapi-tools/workflows/Build/badge.svg)](https://github.com/frankie567/openapi-tools/actions)
[![codecov](https://codecov.io/gh/frankie567/openapi-tools/branch/master/graph/badge.svg)](https://codecov.io/gh/frankie567/openapi-tools)
[![PyPI version](https://badge.fury.io/py/openapi-tools.svg)](https://badge.fury.io/py/openapi-tools)

---

**Documentation**: <a href="https://frankie567.github.io/openapi-tools/" target="_blank">https://frankie567.github.io/openapi-tools/</a>

**Source Code**: <a href="https://github.com/frankie567/openapi-tools" target="_blank">https://github.com/frankie567/openapi-tools</a>

---

## OpenAPI TUI

Explore any OpenAPI schema right in your terminal — no browser required.

```bash
uvx openapi-tools view https://petstore3.swagger.io/api/v3/openapi.json
```

You can also point it at a local file:

```bash
uvx openapi-tools view ./my-api.yaml
```

### Features

- **Endpoints browser** — all routes grouped by tag in a navigable tree, with per-endpoint details across dedicated tabs: Info, Path parameters, Query parameters, Headers, Request body, and Responses.
- **Schemas browser** — browse every component schema with a full property table including types, constraints, and required markers.
- **Schema navigation** — clickable schema links inside endpoint and schema detail panels let you jump straight to the referenced type, with breadcrumb-style back navigation.
- **Live reload** — press `Ctrl+R` to re-fetch the schema from its original source without leaving the TUI.
- **Keyboard-driven** — switch between Endpoints (`E`) and Schemas (`S`) views, quit with `Q` or `Ctrl+C`.

### Screenshots

#### Endpoints list

![Endpoints list](docs/images/tui-endpoints.svg)

#### Endpoint detail

![Endpoint detail](docs/images/tui-endpoint-detail.svg)

#### Schemas list

![Schemas list](docs/images/tui-schemas.svg)

#### Schema detail

![Schema detail](docs/images/tui-schema-detail.svg)

---

## Development

### Setup environment

We use [uv](https://docs.astral.sh/uv/) to manage the development environment and production build, and [just](https://github.com/casey/just) to manage command shortcuts. Ensure they are installed on your system.

### Run unit tests

You can run all the tests with:

```bash
just test
```

### Format the code

Execute the following command to apply linting and check typing:

```bash
just lint
```

### Regenerate screenshots

The screenshots in this README are generated from a live Petstore schema using Textual's headless mode:

```bash
uv run scripts/generate_screenshots.py
```

### Publish a new version

You can bump the version, create a commit and associated tag with one command:

```bash
just version patch
```

```bash
just version minor
```

```bash
just version major
```

Your default Git text editor will open so you can add information about the release.

When you push the tag on GitHub, the workflow will automatically publish it on PyPi and a GitHub release will be created as draft.

## Serve the documentation

You can serve the Mkdocs documentation with:

```bash
just docs-serve
```

It'll automatically watch for changes in your code.

## License

This project is licensed under the terms of the MIT license.
