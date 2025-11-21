import re
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from pages.base import BasePage, PageElement

class AccountCreatePage(BasePage):
    def __init__(self) -> None:
        
        super().__init__(title="Create an Account")

    def load_elements(self, *args, **kwargs):
        if self.elements == []:
            self.elements = [
                PageElement(label="Name", input=[""]),
                PageElement(label="Submit", action=self.handle_submit)
            ]

    def handle_submit(self, app: "App"):
        accounts_dir = app.data_dir / "accounts"
        name = self.elements[0].input[0]

        def slugify(name: str) -> str:
            cleaned = re.sub(r"\s+", "_", name.strip())
            slug = re.sub(r"[^0-9a-zA-Z_-]+", "_", cleaned)
            slug = slug.strip("_")
            if not slug:
                slug = "account"
            return slug
        
        slug = slugify(name)

        candidate_path = accounts_dir / f"{slug}.bin"

        if candidate_path.exists():
            app.flash_message = f"Account name `{input[0]}` already in use!"

        private_key = ed25519.Ed25519PrivateKey.generate()
        private_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )
        try:
            candidate_path.write_bytes(private_bytes)
        except OSError as exc:
            app.flash_message = f"Failed to save account: {exc}"
        
        app.previous_view = "account_create"
        app.active_view = "account_list"