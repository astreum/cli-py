import os
import sys
from typing import List


def draw(app: "App"):
    """
    Renders the visible slice of 'lines' based on 'offset'.
    """
    buffer = ["\033[H"]

    for i in range(app.window_rows):
        line_idx = app.line_offset + i
        
        if line_idx < len(app.lines):
            clean_line = app.lines[line_idx][:app.window_cols]
            clean_line = clean_line.ljust(app.window_cols)
        else:
            clean_line = " " * app.window_cols

        buffer.append(f"{clean_line}\n")

    sys.stdout.write("".join(buffer))
    sys.stdout.flush()

def render_app(app, cursor_effect: bool = False) -> None:
    """Render the shared header/body/footer layout for an app instance."""
    lines: List[str] = ["","",""]

    lines.extend(app.header_block)
    lines.append("")

    if app.flash_message:
        lines.append(app.flash_message)
        lines.append("")

    body_start = len(lines)
    page = app.pages.get(app.active_view)
    if page is None:
        page = app.pages["menu"]
        
    page.load_elements(app=app)
    body_lines = page.render(cursor_effect=cursor_effect)
    lines.extend(body_lines)
    app.body_lines = (
        (body_start, body_start + len(body_lines) - 1) if body_lines else None
    )
    lines.append("")

    footer_start = len(lines)
    lines.append(app.footer_text)
    app.footer_lines = (footer_start, footer_start)

    app.lines = lines

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
