from typing import Callable, List


class AddDefinitionPage:
    """Simple add-definition form with two inputs and a submit button."""

    def __init__(self) -> None:
        self.name: str = ""
        self.expression: str = ""
        self.focus_index: int = 0  # 0=name, 1=expression, 2=submit
        self.message: str = ""

    def prepare_for_entry(self) -> None:
        self.name = ""
        self.expression = ""
        self.message = ""
        self.focus_index = 0

    def cycle_focus(self) -> None:
        self.focus_index = (self.focus_index + 1) % 3

    def handle_char(self, key: str) -> bool:
        if self.focus_index not in (0, 1):
            return False
        target = "name" if self.focus_index == 0 else "expression"
        if key in {"\x08", "\x7f"}:
            current = getattr(self, target)
            if not current:
                return False
            setattr(self, target, current[:-1])
            return True
        if len(key) == 1 and key.isprintable():
            current = getattr(self, target)
            setattr(self, target, current + key)
            return True
        return False

    def handle_enter(self, submit_callback: Callable[[str, str], tuple[bool, str]]) -> None:
        if self.focus_index in (0, 1):
            self.cycle_focus()
            return
        name = self.name.strip()
        expression = self.expression.strip()
        if not name:
            self.message = "\x1b[91mName is required before saving.\x1b[0m"
            self.focus_index = 0
            return
        if not expression:
            self.message = "\x1b[91mExpression is required before saving.\x1b[0m"
            self.focus_index = 1
            return
        success, feedback = submit_callback(name, expression)
        color = "\x1b[92m" if success else "\x1b[91m"
        self.message = f"{color}{feedback}\x1b[0m"
        if success:
            self.name = ""
            self.expression = ""
            self.focus_index = 0

    def render_lines(self) -> List[str]:
        lines = ["\x1b[1mAdd Definition\x1b[0m", ""]

        name_active = self.focus_index == 0
        lines.append(("> " if name_active else "  ") + "Name")
        lines.append(f"  {self.name}{'_' if name_active else ''}")
        lines.append("")

        expr_active = self.focus_index == 1
        lines.append(("> " if expr_active else "  ") + "Expression")
        lines.append(f"  {self.expression}{'_' if expr_active else ''}")
        lines.append("")

        submit_active = self.focus_index == 2
        submit_prefix = "> " if submit_active else "  "
        submit_text = "\x1b[97mSubmit\x1b[0m" if submit_active else "\x1b[90mSubmit\x1b[0m"
        lines.append(f"{submit_prefix}{submit_text}")

        if self.message:
            lines.append("")
            lines.append(self.message)

        return lines
