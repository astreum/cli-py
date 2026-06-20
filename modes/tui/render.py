import os
import sys
from datetime import datetime, timezone
from typing import List, Optional, Tuple

CURSOR_STYLE = "\x1b[47m\x1b[30m"
CURSOR_RESET = "\x1b[0m"

def build_block_summary(node) -> str:
    block = getattr(node, "latest_block", None)
    if block is None:
        attempts = getattr(node, "_block_fetch_attempts", 0)
        return f"  No blocks yet! ({attempts} queries)"
    height = block.height
    expr_hex = block.expr_id.hex()[:16] if block.expr_id else "0000000000000000"
    ts = block.timestamp
    if ts:
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        time_str = dt.strftime("%Y-%m-%d %H:%M UTC")
    else:
        time_str = "---"
    return f"  Block #{height}  \u2502  0x{expr_hex}  \u2502  {time_str}"

def build_node_status(node) -> str:
    chain = node.config.get("chain", "unknown")
    connected = "connected" if getattr(node, "is_connected", False) else "disconnected"
    peer_count = len(getattr(node, "peers", {}))
    peer_word = "peer" if peer_count == 1 else "peers"
    return f"  {chain}  \u2502  {connected}  \u2502  {peer_count} {peer_word}"


def apply_cursor_overlay(line: str, col: int, width: int) -> str:
    if col < 0 or col >= width:
        return line

    if col >= len(line):
        before = line.ljust(col)
        char = " "
        after = ""
    else:
        before = line[:col]
        char = line[col]
        after = line[col + 1 :]

    return f"{before}{CURSOR_STYLE}{char}{CURSOR_RESET}{after}"


def draw(app: "App"):
    """
    Renders the visible slice of 'lines' based on 'offset'.
    """
    buffer = ["\033[H"]

    cursor: Optional[Tuple[int, int]] = getattr(app, "cursor_position", None)

    for i in range(app.window_rows):
        line_idx = app.line_offset + i
        
        if line_idx < len(app.lines):
            clean_line = app.lines[line_idx][:app.window_cols]
        else:
            clean_line = ""

        if cursor is not None and line_idx == cursor[0]:
            clean_line = apply_cursor_overlay(clean_line, cursor[1], app.window_cols)

        clean_line = clean_line.ljust(app.window_cols)

        buffer.append(f"{clean_line}\n")

    sys.stdout.write("".join(buffer))
    sys.stdout.flush()

def render_app(app) -> None:
    """Render the shared header/body layout for an app instance."""
    lines: List[str] = ["","",""]

    lines.extend(app.header_block)
    lines.append("")
    lines.append(build_block_summary(app.node))
    lines.append(build_node_status(app.node))
    lines.append("")

    if app.flash_message:
        lines.append(app.flash_message)
        lines.append("")

    body_start = len(lines)
    page = app.pages.get(app.active_view)
    if page is None:
        page = app.pages["menu"]
        
    page.load_elements(app=app)
    body_lines, cursor_pos = page.render_with_cursor(cursor_active=app.input_focus)
    lines.extend(body_lines)
    app.body_lines = (
        (body_start, body_start + len(body_lines) - 1) if body_lines else None
    )
    lines.append("")

    app.lines = lines
    app.cursor_position = None
    if cursor_pos is not None and app.input_focus:
        app.cursor_position = (body_start + cursor_pos[0], cursor_pos[1])

    try:
        cols, rows = os.get_terminal_size()
    except OSError:
        cols, rows = 256, 128

    # Clamp to the max size we support.
    cols = min(cols, 256)
    rows = min(rows, 128)

    app.window_cols = cols
    app.window_rows = rows

    draw(app=app)
