from __future__ import annotations

from pathlib import Path
from typing import Dict

from astreum._node import Env, Expr, parse, tokenize


def load_script_to_environment(script: str) -> Env:
    module_path = Path(script).expanduser()
    try:
        raw_contents = module_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"unable to read module script at '{script}'") from exc

    module_str = raw_contents.replace("\r\n", "\n").replace("\r", "\n")
    tokens = tokenize(module_str)
    module_expr, remainder = parse(tokens=tokens)
    if remainder:
        raise ValueError("unexpected trailing tokens while parsing module script")
    if not isinstance(module_expr, Expr.ListExpr):
        raise ValueError("module script must resolve to a list expression of definitions")

    env_data: Dict[bytes, Expr] = {}
    for index, definition in enumerate(module_expr.elements):
        if not isinstance(definition, Expr.ListExpr):
            raise ValueError(f"definition {index} must be a list expression")
        if len(definition.elements) != 3:
            raise ValueError(f"definition {index} must contain value, name, and def symbol")

        value_expr, name_expr, def_expr = definition.elements

        if not isinstance(name_expr, Expr.Symbol):
            raise ValueError(f"definition {index} name must be a symbol")
        if not (isinstance(def_expr, Expr.Symbol) and def_expr.value == "def"):
            raise ValueError(f"definition {index} must terminate with def symbol")

        try:
            key = name_expr.value.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ValueError(f"definition {index} name must be valid utf-8") from exc

        env_data[key] = value_expr

    env = Env(data=env_data)
    return env
