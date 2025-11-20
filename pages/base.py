
from typing import List

from pages.element import PageElement



class BasePage:
    def __init__(self, title: str, elements: List[PageElement] = []) -> None:
        self.title = title
        self.elements = elements
        self.index = 0

    def load_elements(self, *args, **kwargs):
        pass

    def render(self, cursor_effect: bool = False) -> List[str]:
        lines: List[str] = [f"\x1b[1m{self.title}\x1b[0m", ""]
        for idx, element in enumerate(self.elements):
            lines.extend(element.render(focus=(idx == self.index), cursor_effect=cursor_effect))
            if idx < len(self.elements) - 1:
                lines.append("")
        return lines

    def navigate(self, forward: bool = True) -> List[str]:
        if not self.elements:
            return self.render()
        delta = 1 if forward else -1
        self.index = (self.index + delta) % len(self.elements)
        return self.render()
