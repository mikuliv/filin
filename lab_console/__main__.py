from __future__ import annotations

import argparse

import uvicorn

from .adapters import git_value
from .app import create_app
from .config import load_settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Локальная лабораторная консоль «Филин»")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8043)
    parser.add_argument("--development-mode", action="store_true")
    args = parser.parse_args()
    settings = load_settings(args.host, args.port, development_mode=args.development_mode)
    app = create_app(settings)
    print(f"Локальный адрес: http://{settings.host}:{settings.port}")
    print("Режим: лабораторный; production=false; внешний доступ=false")
    print(f"Git HEAD: {git_value('rev-parse', 'HEAD')}")
    print("candidate_id: v03154:65a3dd912d845bc1; runtime: runtime/lab_console")
    print(f"SQLite: ready; разрешённых задач: {len(app.state.catalog.tasks)}; token: ***")
    uvicorn.run(app, host=settings.host, port=settings.port, access_log=False)


if __name__ == "__main__":
    main()
