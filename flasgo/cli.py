from __future__ import annotations

import argparse
import importlib
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

from .app import Flasgo


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="flasgo")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run a Flasgo application")
    run_parser.add_argument("target", help="Python file path or import string such as app.py or package.module:app")
    run_parser.add_argument("--app", default="app", help="Application variable name when loading from a Python file")
    run_parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind")
    run_parser.add_argument("--port", type=int, default=8000, help="Port to bind")
    run_parser.add_argument(
        "--reload",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Enable or disable automatic reload. Defaults to app settings DEBUG when omitted.",
    )
    run_parser.add_argument(
        "--reload-dir",
        dest="reload_dirs",
        action="append",
        default=None,
        help="Additional directory to watch for reload. Can be specified multiple times.",
    )
    run_parser.set_defaults(handler=_run_command)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = args.handler
    return int(handler(args))


def _run_command(args: argparse.Namespace) -> int:
    app = load_app(args.target, app_name=args.app)
    reload_dirs = args.reload_dirs
    if Path(args.target).suffix == ".py" and reload_dirs is None:
        reload_dirs = [str(Path(args.target).expanduser().resolve().parent)]
    app.run(
        host=args.host,
        port=args.port,
        reload=args.reload,
        reload_dirs=reload_dirs,
    )
    return 0


def load_app(target: str, *, app_name: str = "app") -> Flasgo:
    if ":" in target:
        module_path, attr_name = target.split(":", 1)
        module = importlib.import_module(module_path)
        resolved_name = attr_name.strip() or app_name
    elif target.endswith(".py"):
        module = _load_module_from_path(Path(target))
        resolved_name = app_name
    else:
        module = importlib.import_module(target)
        resolved_name = app_name

    candidate = getattr(module, resolved_name, None)
    if not isinstance(candidate, Flasgo):
        msg = f"Target '{target}' did not resolve to a Flasgo app named '{resolved_name}'."
        raise SystemExit(msg)
    return candidate


def _load_module_from_path(path: Path) -> ModuleType:
    resolved = path.expanduser().resolve()
    if not resolved.exists():
        raise SystemExit(f"Python file not found: {resolved}")
    if resolved.suffix != ".py":
        raise SystemExit(f"Expected a .py file path, got: {resolved}")
    module_name = f"_flasgo_cli_{resolved.stem}_{abs(hash(resolved))}"
    spec = importlib.util.spec_from_file_location(module_name, resolved)
    if spec is None or spec.loader is None:
        raise SystemExit(f"Could not load module from: {resolved}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    raise SystemExit(main())
