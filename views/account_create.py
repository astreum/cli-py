from typing import Callable, List


class CreateAccountPage:
    """Simple create-account form with input focus and submit button."""

    def __init__(self) -> None:
        self.name: str = ""
        self.focus_index: int = 0  # 0 = input, 1 = submit button
        self.message: str = ""

    def prepare_for_entry(self) -> None:
        self.focus_index = 0
        self.message = ""
        self.name = ""

    def cycle_focus(self) -> None:
        self.focus_index = (self.focus_index + 1) % 2

    def handle_char(self, key: str) -> bool:
        if self.focus_index != 0:
            return False
        if key == "\x08":  # backspace
            if self.name:
                self.name = self.name[:-1]
                return True
            return False
        if len(key) == 1 and key.isprintable():
            self.name += key
            return True
        return False

    def handle_enter(self, submit_callback: Callable[[str], tuple[bool, str]]) -> None:
        if self.focus_index == 0:
            self.cycle_focus()
            return
        trimmed = self.name.strip()
        if not trimmed:
            self.message = "\x1b[91mPlease enter a name before submitting.\x1b[0m"
            return
        success, message = submit_callback(trimmed)
        color = "\x1b[92m" if success else "\x1b[91m"
        self.message = f"{color}{message}\x1b[0m"
        if success:
            self.name = ""
            self.focus_index = 0

    def render_lines(self) -> List[str]:
        highlight = self.focus_index == 0
        name_label = ("> " if highlight else "  ") + "Name"
        lines = ["\x1b[1mCreate Account\x1b[0m", "", name_label]
        cursor_suffix = "_" if self.focus_index == 0 else ""
        lines.append(f"  {self.name}{cursor_suffix}")
        lines.append("")
        submit_prefix = "> " if self.focus_index == 1 else "  "
        submit_text = "\x1b[97mSubmit\x1b[0m" if self.focus_index == 1 else "\x1b[90mSubmit\x1b[0m"
        lines.append(f"{submit_prefix}{submit_text}")
        if self.message:
            lines.append("")
            lines.append(self.message)
        return lines
