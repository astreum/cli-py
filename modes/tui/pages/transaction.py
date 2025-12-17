from .base import BasePage


class TransactionPage(BasePage):
    def __init__(self) -> None:
        super().__init__(title="Create a Transaction")

    def load_elements(self, *args, **kwargs):
        if self.elements == []:
            self.elements = []
