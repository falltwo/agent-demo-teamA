"""將 FastAPI OpenAPI 結構寫入 contracts/openapi.json，供前端 openapi-typescript 使用。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.main import create_app


def main() -> None:
    root = _ROOT
    out = root / "contracts" / "openapi.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    app = create_app()
    schema = app.openapi()
    out.write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
