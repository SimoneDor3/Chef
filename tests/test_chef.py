"""Tests for scripts/chef.py. Run: python -m unittest discover -s tests"""
import contextlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import chef  # noqa: E402


def run(*argv):
    out = io.StringIO()
    code = 0
    with contextlib.redirect_stdout(out):
        try:
            chef.main(list(argv))
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else 1
    return code, out.getvalue().strip()


class ChefTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.dir = str(self.tmp / "product")
        self.assertEqual(run("--dir", self.dir, "init", "--name", "Sample App")[0], 0)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def q(self, *extra):
        return run("--dir", self.dir, "add-question", "--topic", "data", "--title", "Where does data come from?", *extra)[1]

    def test_init_creates_skeleton(self):
        meta = json.loads((self.tmp / "product" / "product.json").read_text())
        self.assertEqual(meta["phase"], "frame")
        self.assertIn("Sample App", (self.tmp / "product" / "README.md").read_text())
        self.assertEqual(run("--dir", self.dir, "check")[0], 0)

    def test_ids_increase(self):
        self.assertEqual(self.q(), "Q-001")
        self.assertEqual(self.q(), "Q-002")

    def test_unknown_topic_refused(self):
        code, _ = run("--dir", self.dir, "add-question", "--topic", "nope", "--title", "x")
        self.assertNotEqual(code, 0)

    def test_proposed_then_accepted(self):
        qid = self.q("--blocking")
        did = run("--dir", self.dir, "add-decision", "--title", "Use the API", "--decision", "Read from the API.",
                  "--answers", qid)[1]
        p = chef.Product(self.dir)
        self.assertEqual(p.items("Q")[0]["Status"], "discussing")
        self.assertEqual(p.items("D")[0]["Status"], "proposed")
        run("--dir", self.dir, "accept", did)
        p = chef.Product(self.dir)
        self.assertEqual(p.items("Q")[0]["Status"], "decided")
        self.assertEqual(p.items("Q")[0]["Answered by"], did)
        self.assertEqual(run("--dir", self.dir, "check")[0], 0)

    def test_check_catches_decided_without_decision(self):
        self.q()
        path = next((self.tmp / "product" / "questions").glob("Q-001*.md"))
        path.write_text(chef.set_field(path.read_text(), "Status", "decided"))
        code, out = run("--dir", self.dir, "check")
        self.assertNotEqual(code, 0)
        self.assertIn("no accepted decision", out)

    def test_check_catches_unknown_reference(self):
        self.q("--context", "Depends on Q-099.")
        code, out = run("--dir", self.dir, "check")
        self.assertNotEqual(code, 0)
        self.assertIn("Q-099", out)

    def test_discover_gate_blocks_on_open_blocking_question(self):
        self.q("--blocking")
        code, out = run("--dir", self.dir, "gate", "discover")
        self.assertNotEqual(code, 0)
        self.assertIn("OPEN   no blocking question open (1 open)", out)

    def test_frame_gate_needs_filled_vision(self):
        self.assertNotEqual(run("--dir", self.dir, "gate", "frame")[0], 0)

    def test_dashboard_escapes_and_writes(self):
        run("--dir", self.dir, "add-question", "--topic", "data", "--title", "<script>alert(1)</script>")
        code, _ = run("--dir", self.dir, "dashboard")
        self.assertEqual(code, 0)
        page = (self.tmp / "product" / "dashboard.html").read_text()
        self.assertNotIn("<script>alert", page)
        self.assertIn("&lt;script&gt;", page)

    def test_separation_flags_product_name_in_kit(self):
        p = chef.Product(self.dir)
        p.meta["name"] = "Zebrafinch"
        probe = chef.KIT / "_probe_zebrafinch.md"
        probe.write_text("mentions zebrafinch")
        try:
            self.assertTrue(any("zebrafinch" in e for e in chef.separation_problems(p)))
        finally:
            probe.unlink()


if __name__ == "__main__":
    unittest.main()
