from __future__ import annotations

from ..base import BasePage
from ..element import PageElement


class SearchPage(BasePage):
    def __init__(self) -> None:
        super().__init__(title="Search")

    def load_elements(self, *args, **kwargs):
        if self.elements == []:
            self.elements = [
                PageElement(label="Block", next="block_search"),
                PageElement(label="Accounts", next="account_search"),
                PageElement(label="Transactions", next="transaction_search"),
            ]
