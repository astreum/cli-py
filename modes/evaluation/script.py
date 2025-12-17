from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

from astreum import Env, Expr, Node, parse, tokenize

def load_script_to_environment(node: Node, script: str) -> Env:
    env_data: Dict[bytes, Expr] = {}
    _load_module_from_path(
        node=node,
        module_path=Path(script).expanduser(),
        env_data=env_data,
        current_prefix=None,
        active_stack=set(),
    )
    return Env(data=env_data)


def _load_module_from_path(
    node: Node,
    module_path: Path,
    env_data: Dict[bytes, Expr],
    current_prefix: Optional[str],
    active_stack: Set[Tuple[str, str]],
) -> None:
    normalized_path = module_path.expanduser()
    module_expr = _parse_module_expr(normalized_path)
    resolved_path = normalized_path.resolve()
    _process_module(
        node=node,
        module_expr=module_expr,
        env_data=env_data,
        current_prefix=current_prefix,
        module_dir=resolved_path.parent,
        origin=("path", str(resolved_path)),
        active_stack=active_stack,
    )


def _load_module_from_ref(
    node: Node,
    atom_id: bytes,
    env_data: Dict[bytes, Expr],
    current_prefix: Optional[str],
    active_stack: Set[Tuple[str, str]],
) -> None:
    module_expr = node.get_expr_list_from_storage(atom_id)
    if module_expr is None:
        raise ValueError(
            f"unable to load module script from reference '{atom_id.hex()}'"
        )
    if not isinstance(module_expr, Expr.ListExpr):
        raise ValueError("reference import must resolve to a list expression")
    _process_module(
        node=node,
        module_expr=module_expr,
        env_data=env_data,
        current_prefix=current_prefix,
        module_dir=None,
        origin=("ref", atom_id.hex()),
        active_stack=active_stack,
    )


def _process_module(
    node: Node,
    module_expr: Expr.ListExpr,
    env_data: Dict[bytes, Expr],
    current_prefix: Optional[str],
    module_dir: Optional[Path],
    origin: Tuple[str, str],
    active_stack: Set[Tuple[str, str]],
) -> None:
    if origin in active_stack:
        raise ValueError(
            f"circular import detected while loading '{origin[1]}'"
        )

    active_stack.add(origin)

    entries = _collect_definition_entries(module_expr=module_expr)
    local_name_map = _build_definition_name_map(
        entries=entries, current_prefix=current_prefix
    )

    try:
        for index, first_expr, second_expr, terminator_expr in entries:
            if terminator_expr.value == "def":
                _register_definition(
                    index=index,
                    value_expr=first_expr,
                    name_expr=second_expr,
                    env_data=env_data,
                    current_prefix=current_prefix,
                    local_name_map=local_name_map,
                )
            elif terminator_expr.value == "import":
                _handle_import(
                    node=node,
                    index=index,
                    prefix_expr=first_expr,
                    path_expr=second_expr,
                    env_data=env_data,
                    module_dir=module_dir,
                    current_prefix=current_prefix,
                    active_stack=active_stack,
                )
            else:
                raise ValueError(
                    f"definition {index} must terminate with def or import symbol"
                )
    finally:
        active_stack.remove(origin)


def _register_definition(
    index: int,
    value_expr: Expr,
    name_expr: Expr,
    env_data: Dict[bytes, Expr],
    current_prefix: Optional[str],
    local_name_map: Dict[str, str],
) -> None:
    if not isinstance(name_expr, Expr.Symbol):
        raise ValueError(f"definition {index} name must be a symbol")

    qualified_name = local_name_map.get(
        name_expr.value, _join_prefix(current_prefix, name_expr.value)
    )
    rewritten_value = (
        _rewrite_expr_symbols(value_expr=value_expr, replacements=local_name_map)
        if current_prefix
        else value_expr
    )
    try:
        key = qualified_name.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError(f"definition {index} name must be valid utf-8") from exc

    env_data[key] = rewritten_value


def _handle_import(
    node: Node,
    index: int,
    prefix_expr: Expr,
    path_expr: Expr,
    env_data: Dict[bytes, Expr],
    module_dir: Optional[Path],
    current_prefix: Optional[str],
    active_stack: Set[Tuple[str, str]],
) -> None:
    if not isinstance(prefix_expr, Expr.Symbol):
        raise ValueError(f"definition {index} import prefix must be a symbol")

    import_prefix = _join_prefix(current_prefix, prefix_expr.value)
    if _is_ref_import(path_expr):
        atom_bytes = _expr_to_bytes(path_expr.elements[0])
        if not atom_bytes:
            raise ValueError(
                f"definition {index} import ref must provide valid atom id"
            )
        _load_module_from_ref(
            node=node,
            atom_id=atom_bytes,
            env_data=env_data,
            current_prefix=import_prefix,
            active_stack=active_stack,
        )
        return

    import_path_str = _import_path_from_expr(index=index, path_expr=path_expr)
    import_path = Path(import_path_str).expanduser()
    if not import_path.is_absolute():
        if module_dir is None:
            raise ValueError(
                f"definition {index} relative import requires a module directory"
            )
        import_path = module_dir / import_path

    _load_module_from_path(
        node=node,
        module_path=import_path,
        env_data=env_data,
        current_prefix=import_prefix,
        active_stack=active_stack,
    )


def _import_path_from_expr(index: int, path_expr: Expr) -> str:
    if isinstance(path_expr, Expr.Bytes):
        try:
            return path_expr.value.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(
                f"definition {index} import path must be valid utf-8"
            ) from exc
    if isinstance(path_expr, Expr.Symbol):
        return _strip_wrapping_quotes(path_expr.value)

    raise ValueError(
        f"definition {index} import path must be a symbol or bytes expression"
    )


def _is_ref_import(path_expr: Expr) -> bool:
    return (
        isinstance(path_expr, Expr.ListExpr)
        and len(path_expr.elements) == 2
        and isinstance(path_expr.elements[1], Expr.Symbol)
        and path_expr.elements[1].value == "ref"
    )


def _join_prefix(current_prefix: Optional[str], name: str) -> str:
    return f"{current_prefix}.{name}" if current_prefix else name


def _strip_wrapping_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _parse_module_expr(module_path: Path) -> Expr.ListExpr:
    try:
        raw_contents = module_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"unable to read module script at '{module_path}'") from exc

    module_str = raw_contents.replace("\r\n", "\n").replace("\r", "\n")
    tokens = tokenize(module_str)
    module_expr, remainder = parse(tokens=tokens)
    if remainder:
        raise ValueError("unexpected trailing tokens while parsing module script")
    if not isinstance(module_expr, Expr.ListExpr):
        raise ValueError("module script must resolve to a list expression of definitions")
    return module_expr


def _expr_to_bytes(expr: Expr) -> Optional[bytes]:
    if isinstance(expr, Expr.Bytes):
        return expr.value
    if isinstance(expr, Expr.Symbol):
        data = expr.value.strip()
        if data.startswith(("0x", "0X")):
            data = data[2:]
        if len(data) % 2:
            data = "0" + data
        try:
            return bytes.fromhex(data)
        except ValueError:
            return None
    return None


def _collect_definition_entries(
    module_expr: Expr.ListExpr,
) -> List[Tuple[int, Expr, Expr, Expr.Symbol]]:
    entries: List[Tuple[int, Expr, Expr, Expr.Symbol]] = []
    for index, definition in enumerate(module_expr.elements):
        if not isinstance(definition, Expr.ListExpr):
            raise ValueError(f"definition {index} must be a list expression")
        if len(definition.elements) != 3:
            raise ValueError(
                f"definition {index} must contain value, name, and def symbol"
            )

        first_expr, second_expr, terminator_expr = definition.elements
        if not isinstance(terminator_expr, Expr.Symbol):
            raise ValueError(
                f"definition {index} must terminate with def or import symbol"
            )

        entries.append((index, first_expr, second_expr, terminator_expr))
    return entries


def _build_definition_name_map(
    entries: Sequence[Tuple[int, Expr, Expr, Expr.Symbol]],
    current_prefix: Optional[str],
) -> Dict[str, str]:
    name_map: Dict[str, str] = {}
    for index, _, name_expr, terminator_expr in entries:
        if terminator_expr.value != "def":
            continue
        if not isinstance(name_expr, Expr.Symbol):
            raise ValueError(f"definition {index} name must be a symbol")
        name_map[name_expr.value] = _join_prefix(
            current_prefix=current_prefix, name=name_expr.value
        )
    return name_map


def _rewrite_expr_symbols(value_expr: Expr, replacements: Dict[str, str]) -> Expr:
    if isinstance(value_expr, Expr.Symbol):
        replacement = replacements.get(value_expr.value)
        if replacement and replacement != value_expr.value:
            return Expr.Symbol(replacement)
        return value_expr

    if isinstance(value_expr, Expr.ListExpr):
        changed = False
        new_elements: List[Expr] = []
        for element in value_expr.elements:
            rewritten = _rewrite_expr_symbols(element, replacements)
            if rewritten is not element:
                changed = True
            new_elements.append(rewritten)
        if changed:
            return Expr.ListExpr(new_elements)
        return value_expr

    return value_expr
