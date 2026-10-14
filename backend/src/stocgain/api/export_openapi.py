"""Export deterministic API schema without a running database or web server."""

import json
import sys
from pathlib import Path

from stocgain.api.app import create_app


def export_openapi(path: Path) -> None:
    """Write sorted OpenAPI JSON for generated frontend types (docs/02 §9.2)."""
    path.write_text(json.dumps(create_app().openapi(), indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    export_openapi(Path(sys.argv[1]))
