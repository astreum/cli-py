import sys
import uuid
from pathlib import Path
from typing import Any, Optional

from utils.config import persist_node_latest_block_hash
from utils.latest_block import start_latest_block_hash_poller
from astreum import Node, Expr
from modes.evaluation.script import load_script_to_environment


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

    evaluated_expr = None
    env_id: Optional[uuid.UUID] = None

    if script is not None:
        env = load_script_to_environment(script=script, node=node)
        env_id = uuid.uuid4()
        node.environments[env_id] = env

    try:
        match (script is not None, entry_expr_str is not None):
            case (True, True):
                evaluated_expr = node.script_eval(source=entry_expr_str, env_id=env_id)
            case (True, False):
                expr = Expr.Symbol("main")
                evaluated_expr = node.high_eval(expr=expr, env_id=env_id)
            case (False, True):
                evaluated_expr = node.script_eval(source=entry_expr_str)
            case (False, False):
                sys.stdout.write("Eval command requires --script or --expr.\n")
                sys.stdout.flush()
                return 1
    finally:
        stop_latest_block_hash_poller()
        if env_id is not None:
            node.environments.pop(env_id, None)
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
