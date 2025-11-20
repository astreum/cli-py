from pages.base import BasePage


class SettingsPage(BasePage):
    def __init__(self) -> None:
        elements = [
        ]
        super().__init__(title="Settings", elements=elements)

    def load_elements(self, *args, **kwargs):
        if self.elements == []:
            self.elements = []