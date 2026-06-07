import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from astreum import Expr, parse, tokenize
from astreum.machine.main import Machine
from astreum.machine.models.environment import Env
from modes.evaluation.script import load_script_to_environment


TEST_SCRIPTS = ROOT / "tests" / "test_scripts"


class TestScriptImport(unittest.TestCase):
    def test_import_calc_sum(self):
        """Load main.aex which imports math/sum.aex and verify defs."""
        env = load_script_to_environment(
            node=None, script=str(TEST_SCRIPTS / "main.aex")
        )

        self.assertIsNotNone(
            env.get("math.calc_sum"),
            "math.calc_sum should be available via import prefix",
        )

    def test_calc_sum_definition(self):
        """Load math/sum.aex directly and verify calc_sum exists."""
        env = load_script_to_environment(
            node=None, script=str(TEST_SCRIPTS / "math" / "sum.aex")
        )

        self.assertIsNotNone(
            env.get("calc_sum"),
            "calc_sum should be defined in sum.aex",
        )

    def test_factorial_direct(self):
        """Recursive factorial via direct fn call (no file loading)."""
        fact_body_src = (
            "((n 1 is_eq) (quote 1)"
            " (quote (((n 1 -) (quote (n)) fact fn) n *)) if)"
        )
        entry_src = f"(5 (quote (n)) (quote {fact_body_src}) fn)"

        tokens = tokenize(entry_src)
        expr, _ = parse(tokens)

        fact_body, _ = parse(tokenize(fact_body_src))
        env = Env()
        env.put("fact", fact_body)

        machine = Machine(node=None, meter_enabled=False)
        result = machine.run(expr=expr, env=env)

        self.assertIsInstance(result, Expr.Bytes)
        self.assertEqual(int.from_bytes(result.value, "little"), 120)
