from __future__ import annotations

from astreum._node import Expr, parse, tokenize


def expression_from_string(source: str) -> Expr:
    normalized = source.replace("\r\n", "\n").replace("\r", "\n")
    tokens = tokenize(normalized)
    expr, remainder = parse(tokens=tokens)
    if remainder:
        raise ValueError("unexpected trailing tokens while parsing expression")
    return expr
