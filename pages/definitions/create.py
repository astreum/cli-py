from pathlib import Path
import re
from pages.base import BasePage
from astreum._node import Expr, ParseError, parse, tokenize, Atom

from pages.element import PageElement



class DefinitionCreatePage(BasePage):
    def __init__(self) -> None:
        super().__init__(title="Definitions List")

    def load_elements(self, *args, **kwargs):
        if self.elements == []:
            self.elements = [
                PageElement(label="Name", input=[""]),
                PageElement(label="Expression", input=["","",""]),
                PageElement(label="Submit", action=self.handle_submit),
                PageElement(label="Terminal", next="terminal")
                
            ]

    def handle_submit(self, app: "App"):
        name = self.elements[0].input[0]

        def slugify(name:str):
            cleaned = re.sub(r"\s+", "_", name.strip())
            slug = re.sub(r"[^0-9a-zA-Z_-]+", "_", cleaned)
            slug = slug.strip("_")
            if not slug:
                pass
        

        expr_str = "".join(self.elements[1].input[0])
        try:
            tokens = tokenize(source=expr_str)
        except ParseError as exc:
            return False, f"Failed to tokenize expression: {exc}"
        except Exception as exc:
            return False, f"Unexpected tokenization error: {exc}"

        try:
            expr, _ = parse(tokens=tokens)
        except ParseError as exc:
            return False, f"Failed to parse expression: {exc}"
        except Exception as exc:
            return False, f"Failed to parse expression: {exc}"

        if expr is None:
            return False, "Parser did not return a valid expression."

        try:
            root_hash, atoms = expr.to_atoms()
        except Exception as exc:
            return False, f"Failed to convert expression: {exc}"

        atoms_dir = app.data_dir / "atoms"
        definitions_dir = app.data_dir / "definitions"


        saved_atoms = 0
        for atom in atoms:
            try:
                atom_bytes = atom.to_bytes()
            except Exception as exc:
                return False, f"Failed to serialise atom: {exc}"
            
            object_id = atom.object_id()
            object_hex = (
                object_id.hex()
                if isinstance(object_id, (bytes, bytearray))
                else str(object_id)
            )
            atom_path = atoms_dir / f"0x{object_hex}.bin"
            try:
                atom_path.write_bytes(atom_bytes)
            except OSError as exc:
                return False, f"Failed to write atom {object_hex}: {exc}"
            saved_atoms += 1

        slug = slugify(name)
        definition_path = definitions_dir / f"{slug}.bin"

        try:
            definition_path.write_bytes(root_hash)
        except OSError as exc:
            return False, f"Failed to save definition '{slug}': {exc}"

        return True, f"Saved definition '{definition_path.stem}'. Wrote {saved_atoms} atoms."

