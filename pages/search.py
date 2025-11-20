from pages.base import BasePage


class SearchPage(BasePage):
    def __init__(self) -> None:
        super().__init__(title="Search")

    def load_elements(self, *args, **kwargs):
        if self.elements == []:
            self.elements = []