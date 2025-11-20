from __future__ import annotations

from pages.base import BasePage, PageElement


class MenuPage(BasePage):
    def __init__(self) -> None:
        super().__init__(title="Menu")

    def load_elements(self, *args, **kwargs):
        if self.elements == []:
            self.elements = [
                PageElement(label="Search", next="search"),
                PageElement(label="List Accounts", next="account_list"),
                PageElement(label="Create Account", next="account_create"),
                PageElement(label="Create Transaction", next="transaction_create"),
                PageElement(label="List Definitions", next="definition_list"),
                PageElement(label="Add Definition", next="definition_create"),
                PageElement(label="Terminal", next="terminal"),
                PageElement(label="Settings", next="settings"),
                PageElement(label="Quit", action=self._exit_app),
            ]

    def _exit_app(self, app: "App") -> None:
        app.should_exit = True
