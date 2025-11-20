from pages.base import BasePage


class DefinitionCreatePage(BasePage):
    def __init__(self) -> None:
        super().__init__(title="Add a Definition")

    def load_elements(self, *args, **kwargs):
        if self.elements == []:
            self.elements = []