import argparse
from typing import Any, List, Optional
from modes.headless import run_headless
from modes.evaluation.language import eval_lang
from modes.tui import run_tui
from utils.config import load_config, load_node_latest_block_hash
from utils.data import ensure_data_dir

_ARG_UNSET = object()

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Astreum CLI")
    
    parser.add_argument(
        "--tui",
        dest="tui_mode",
        action="store_true",
        help="Launches TUI",
    )
    parser.add_argument(
        "--headless",
        dest="headless_mode",
        action="store_true",
        help="Run startup actions without launching the TUI",
    )
    parser.add_argument(
        "--eval",
        dest="eval_mode",
        action="store_true",
        help="Enable evaluation mode instead of launching the GUI",
    )
    parser.add_argument("--script", type=str, help="Path to a script file", default=None)
    parser.add_argument(
        "--expr",
        type=str,
        help="Postfix expression to evaluate (e.g., '(a b main)')",
        default=None,
    )
    parser.add_argument(
        "--node-default-seed",
        nargs="?",
        const="none",
        default=_ARG_UNSET,
        help="Override the node default seed; omit value (or use 'none') to clear.",
    )
    return parser


def _coerce_config_value(raw_value: str) -> Any:
    """Attempt to convert the raw CLI value into a native Python type."""
    lowered = raw_value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"none", "null"}:
        return None

    try:
        if raw_value.startswith(("0x", "0X")):
            raise ValueError
        return int(raw_value, 10)
    except ValueError:
        pass

    try:
        return float(raw_value)
    except ValueError:
        return raw_value


def _parse_config_overrides(
    parser: argparse.ArgumentParser,
    raw_args: List[str],
) -> dict[str, dict[str, Any]]:
    """Extract --cli-* and --node-* overrides from unknown CLI arguments."""
    overrides: dict[str, dict[str, Any]] = {"cli": {}, "node": {}}
    if not raw_args:
        return overrides

    idx = 0
    arg_count = len(raw_args)
    while idx < arg_count:
        token = raw_args[idx]
        if not token.startswith("--"):
            parser.error(f"Unrecognized argument: {token}")

        option = token
        explicit_value: Optional[str] = None
        if "=" in token:
            option, explicit_value = token.split("=", 1)

        if option.startswith("--cli-"):
            scope = "cli"
            key = option[len("--cli-"):]
        elif option.startswith("--node-"):
            scope = "node"
            key = option[len("--node-"):]
        else:
            parser.error(f"Unknown option {token}")

        if not key:
            parser.error(f"Missing config key in {token}")

        value = explicit_value
        if value is None:
            next_idx = idx + 1
            if next_idx < arg_count and not raw_args[next_idx].startswith("--"):
                value = raw_args[next_idx]
                idx += 1
            else:
                value = "true"

        normalized_key = key.replace("-", "_")
        overrides[scope][normalized_key] = _coerce_config_value(value)
        idx += 1

    return overrides


def _apply_config_overrides(
    configs: dict[str, Any], overrides: dict[str, dict[str, Any]]
) -> None:
    """Merge parsed overrides into the loaded configuration."""
    for scope, scope_overrides in overrides.items():
        if not scope_overrides:
            continue
        target = configs.setdefault(scope, {})
        target.update(scope_overrides)


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args, unknown_args = parser.parse_known_args(argv)
    config_overrides = _parse_config_overrides(parser, unknown_args)
    if args.node_default_seed is not _ARG_UNSET:
        config_overrides["node"]["default_seed"] = _coerce_config_value(
            args.node_default_seed
        )

    selected_modes = sum(
        bool(flag)
        for flag in (args.tui_mode, args.headless_mode, args.eval_mode)
    )
    if selected_modes > 1:
        parser.error("Select only one mode: --tui, --headless, or --eval.")

    data_dir = ensure_data_dir()
    configs = load_config(data_dir)
    _apply_config_overrides(configs, config_overrides)
    configs.setdefault("node", {}).pop("latest_block_hash", None)
    latest_hash = load_node_latest_block_hash(data_dir)
    if latest_hash is not None:
        configs["node"]["latest_block_hash"] = f"0x{latest_hash.hex()}"
    if args.headless_mode:
        return run_headless(
            data_dir=data_dir,
            configs=configs,
        )
    elif args.tui_mode:
        return run_tui(data_dir=data_dir, configs=configs)
    
    elif args.eval_mode:
        return eval_lang(
            script=args.script,
            entry_expr_str=args.expr,
            data_dir=data_dir,
            configs=configs,
        )


if __name__ == "__main__":
    raise SystemExit(main())
