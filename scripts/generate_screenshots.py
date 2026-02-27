"""Generate SVG screenshots of the OpenAPI TUI for documentation purposes."""

import asyncio
import re
import sys
from pathlib import Path

PETSTORE_URL = "https://petstore3.swagger.io/api/v3/openapi.json"
OUTPUT_DIR = Path(__file__).parent.parent / "docs" / "images"
DISPLAY_WIDTH = 800


async def generate() -> None:
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from openapi_tools._parser import OpenAPIParser
    from openapi_tools.tui.app import OpenAPITUIApp

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Fetching schema from {PETSTORE_URL} …")
    parser = OpenAPIParser.from_source(PETSTORE_URL)

    screenshots: dict[str, str] = {}

    async def auto_pilot(pilot: object) -> None:
        from textual.pilot import Pilot

        assert isinstance(pilot, Pilot)

        await pilot.pause()
        await pilot.pause()

        screenshots["tui-endpoints"] = pilot.app.export_screenshot(
            title="OpenAPI TUI – Endpoints"
        )

        await pilot.press("down")
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        await pilot.pause()

        screenshots["tui-endpoint-detail"] = pilot.app.export_screenshot(
            title="OpenAPI TUI – Endpoint detail"
        )

        await pilot.press("s")
        await pilot.pause()
        await pilot.pause()

        screenshots["tui-schemas"] = pilot.app.export_screenshot(
            title="OpenAPI TUI – Schemas"
        )

        await pilot.press("down")
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        await pilot.pause()

        screenshots["tui-schema-detail"] = pilot.app.export_screenshot(
            title="OpenAPI TUI – Schema detail"
        )

        await pilot.app.action_quit()

    app = OpenAPITUIApp(parser, source=PETSTORE_URL)
    await app.run_async(headless=True, size=(160, 58), auto_pilot=auto_pilot)

    for name, svg in screenshots.items():
        svg = _set_display_width(svg, DISPLAY_WIDTH)
        path = OUTPUT_DIR / f"{name}.svg"
        path.write_text(svg, encoding="utf-8")
        print(f"Saved {path}")

    print("Done.")


def _set_display_width(svg: str, width: int) -> str:
    """Inject a width attribute so browsers render the SVG at a fixed pixel size."""
    return re.sub(
        r'(<svg\b[^>]*?)(viewBox="0 0 ([\d.]+) ([\d.]+)")',
        lambda m: (
            f'{m.group(1)}width="{width}" '
            f'height="{round(float(m.group(4)) * width / float(m.group(3)))}" '
            f"{m.group(2)}"
        ),
        svg,
        count=1,
    )


if __name__ == "__main__":
    asyncio.run(generate())
