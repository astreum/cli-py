
from typing import Any, Callable, List, Optional, Tuple, Union


class PageElement:
    def __init__(
        self,
        label: str,
        input: Optional[List[str]] = None,
        action: Optional[Callable[..., Any]] = None,
        input_index: Tuple[int, int] = (0, 0),
        next: Optional[str] = None,
        body: Optional[str] = None,
        header: bool = False,
        options: Optional[List[str]] = None,
        selected: int = 0,
        enabled: Union[bool, Callable[[], bool]] = True,
    ) -> None:
        self.label = label
        self.input = input
        self.action = action
        self.input_index = input_index
        self.next = next
        self.body = body
        self.header = header
        self.options = options
        self.selected = selected
        self.enabled = enabled

    @property
    def is_enabled(self) -> bool:
        if callable(self.enabled):
            return bool(self.enabled())
        return bool(self.enabled)

    @property
    def selectable(self) -> bool:
        return not self.header and self.is_enabled

    @property
    def selected_option(self) -> Optional[str]:
        if not self.options:
            return None
        return self.options[self.selected % len(self.options)]

    def cycle_option(self) -> None:
        if not self.options:
            return
        self.selected = (self.selected + 1) % len(self.options)

    def render(self, focus: bool = False) -> List[str]:
        if self.header:
            return [f"\x1b[1m{self.label}\x1b[0m"]

        enabled = self.is_enabled
        prefix = "> " if focus and enabled else "  "
        label = self.label if enabled else f"\x1b[2m{self.label}\x1b[0m"

        if self.options:
            choices = "  ".join(
                f"[{'x' if i == self.selected else ' '}] {name}"
                for i, name in enumerate(self.options)
            )
            lines: List[str] = [f"{prefix}{label}", f"  {choices}"]
        else:
            lines = [f"{prefix}{label}"]

        if self.input:
            for line in self.input:
                lines.append(f"  {line}")

        if self.body:
            for line in self.body.split("\n"):
                lines.append(f"  {line}")

        return lines

    def cursor_offset(self) -> Optional[Tuple[int, int]]:
        if not self.input:
            return None

        row, col = self.input_index
        row = max(0, min(row, len(self.input) - 1))
        col = max(0, min(col, len(self.input[row])))
        return (1 + row, 2 + col)


    def navigate_input(self, direction: str) -> bool:
        if not self.input:
            return False
        row, col = self.input_index
        row = max(0, min(row, len(self.input) - 1))
        col = max(0, min(col, len(self.input[row])))

        if direction == "up":
            if row == 0:
                return False
            row -= 1
            col = self._clamped_col(row, col)
        elif direction == "down":
            if row >= len(self.input) - 1:
                return False
            row += 1
            col = self._clamped_col(row, col)
        elif direction == "left":
            if col > 0:
                col -= 1
            else:
                if row == 0:
                    return False
                row -= 1
                col = self._last_col(row)
        elif direction == "right":
            current_len = len(self.input[row])
            if col < current_len:
                col += 1
            else:
                if row >= len(self.input) - 1:
                    return False
                row += 1
                col = 0
        else:
            raise ValueError(f"Unsupported direction: {direction}")

        self.input_index = (row, col)
        return True

    def _clamped_col(self, row: int, col: int) -> int:
        row_len = len(self.input[row])
        return min(col, row_len)

    def _last_col(self, row: int) -> int:
        row_len = len(self.input[row])
        return row_len
    
    def handle_input(self, char: str) -> None:
        if self.input is None:
            return

        row, col = self.input_index

        # Ensure row is within valid bounds
        if 0 <= row < len(self.input):
            current_line = self.input[row]
            
            # Insert the character using string slicing
            new_line = current_line[:col] + char + current_line[col:]
            self.input[row] = new_line
            
            # Advance the cursor to the right
            self.input_index = (row, col + 1)

    def handle_input_enter(self) -> None:
        if self.input is None:
            return

        row, col = self.input_index

        # Ensure the current row is valid
        if 0 <= row < len(self.input):
            current_line = self.input[row]

            # 1. Split the line:
            # 'left_part' stays on the current row.
            # 'right_part' moves down to the new row.
            left_part = current_line[:col]
            right_part = current_line[col:]

            # 2. Update the current row
            self.input[row] = left_part

            # 3. Insert the new row immediately after the current one
            self.input.insert(row + 1, right_part)

            # 4. Move the cursor to the start of the new line
            self.input_index = (row + 1, 0)

    def handle_input_delete(self) -> None:
        if not self.input:
            return

        row, col = self.input_index

        if not (0 <= row < len(self.input)):
            return

        current_line = self.input[row]
        col = max(0, min(col, len(current_line)))

        if col > 0:
            self.input[row] = current_line[:col - 1] + current_line[col:]
            self.input_index = (row, col - 1)
            return

        if row == 0:
            return

        previous_line = self.input[row - 1]
        new_col = len(previous_line)
        self.input[row - 1] = previous_line + current_line
        del self.input[row]
        self.input_index = (row - 1, new_col)

