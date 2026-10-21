import sys
import uuid
from pathlib import Path
from typing import Any, List, Optional

from utils.config import persist_node_latest_block_hash
from utils.latest_block import start_latest_block_hash_poller
from astreum import Node, Expr, parse, tokenize
from astreum.machine import assemble_env
from astreum.machine.main import Machine
from astreum.machine.operators.main import OPERATOR_LIST
from astreum.machine.environment import Env
from astreum.expression import link, symbol, NIL


def _link_to_list(link: Expr) -> List[Expr]:
    """Unroll a right-linked Link chain into a Python list."""
    result: List[Expr] = []
    while link.base == "link":
        if link.head is None and link.tail is None:
            break
        result.append(link.head)
        if link.tail is None or link.tail.base != "link":
            if link.tail is not None:
                result.append(link.tail)
            break
        link = link.tail
    return result


def _list_to_link(items: List[Expr]) -> Expr:
    """Build a right-linked Link chain from a Python list."""
    if not items:
        return NIL
    result: Expr = items[-1]
    for item in reversed(items[:-1]):
        result = link(item, result)
    return result


MAX_CALL_ARGS = 6


def _build_param_symbols(count: int) -> Expr:
    """Build a NIL-ended Link chain of param symbols: (n), (n m), etc."""
    names = ["n", "m", "o", "p", "q", "r"]
    chain: Expr = NIL
    for name in reversed(names[:count]):
        chain = link(symbol(name), chain)
    return chain


def _quote(value: Expr) -> Expr:
    """Build the quoted form the parser builds for 'value."""
    return link(symbol("'"), link(value, NIL))


def _wrap_as_fn_call(args: List[Expr], body: Expr) -> Expr:
    """Wrap args and a body expression into an implicit closure call.

    Produces: (arg1 ... argN '(n ...) 'body closure apply)
    """
    param_chain = _build_param_symbols(len(args))
    all_parts = list(args) + [
        _quote(param_chain),
        _quote(body),
        symbol("closure"),
        symbol("apply"),
    ]
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

    try:
        if entry_expr_str is not None:
            machine = Machine(node=node, meter_limit=None)
            tokens = tokenize(entry_expr_str)
            entry_expr, remainder = parse(tokens)

            # Implicit function-call convention:
            # If the expression is a Link chain ending with a non-operator
            # symbol (a function name), treat preceding items as args and
            # wrap as (args... '(params) 'body closure apply).
            elems = _link_to_list(entry_expr) if entry_expr.base == "link" else []
            if (
                len(elems) >= 2
                and elems[-1].base == "symbol"
                and elems[-1].value not in OPERATOR_LIST
            ):
                func_name = elems[-1].value
                args = elems[:-1]

                if len(args) > MAX_CALL_ARGS:
                    sys.stdout.write(
                        f"error: at most {MAX_CALL_ARGS} arguments, got {len(args)}\n"
                    )
                    sys.stdout.flush()
                    return 1

                if script is None:
                    sys.stdout.write(f"error: implicit fn-call requires --script\n")
                    sys.stdout.flush()
                    return 1

                env = assemble_env(node=node, script=script, target=func_name)
                body = env.get(func_name)
                if body is None:
                    sys.stdout.write(f"error: '{func_name}' not defined in '{script}'\n")
                    sys.stdout.flush()
                    return 1
                call_expr = _wrap_as_fn_call(args, body)
                evaluated_expr = machine.run(expr=call_expr, env=env)
            else:
                if script is not None:
                    env = assemble_env(node=node, script=script, target=entry_expr_str)
                evaluated_expr = machine.run(expr=entry_expr, env=env)

        elif script is not None:
            machine = Machine(node=node, meter_limit=None)
            env = assemble_env(node=node, script=script, target="main")
            evaluated_expr = machine.run(expr=symbol("main"), env=env)

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
