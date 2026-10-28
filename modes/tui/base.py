
from typing import List, Optional, Tuple

from .element import PageElement



class BasePage:
    def __init__(self, title: str, elements: List[PageElement] = []) -> None:
        self.title = title
        self.elements = elements
        self.index = 0
        self.element_spans: List[Tuple[int, int]] = []

    def load_elements(self, *args, **kwargs):
        pass

    def has_selectable(self) -> bool:
        return any(element.selectable for element in self.elements)

    def ensure_focus(self) -> None:
        if not self.elements:
            return
        self.index = max(0, min(self.index, len(self.elements) - 1))
        if self.elements[self.index].selectable or not self.has_selectable():
            return
        self._step(1)

    def _step(self, delta: int) -> None:
        count = len(self.elements)
        for _ in range(count):
            self.index = (self.index + delta) % count
            if self.elements[self.index].selectable:
                return

    def render_with_cursor(
        self,
        cursor_active: bool = False,
    ) -> Tuple[List[str], Optional[Tuple[int, int]]]:
        self.ensure_focus()
        lines: List[str] = [f"\x1b[1m{self.title}\x1b[0m", ""]
        cursor_pos: Optional[Tuple[int, int]] = None
        self.element_spans = []

        for idx, element in enumerate(self.elements):
            focus = idx == self.index
            element_lines = element.render(focus=focus)

            if cursor_active and focus:
                element_cursor = element.cursor_offset()
                if element_cursor is not None:
                    cursor_pos = (len(lines) + element_cursor[0], element_cursor[1])

            self.element_spans.append((len(lines), len(lines) + len(element_lines) - 1))
            lines.extend(element_lines)
            if idx < len(self.elements) - 1:
                lines.append("")

        return lines, cursor_pos

    def render(self) -> List[str]:
        lines, _ = self.render_with_cursor()
        return lines

    def navigate(self, forward: bool = True) -> List[str]:
        if not self.elements:
            return self.render()
        if self.has_selectable():
            self._step(1 if forward else -1)
        return self.render()

