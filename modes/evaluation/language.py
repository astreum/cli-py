import sys
import uuid
from pathlib import Path
from typing import Any, List, Optional

from utils.config import persist_node_latest_block_hash
from utils.latest_block import start_latest_block_hash_poller
from astreum import Node, Expr, parse, tokenize
from astreum.machine.main import Machine
from astreum.machine.models.environment import Env
from modes.evaluation.script import load_script_to_environment


def _link_to_list(link: Expr) -> List[Expr]:
    """Unroll a right-linked Link chain into a Python list."""
    result: List[Expr] = []
    while isinstance(link, Expr.Link):
        if link.head is None and link.tail is None:
            break
        result.append(link.head)
        link = link.tail
    return result


def _list_to_link(items: List[Expr]) -> Expr:
    """Build a right-linked Link chain from a Python list."""
    if not items:
        return Expr.Link(None, None)
    result: Expr = items[-1]
    for item in reversed(items[:-1]):
        result = Expr.Link(item, result)
    return result


def _build_param_symbols(count: int) -> Expr:
    """Build a Link chain of param symbols: ($0 $1 ... $N-1)."""
    symbols = [Expr.Symbol(f"${i}") for i in range(count)]
    return _list_to_link(symbols)


def _wrap_as_fn_call(args: List[Expr], body: Expr) -> Expr:
    """Wrap args and a body expression into an implicit fn call.

    Produces: (argN ... arg1 (quote ($0 ... $N-1)) (quote body) fn)
    """
    n = len(args)
    param_chain = _build_param_symbols(n)
    quoted_params = Expr.Link(Expr.Symbol("quote"), param_chain)
    quoted_body = Expr.Link(Expr.Symbol("quote"), body)

    # Build the full expression: args... then quoted_params, quoted_body, fn
    all_parts = list(args) + [quoted_params, quoted_body, Expr.Symbol("fn")]
    return _list_to_link(all_parts)


def eval_lang(
    *,
    script: Optional[str],
    entry_expr_str: Optional[str],
    data_dir: Path,
    configs: dict[str, Any],
    node: Node,
) -> int:
    poll_interval = configs["cli"]["latest_block_hash_poll_interval"]
    stop_latest_block_hash_poller = start_latest_block_hash_poller(
        node=node,
        data_dir=data_dir,
        poll_interval=poll_interval,
    )

    evaluated_expr: Optional[Expr] = None
    env: Env = Env()

    if script is not None:
        env = load_script_to_environment(script=script, node=node)

    try:
        if entry_expr_str is not None:
            machine = Machine(node=node, meter_enabled=False)
            tokens = tokenize(entry_expr_str)
            entry_expr, remainder = parse(tokens)

            # Implicit fn-call convention:
            # If the expression is a Link chain ending with a non-operator
            # symbol (a function name), treat preceding items as args and
            # wrap as (args... (quote params) (quote body) fn).
            elems = _link_to_list(entry_expr) if isinstance(entry_expr, Expr.Link) else []
            if (
                len(elems) >= 2
                and isinstance(elems[-1], Expr.Symbol)
                and elems[-1].value not in _OPERATOR_SYMBOLS
            ):
                func_name = elems[-1].value
                args = elems[:-1]
                body = env.get(func_name)
                if body is None:
                    sys.stdout.write(f"error: '{func_name}' not defined in environment\n")
                    sys.stdout.flush()
                    return 1
                call_expr = _wrap_as_fn_call(args, body)
                evaluated_expr = machine.run(expr=call_expr, env=env)
            else:
                evaluated_expr = machine.run(expr=entry_expr, env=env)

        elif script is not None:
            # No --expr given, evaluate the symbol 'main' as entry point
            machine = Machine(node=node, meter_enabled=False)
            evaluated_expr = machine.run(expr=Expr.Symbol("main"), env=env)

    finally:
        stop_latest_block_hash_poller()
        latest_hash = node.latest_block_hash
        if latest_hash is not None:
            persist_node_latest_block_hash(
                data_dir=data_dir,
                latest_block_hash=latest_hash,
                logger=node.logger,
            )

    if evaluated_expr is not None:
        sys.stdout.write(f"{evaluated_expr}\n")
        sys.stdout.flush()
        return 0
    return 0


_OPERATOR_SYMBOLS = {
    "+", "add", "-", "sub", "*", "mul", "/", "div", "%", "mod",
    "&", "and", "|", "or", "^", "xor",
    "<<", ">>>", ">>", "rol", "ror",
    "fadd", "fsub", "fmul", "fdiv", "fsqrt",
    "~", "not",
    "fn", "if", "def",
    "link", "head", "tail", "is_atom", "is_eq",
    "quote",
    "spawn", "send", "receive",
}
