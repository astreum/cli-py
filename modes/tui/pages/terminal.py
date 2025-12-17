from .base import BasePage


class TerminalPage(BasePage):
    def __init__(self) -> None:
        super().__init__(title="Terminal")

    def load_elements(self, *args, **kwargs):
        if self.elements == []:
            self.elements = []
