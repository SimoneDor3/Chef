"""Tests for scripts/chef.py. Run: python -m unittest discover -s tests"""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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
            if isinstance(exc.code, str):
                out.write(exc.code)
    return code, out.getvalue().strip()


def fill_sections(path):
    """Replace every TODO line of a template file with real text."""
    path.write_text("\n".join("Filled." if line.startswith("TODO") else line
                              for line in path.read_text().splitlines()) + "\n")


class ChefTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.root = self.tmp / "product"
        self.dir = str(self.root)
        self.assertEqual(run("--dir", self.dir, "init", "--name", "Sample App")[0], 0)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def cmd(self, *argv):
        return run("--dir", self.dir, *argv)

    def q(self, *extra):
        return self.cmd("add-question", "--topic", "stack", "--title", "Which language?", *extra)[1]

    def stage(self, item="mvp"):
        return chef.Product(self.dir).stage(item)

    def set_stage(self, item, stage):
        meta = json.loads((self.root / "product.json").read_text())
        meta["stages"][item] = stage
        (self.root / "product.json").write_text(json.dumps(meta))

    def feature_with_criteria(self, label):
        fid = self.cmd("add-feature", "--title", "Sign in", "--label", label, "--goal", "People get in.")[1]
        path = next((self.root / "features").glob(f"{fid}*.md"))
        path.write_text(path.read_text().replace("Given ..., when ..., then ....",
                                                 "Given a user, when they sign in, then they see home."))
        return fid

    def make_scope_ready(self):
        """Everything /chef:approve mvp needs, once the MVP is discovering."""
        fill_sections(self.root / "mvp.md")
        self.feature_with_criteria("MVP")
        topics = self.root / "topics.md"
        topics.write_text(topics.read_text().replace("| MVP | open |", "| MVP | covered |"))
        (self.root / "toolset.json").write_text('{"stack": ["python"]}')

    def start_discovery(self):
        fill_sections(self.root / "vision.md")
        self.assertEqual(self.cmd("stage", "mvp", "discovering")[0], 0)

    # -------------------------------------------------------------- records
    def test_init_creates_skeleton(self):
        meta = json.loads((self.root / "product.json").read_text())
        self.assertEqual(meta["stages"], {"mvp": "idea"})
        self.assertIn("Sample App", (self.root / "mvp.md").read_text())
        self.assertFalse((self.root / "gates.md").exists())
        self.assertEqual([t["id"] for t in chef.Product(self.dir).topics()], ["stack"])
        self.assertEqual(self.cmd("check")[0], 0)

    def test_ids_increase(self):
        self.assertEqual(self.q(), "Q-001")
        self.assertEqual(self.q(), "Q-002")

    def test_unknown_topic_refused(self):
        self.assertNotEqual(self.cmd("add-question", "--topic", "nope", "--title", "x")[0], 0)

    def test_add_topic_with_label(self):
        self.assertEqual(self.cmd("add-topic", "--id", "sync", "--name", "Sync", "--label", "later")[0], 0)
        self.assertEqual([t["label"] for t in chef.Product(self.dir).topics()], ["MVP", "later"])
        self.assertNotEqual(self.cmd("add-topic", "--id", "sync", "--name", "Again", "--label", "MVP")[0], 0)
        self.assertEqual(self.cmd("check")[0], 0)

    def test_proposed_then_accepted(self):
        qid = self.q("--blocking")
        did = self.cmd("add-decision", "--title", "Use Python", "--decision", "Python.", "--answers", qid)[1]
        p = chef.Product(self.dir)
        self.assertEqual(p.items("Q")[0]["Status"], "discussing")
        self.assertEqual(p.items("D")[0]["Status"], "proposed")
        self.cmd("accept", did)
        p = chef.Product(self.dir)
        self.assertEqual(p.items("Q")[0]["Status"], "decided")
        self.assertEqual(p.items("Q")[0]["Answered by"], did)
        self.assertEqual(self.cmd("check")[0], 0)

    def test_later_feature_gets_a_stage_mvp_feature_does_not(self):
        later = self.cmd("add-feature", "--title", "Export", "--label", "later")[1]
        mvp = self.cmd("add-feature", "--title", "Home", "--label", "MVP")[1]
        self.assertEqual(self.stage(later), "idea")
        self.assertIsNone(self.stage(mvp))
        self.assertNotEqual(self.cmd("stage", mvp)[0], 0)
        self.assertEqual(self.cmd("check")[0], 0)

    def test_topic_status(self):
        self.assertEqual(self.cmd("topic", "stack", "in progress")[0], 0)
        self.assertEqual(chef.Product(self.dir).topics()[0]["status"], "in progress")
        self.assertNotEqual(self.cmd("topic", "nope", "covered")[0], 0)
        self.assertNotEqual(self.cmd("topic", "stack", "done")[0], 0)
        self.assertEqual(self.cmd("check")[0], 0)

    def test_drop_keeps_the_file_and_the_id(self):
        fid = self.cmd("add-feature", "--title", "Export", "--label", "later")[1]
        self.assertEqual(self.cmd("drop", fid, "--reason", "not worth it")[0], 0)
        p = chef.Product(self.dir)
        self.assertIsNone(p.stage(fid))
        self.assertEqual(p.state(fid), "dropped")
        self.assertIn("not worth it", p.meta["dropped"][fid])
        self.assertEqual(self.cmd("add-feature", "--title", "Import", "--label", "later")[1], "F-002")
        self.assertEqual(self.cmd("check")[0], 0)
        self.assertIn("dropped", self.cmd("status")[1])

    def test_drop_refused_once_scoped(self):
        fid = self.cmd("add-feature", "--title", "Export", "--label", "later")[1]
        self.set_stage(fid, "scoped")
        self.assertNotEqual(self.cmd("drop", fid, "--reason", "x")[0], 0)

    def test_missing_vision_or_mvp_never_passes(self):
        (self.root / "vision.md").unlink()
        code, out = self.cmd("stage", "mvp", "discovering")
        self.assertEqual(code, 1)
        self.assertIn("file missing", out)
        self.assertEqual(self.next()[0], "/chef:vision")
        self.assertIn("vision.md is missing", self.cmd("check")[1])

    def test_bad_product_json_gives_a_clear_message(self):
        meta = self.root / "product.json"
        meta.write_text("{bad")
        code, out = self.cmd("status")
        self.assertEqual(code, 1)
        self.assertIn("not valid JSON", out)
        meta.write_text('\ufeff{"name": "Sample App", "stages": {"mvp": "cooking"}}', encoding="utf-8")
        for argv in (("status",), ("next",), ("dashboard",), ("stage", "mvp")):
            code, out = self.cmd(*argv)
            self.assertEqual(code, 1, argv)
            self.assertIn("unknown stages", out, argv)
        self.assertIn("cooking", self.cmd("check")[1])

    def test_accept_writes_nothing_if_a_question_is_broken(self):
        qid = self.q()
        path = next((self.root / "questions").glob("Q-001*.md"))
        path.write_text(path.read_text().replace("| Answered by | - |\n", ""))
        did = self.cmd("add-decision", "--title", "Use Python", "--decision", "Python.", "--answers", qid)[1]
        self.assertNotEqual(self.cmd("accept", did)[0], 0)
        self.assertEqual(chef.Product(self.dir).items("D")[0]["Status"], "proposed")

    def test_add_topic_refuses_table_breaking_text(self):
        self.assertNotEqual(self.cmd("add-topic", "--id", "t2", "--name", "a|b", "--label", "MVP")[0], 0)

    def test_topic_status_only_changes_its_own_row(self):
        self.cmd("add-topic", "--id", "stack-x", "--name", "More stack", "--label", "later")
        self.cmd("topic", "stack-x", "covered")
        self.assertEqual([t["status"] for t in chef.Product(self.dir).topics()], ["open", "covered"])

    def test_init_refuses_a_folder_with_files(self):
        other = self.tmp / "notes"
        other.mkdir()
        (other / "README.md").write_text("mine")
        self.assertNotEqual(run("--dir", str(other), "init", "--name", "X")[0], 0)
        self.assertEqual((other / "README.md").read_text(), "mine")

    def test_product_folder_ignores_dashboard(self):
        self.assertEqual((self.root / ".gitignore").read_text().strip(), "dashboard.html")

    def test_check_catches_decided_without_decision(self):
        self.q()
        path = next((self.root / "questions").glob("Q-001*.md"))
        path.write_text(chef.set_field(path.read_text(), "Status", "decided"))
        code, out = self.cmd("check")
        self.assertNotEqual(code, 0)
        self.assertIn("no accepted decision", out)

    def test_check_catches_unknown_reference(self):
        self.q("--context", "Depends on Q-099.")
        code, out = self.cmd("check")
        self.assertNotEqual(code, 0)
        self.assertIn("Q-099", out)

    def test_check_catches_bad_stage_and_label(self):
        self.set_stage("mvp", "cooking")
        topics = self.root / "topics.md"
        topics.write_text(topics.read_text().replace("| MVP |", "| soon |"))
        code, out = self.cmd("check")
        self.assertNotEqual(code, 0)
        self.assertIn("cooking", out)
        self.assertIn("soon", out)

    # -------------------------------------------------------------- stages
    def test_moves_one_stage_at_a_time(self):
        fill_sections(self.root / "vision.md")
        code, out = self.cmd("stage", "mvp", "scoped")
        self.assertNotEqual(code, 0)
        self.assertIn("one stage at a time", out)
        self.assertEqual(self.stage(), "idea")

    def test_discovery_needs_a_vision(self):
        code, out = self.cmd("stage", "mvp", "discovering")
        self.assertEqual(code, 1)
        self.assertIn("MISSING vision filled in", out)
        self.start_discovery()
        self.assertEqual(self.stage(), "discovering")

    def test_scope_refused_says_what_is_missing(self):
        self.start_discovery()
        self.q("--blocking")
        code, out = self.cmd("stage", "mvp", "scoped")
        self.assertEqual(code, 1)
        for missing in ("mvp.md filled in", "not yet: stack", "no MVP feature yet", "toolset.json", "Q-001"):
            self.assertIn(missing, out)
        self.assertEqual(self.stage(), "discovering")

    def test_scope_passes_when_ready(self):
        self.start_discovery()
        self.make_scope_ready()
        self.assertEqual(self.cmd("stage", "mvp", "scoped")[0], 0)
        self.assertEqual(self.stage(), "scoped")

    def test_design_needs_approved_system_and_screens(self):
        self.set_stage("mvp", "designing")
        code, out = self.cmd("stage", "mvp", "designed")
        self.assertEqual(code, 1)
        self.assertIn("design system approved", out)
        design = self.root / "design"
        (design / "system.md").write_text((chef.KIT / "templates" / "design-system.md").read_text().replace("draft", "approved"))
        (design / "home.md").write_text((chef.KIT / "templates" / "screen.md").read_text())
        self.assertIn("pending: home", self.cmd("stage", "mvp", "designed")[1])
        (design / "home.md").write_text((design / "home.md").read_text().replace("draft", "approved"))
        self.assertEqual(self.cmd("stage", "mvp", "designed")[0], 0)

    def test_feature_build_waits_for_mvp(self):
        fid = self.cmd("add-feature", "--title", "Export", "--label", "later")[1]
        self.set_stage(fid, "designed")
        code, out = self.cmd("stage", fid, "building")
        self.assertEqual(code, 1)
        self.assertIn("the MVP is shipped", out)
        self.set_stage("mvp", "shipped")
        self.assertEqual(self.cmd("stage", fid, "building")[0], 0)

    def test_ship_needs_summary(self):
        self.set_stage("mvp", "building")
        self.assertEqual(self.cmd("stage", "mvp", "shipped")[0], 1)
        (self.root / "build" / "mvp").mkdir(parents=True)
        (self.root / "build" / "mvp" / "summary.md").write_text("# Build summary: mvp\n")
        self.assertEqual(self.cmd("stage", "mvp", "shipped")[0], 0)

    # -------------------------------------------------------------- next move
    def next(self):
        return chef.next_move(chef.Product(self.dir))

    def test_next_move_follows_the_flow(self):
        self.assertEqual(self.next()[0], "/chef:vision")
        fill_sections(self.root / "vision.md")
        self.assertEqual(self.next()[0], "/chef:discover mvp")
        self.cmd("stage", "mvp", "discovering")
        self.assertEqual(self.next()[0], "/chef:discover stack")
        self.make_scope_ready()
        self.assertEqual(self.next()[0], "/chef:approve mvp")
        self.assertIn("mvp: ready to be scoped (/chef:approve mvp)", chef.waiting_on_owner(chef.Product(self.dir)))
        self.cmd("stage", "mvp", "scoped")
        self.assertEqual(self.next()[0], "/chef:design system")

    def test_next_move_after_mvp_ships(self):
        fill_sections(self.root / "vision.md")
        self.set_stage("mvp", "shipped")
        self.assertEqual(self.next()[0], "/chef:idea")
        fid = self.cmd("add-feature", "--title", "Export", "--label", "later")[1]
        self.assertEqual(self.next()[0], f"/chef:discover {fid}")

    def test_next_move_puts_waiting_decision_first(self):
        fill_sections(self.root / "vision.md")
        self.cmd("add-decision", "--title", "Use Python", "--decision", "Python.", "--answers", self.q())
        self.assertEqual(self.next(), ("/chef:discover stack", "D-001 (Use Python) waits for your yes or no"))

    # -------------------------------------------------------------- dashboard
    def test_dashboard_escapes_and_shows_next_move(self):
        self.cmd("add-question", "--topic", "stack", "--title", "<script>alert(1)</script>")
        self.assertEqual(self.cmd("dashboard")[0], 0)
        page = (self.root / "dashboard.html").read_text()
        self.assertNotIn("<script>alert", page)
        self.assertIn("&lt;script&gt;", page)
        self.assertIn("Next move", page)
        self.assertIn("/chef:vision", page)
        self.assertNotIn("http", page)                      # offline: nothing loaded from anywhere
        self.assertNotIn(">---<", page)                     # table separators are not topics

    def test_dashboard_has_a_theme_switch(self):
        self.cmd("dashboard")
        page = (self.root / "dashboard.html").read_text()
        self.assertIn('id="theme"', page)
        self.assertIn('prefers-color-scheme: dark', page)
        self.assertIn(':root[data-theme="dark"]', page)
        self.assertIn("localStorage", page)

    # -------------------------------------------------------------- deps and settings
    def test_deps_reports_missing(self):
        home = self.tmp / "home"
        (home / ".claude").mkdir(parents=True)
        (home / ".claude" / "settings.json").write_text(json.dumps({"enabledPlugins": {"ecc@ecc": True}}))
        with mock.patch.dict(os.environ, {"HOME": str(home), "PATH": ""}):
            code, out = run("deps", "--project", str(self.tmp))
        self.assertEqual(code, 1)
        self.assertIn("OK      plugin ecc", out)
        self.assertIn("MISSING plugin ponytail", out)
        self.assertIn("MISSING uv", out)

    def test_settings_merge_keeps_owner_choices(self):
        (self.tmp / ".claude").mkdir()
        (self.tmp / ".claude" / "settings.json").write_text(json.dumps(
            {"env": {"PONYTAIL_DEFAULT_MODE": "lite", "GATEGUARD_EXEMPT_GLOBS": "docs/**"}, "model": "x"}))
        self.assertEqual(self.cmd("settings", "--project", str(self.tmp))[0], 0)
        data = json.loads((self.tmp / ".claude" / "settings.json").read_text())
        self.assertEqual(data["env"]["PONYTAIL_DEFAULT_MODE"], "lite")
        self.assertEqual(data["env"]["GATEGUARD_EXEMPT_GLOBS"], "docs/**,product/**")
        self.assertEqual(data["model"], "x")
        self.assertTrue(data["enabledPlugins"]["ponytail@ponytail"])
        self.assertIn("already in place", self.cmd("settings", "--project", str(self.tmp))[1])

    def test_settings_refuses_bad_json_and_whole_repo_exemption(self):
        (self.tmp / ".claude").mkdir()
        (self.tmp / ".claude" / "settings.json").write_text("{ // comment")
        code, out = self.cmd("settings", "--project", str(self.tmp))
        self.assertEqual(code, 1)
        self.assertIn("not valid JSON", out)
        (self.tmp / ".claude" / "settings.json").write_text("{}")
        code, out = run("--dir", str(self.tmp), "settings", "--project", str(self.tmp))
        self.assertEqual(code, 1)
        self.assertEqual(json.loads((self.tmp / ".claude" / "settings.json").read_text()), {})

    def test_settings_pins_ponytail_and_keeps_an_owner_pin(self):
        settings = self.tmp / ".claude" / "settings.json"

        def ponytail():
            return json.loads(settings.read_text())["extraKnownMarketplaces"]["ponytail"]

        def with_entry(entry):
            data = json.loads(settings.read_text())
            data["extraKnownMarketplaces"]["ponytail"] = entry
            settings.write_text(json.dumps(data))
            return self.cmd("settings", "--project", str(self.tmp))[1]

        self.assertIn("declared", self.cmd("settings", "--project", str(self.tmp))[1])
        self.assertEqual(ponytail(), {"source": chef.PONYTAIL_SOURCE})
        self.assertRegex(chef.PONYTAIL_SOURCE["ref"], r"^[0-9a-f]{40}$")
        # an earlier unpinned Chef entry is pinned, and its other keys stay
        out = with_entry({"source": {"source": "github", "repo": "DietrichGebert/ponytail"}, "autoUpdate": False})
        self.assertIn("pinned", out)
        self.assertEqual(ponytail(), {"source": chef.PONYTAIL_SOURCE, "autoUpdate": False})
        # an owner's own pin, another source type, or an odd shape is left alone
        for entry in ({"source": {"source": "github", "repo": "DietrichGebert/ponytail", "ref": "v9"}},
                      {"source": {"source": "git", "repo": "DietrichGebert/ponytail"}},
                      {"source": "./local"}, "odd"):
            with_entry(entry)
            self.assertEqual(ponytail(), entry)

    def test_settings_refuses_a_comma_in_the_product_path(self):
        odd = self.tmp / "a,b"
        self.assertEqual(run("--dir", str(odd), "init", "--name", "Odd")[0], 0)
        code, out = run("--dir", str(odd), "settings", "--project", str(self.tmp))
        self.assertEqual(code, 1)
        self.assertIn("comma", out)
        self.assertFalse((self.tmp / ".claude" / "settings.json").exists())

    def test_repo_settings_pin_the_same_release(self):
        repo = json.loads((chef.KIT / ".claude" / "settings.json").read_text())
        self.assertEqual(repo["extraKnownMarketplaces"]["ponytail"]["source"], chef.PONYTAIL_SOURCE)

    def test_settings_on_a_new_project(self):
        self.cmd("settings", "--project", str(self.tmp))
        data = json.loads((self.tmp / ".claude" / "settings.json").read_text())
        self.assertEqual(data["env"]["PONYTAIL_DEFAULT_MODE"], "off")
        self.assertEqual(data["env"]["GATEGUARD_EXEMPT_GLOBS"], "product/**")

    # -------------------------------------------------------------- separation
    def test_separation_flags_product_name_in_kit(self):
        p = chef.Product(self.dir)
        p.meta["name"] = "Zebrafinch"
        probe = chef.KIT / "_probe_zebrafinch.md"
        probe.write_text("mentions zebrafinch")
        try:
            self.assertTrue(any("zebrafinch" in e for e in chef.separation_problems(p)))
        finally:
            probe.unlink()


class SkillsTest(unittest.TestCase):
    def test_eight_commands_plus_the_shared_rules_skill(self):
        skills = sorted(d.name for d in (chef.KIT / "skills").iterdir() if (d / "SKILL.md").exists())
        self.assertEqual(skills, ["approve", "bug", "build", "chef", "design", "discover", "idea", "status", "vision"])
        for name in skills:
            head = (chef.KIT / "skills" / name / "SKILL.md").read_text().split("---")[1]
            self.assertIn(f"name: {name}\n", head)
            self.assertIn("description: ", head)


if __name__ == "__main__":
    unittest.main()
