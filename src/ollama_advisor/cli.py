"""Command-line interface for ollama-advisor."""

from __future__ import annotations

import argparse
import json
import sys

from . import ctl
from .core import recommend
from .system import format_specs_summary, get_system_specs


def _print_df(df) -> None:
    if df.empty:
        print("추천 가능한 모델이 없습니다.")
        summary = df.attrs.get("system_summary")
        if summary:
            print(f"시스템: {summary}")
        return
    print(df.to_string(index=False))
    summary = df.attrs.get("system_summary")
    if summary:
        print(f"\n시스템: {summary}")


def _cmd_recommend(args: argparse.Namespace) -> int:
    df = recommend(
        purpose=args.purpose,
        as_dataframe=True,
        top_n=args.top,
        force_refresh=args.force_refresh,
    )
    _print_df(df)
    return 0


def _cmd_pull(args: argparse.Namespace) -> int:
    ctl.pull_model(args.name, stream=not args.quiet)
    print(f"Downloaded: {args.name}")
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    output = ctl.run_model(args.name, prompt=args.prompt)
    print(output)
    return 0


def _cmd_stop(args: argparse.Namespace) -> int:
    ctl.stop_model(args.name)
    print(f"Stopped: {args.name}")
    return 0


def _cmd_list(_args: argparse.Namespace) -> int:
    models = ctl.list_installed()
    if not models:
        print("설치된 모델이 없습니다.")
        return 0
    print(json.dumps(models, indent=2, ensure_ascii=False))
    return 0


def _cmd_ps(_args: argparse.Namespace) -> int:
    running = ctl.list_running()
    if not running:
        print("실행 중인 모델이 없습니다.")
        return 0
    print(json.dumps(running, indent=2, ensure_ascii=False))
    return 0


def _cmd_specs(_args: argparse.Namespace) -> int:
    specs = get_system_specs()
    print(json.dumps(specs, indent=2, ensure_ascii=False))
    print(format_specs_summary(specs))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ollama-advisor",
        description="Recommend and manage Ollama models for your hardware.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    rec = sub.add_parser("recommend", help="Recommend models for this machine")
    rec.add_argument(
        "--purpose",
        default="all",
        choices=["all", "general", "coding", "reasoning", "vision", "embedding", "audio"],
        help="Filter by use case",
    )
    rec.add_argument("--top", type=int, default=None, help="Limit number of results")
    rec.add_argument(
        "--force-refresh",
        action="store_true",
        help="Re-fetch catalog from ollama.com",
    )
    rec.set_defaults(func=_cmd_recommend)

    pull = sub.add_parser("pull", help="Download a model")
    pull.add_argument("name", help="Model tag, e.g. qwen2.5-coder:7b")
    pull.add_argument("--quiet", action="store_true", help="Disable progress stream")
    pull.set_defaults(func=_cmd_pull)

    run = sub.add_parser("run", help="Run a single prompt")
    run.add_argument("name", help="Model tag")
    run.add_argument("--prompt", required=True, help="Prompt text")
    run.set_defaults(func=_cmd_run)

    stop = sub.add_parser("stop", help="Unload a running model")
    stop.add_argument("name", help="Model tag")
    stop.set_defaults(func=_cmd_stop)

    lst = sub.add_parser("list", help="List installed models")
    lst.set_defaults(func=_cmd_list)

    ps = sub.add_parser("ps", help="List running models")
    ps.set_defaults(func=_cmd_ps)

    specs = sub.add_parser("specs", help="Show detected system specs")
    specs.set_defaults(func=_cmd_specs)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ctl.OllamaError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
