from pages.base import BasePage
from pages.element import PageElement


def load_definitions(app: "App") -> list[tuple[str, str]]:
    definitions_dir = app.data_dir / "definitions"
    if not definitions_dir.exists():
        return []
    
    definitions: list[tuple[str, "Expr"]] = []
    for definition_file in sorted(definitions_dir.glob("*.bin")):
        try:
            root_hash = definition_file.read_bytes()
        except OSError:
            continue

        expr = app.node.get_expr_list_from_storage(key=root_hash)
        if expr is None:
            continue

        definition_name = definition_file.stem
        definitions.append((definition_name, expr))

    return definitions

class DefinitionCreatePage(BasePage):
    def __init__(self) -> None:
        super().__init__(title="Add a Definition")

    def load_elements(self, app: "App"):
        if self.elements == []:
            definitions = load_definitions(app)
            self.elements = [
                PageElement(label=name, body=f"{expr}")
                    for name, expr in definitions
                ]