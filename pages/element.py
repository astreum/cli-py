
from typing import Any, Callable, List, Optional, Tuple


class PageElement:
    def __init__(
        self,
        label: str,
        input: Optional[List[str]] = None,
        action: Optional[Callable[..., Any]] = None,
        input_index: Tuple[int, int] = (0, 0),
        next: Optional[str] = None,
        body: Optional[str] = None
    ) -> None:
        self.label = label
        self.input = input
        self.action = action
        self.input_index = input_index
        self.next = next
        self.body = body

    def render(self, focus: bool = False, cursor_effect: bool = False) -> List[str]:
        prefix = "> " if focus else "  "
        lines: List[str] = [f"{prefix}{self.label}"]

        if self.input:
            for row, line in enumerate(self.input):
                rendered_line = line

                if focus and row == self.input_index[0]:
                    col = self.input_index[1]

                    if 0 <= col <= len(line):
                        if cursor_effect:
                            if col < len(line):
                                rendered_line = f"{line[:col]}_{line[col+1:]}"
                            else:
                                if line == "":
                                    rendered_line = f" "
                                else:
                                    rendered_line = f"{line}"

                lines.append(f"  {rendered_line}")

        if self.body:
            for line in self.body.split("\n"):
                lines.append(f"  {line}")

        return lines


    def navigate_input(self, direction: str) -> bool:
        if not self.input:
            return False
        row, col = self.input_index
        row = max(0, min(row, len(self.input) - 1))
        col = max(0, col)

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
            if current_len == 0:
                if row >= len(self.input) - 1:
                    return False
                row += 1
                col = 0
            elif col < current_len - 1:
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
        if row_len == 0:
            return 0
        return min(col, row_len - 1)

    def _last_col(self, row: int) -> int:
        row_len = len(self.input[row])
        return max(row_len - 1, 0)
    
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
        if self.input is None:
            return

        row, col = self.input_index

        # Case 1: Simple deletion within the line
        if col > 0:
            current_line = self.input[row]
            # Remove the character at index col-1
            self.input[row] = current_line[:col - 1] + current_line[col:]
            # Move cursor back one space
            self.input_index = (row, col - 1)

        # Case 2: Start of line (Merge with previous line)
        elif row > 0:
            current_line = self.input[row]
            previous_line = self.input[row - 1]
            
            # The cursor should land where the previous line ended
            new_col = len(previous_line)
            
            # Merge: Append current line to the previous one
            self.input[row - 1] = previous_line + current_line
            
            # Remove the current line (now merged)
            del self.input[row]
            
            # Move cursor up to the merge point
            self.input_index = (row - 1, new_col)
