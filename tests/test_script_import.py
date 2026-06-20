import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from astreum import Expr, compile, parse, tokenize
from astreum.machine.main import Machine
from astreum.machine.models.environment import Env


TEST_SCRIPTS = ROOT / "tests" / "test_scripts"


class TestScriptCompile(unittest.TestCase):
    def test_imported_target(self):
        env = compile(
            node=None,
            script=str(TEST_SCRIPTS / "main.aex"),
            target="math.calc_sum",
        )
        self.assertIsNotNone(
            env.get("math.calc_sum"),
            "math.calc_sum should be available via import prefix",
        )

    def test_plain_target(self):
        env = compile(
            node=None,
            script=str(TEST_SCRIPTS / "math" / "sum.aex"),
            target="calc_sum",
        )
        self.assertIsNotNone(
            env.get("calc_sum"),
            "calc_sum should be defined in sum.aex",
        )

    def test_shared_module_dedup(self):
        env = compile(
            node=None,
            script=str(TEST_SCRIPTS / "multi_import.aex"),
            target="a.add_one",
        )
        self.assertIsNotNone(env.get("a.add_one"))
        self.assertIsNotNone(env.get("a.s.foo"))
        self.assertIsNone(env.get("b.sub_one"))


if __name__ == "__main__":
    unittest.main()
