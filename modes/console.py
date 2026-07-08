import signal
import sys
from pathlib import Path
from typing import Any

from astreum.machine.main import Machine
from astreum.machine.models.environment import Env
from astreum.machine.tokenizer import tokenize
from astreum.machine.parser import parse
from astreum.machine.evaluation.main import evaluation


def run_console(*, data_dir: Path, configs: dict[str, Any], node: "Node") -> int:
    machine = Machine(node=node, meter_limit=None, mode="dynamic")
    env = Env()

    sys.stderr.write("Console mode — enter expressions, Ctrl+C to exit.\n")
    sys.stderr.flush()

    try:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue

            try:
                tokens = tokenize(line)
                expr, _ = parse(tokens)
                
                stack = []
                result = evaluation(machine, expr, stack, env)
                
                if result:
                    for item in result:
                        sys.stdout.write(f"{item}\n")
                sys.stdout.flush()

            except Exception as e:
                sys.stderr.write(f"Error: {e}\n")
                sys.stderr.flush()

    except KeyboardInterrupt:
        sys.stderr.write("\nExiting.\n")
        sys.stderr.flush()

    return 0
