#!/usr/bin/env python3
"""Chef: the tool behind a product folder, from first idea to a shipped product.

Usage: python chef.py [--dir PRODUCT_DIR] <command> [options]

Commands
  init --name NAME              create a product folder from Chef's templates
  add-topic ...                 add a topic to topics.md, labelled MVP or later
  add-question ...              record a new open question (prints its id)
  add-decision ...              record a decision, proposed unless --accepted (prints its id)
  accept D-001                  accept a decision; questions it answers become decided
  add-feature ...               write a feature file; a later feature starts at stage idea
  topic ID STATUS               set a topic to open, in progress or covered
  drop F-001 --reason ...       park a later idea for good (its file and id stay)
  stage ITEM [STAGE]            show an item's stage and checks, or move it one stage on
  next                          the suggested next move
  status                        one-screen summary: stages, waiting on the owner, next move
  check                         validate every file, every link, and the Chef/product separation
  dashboard [--out F] [--open]  write the offline HTML dashboard, and open it
  deps [--project DIR]          check the plugins and tools Chef needs
  settings [--project DIR]      merge Chef's settings into the project's .claude/settings.json

ITEM is `mvp` or a feature id (F-001). Standard library only, so it runs anywhere Python 3.9+
does. The product folder defaults to ./product; pass --dir to point elsewhere.
"""
import argparse
import datetime as dt
import html
import json
import os
import re
import shutil
import sys
import webbrowser
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
STAGES = ["idea", "discovering", "scoped", "designing", "designed", "building", "shipped"]
# moves that start work (made by discover/design/build); every other move needs /chef:approve
STARTED_BY = {"discovering": "/chef:discover", "designing": "/chef:design", "building": "/chef:build"}
LABELS = ["MVP", "later"]
Q_STATUSES = ["open", "discussing", "decided", "dropped"]
D_STATUSES = ["proposed", "accepted", "superseded", "rejected"]
TOPIC_STATUSES = ["open", "in progress", "covered"]
PLUGINS = {"ecc": "the ECC plugin", "ponytail": "the Ponytail plugin (/plugin marketplace add DietrichGebert/ponytail)"}


# ------------------------------------------------------------------ files and parsing
def today():
    return dt.date.today().isoformat()


def slug(text, limit=48):
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:limit].rstrip("-") or "item"


def fields(text):
    """The first markdown table of a file, read as {Field: Value}."""
    out, started = {}, False
    for line in text.splitlines():
        m = re.match(r"^\|\s*([^|]+?)\s*\|\s*([^|]*?)\s*\|\s*$", line)
        if m:
            started = True
            key = m.group(1)
            if key == "Field" or set(key) <= set("-: "):
                continue
            out[key] = m.group(2)
        elif started:
            break
    return out


def set_field(text, key, value):
    pattern = re.compile(r"^(\|\s*" + re.escape(key) + r"\s*\|\s*)([^|]*?)(\s*\|\s*)$", re.M)
    if not pattern.search(text):
        raise SystemExit(f"field {key!r} not found")
    return pattern.sub(lambda m: m.group(1) + value + m.group(3), text, count=1)


def section(text, name):
    m = re.search(r"^## " + re.escape(name) + r"\s*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    return m.group(1).strip() if m else ""


def title(text):
    m = re.search(r"^# [A-Z]-\d+: (.+)$", text, re.M) or re.search(r"^# (.+)$", text, re.M)
    return m.group(1).strip() if m else ""


def ids(value):
    return re.findall(r"\b[QDF]-\d{3}\b", value or "")


def unfilled(text):
    """Section names of a TODO-template file that are still empty or say TODO."""
    return [n for n in re.findall(r"^## (.+)$", text, re.M) if not section(text, n) or "TODO" in section(text, n)]


def has_criteria(text):
    return bool(re.search(r"^- \*\*AC-\d+\*\* (?!Given \.\.\.)", section(text, "Acceptance criteria"), re.M))


class Product:
    def __init__(self, root):
        self.root = Path(root)
        meta = self.root / "product.json"
        if not meta.exists():
            raise SystemExit(f"{meta} not found: run `chef.py --dir {root} init --name ...` first")
        self.meta = json.loads(meta.read_text(encoding="utf-8"))
        self.meta.setdefault("stages", {})

    def save(self):
        (self.root / "product.json").write_text(json.dumps(self.meta, indent=2) + "\n", encoding="utf-8")

    def read(self, name):
        path = self.root / name
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def items(self, kind):
        folder = {"Q": "questions", "D": "decisions", "F": "features"}[kind]
        out = []
        for path in sorted((self.root / folder).glob(f"{kind}-[0-9][0-9][0-9]*.md")):
            text = path.read_text(encoding="utf-8")
            out.append({"id": path.name[:5], "path": path, "text": text, "title": title(text), **fields(text)})
        return out

    def feature(self, fid):
        return next((f for f in self.items("F") if f["id"] == fid), None)

    def next_id(self, kind):
        nums = [int(i["id"][2:]) for i in self.items(kind)]
        return f"{kind}-{(max(nums) if nums else 0) + 1:03d}"

    def topics(self):
        rows = []
        for line in self.read("topics.md").splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")] if line.startswith("|") else []
            if len(cells) >= 5 and re.match(r"^[a-z0-9][a-z0-9-]*$", cells[0]) and cells[0] != "id":
                rows.append({"id": cells[0], "name": cells[1], "label": cells[2], "status": cells[3], "scope": cells[4]})
        return rows

    def screens(self):
        return [{"path": s, **fields(s.read_text(encoding="utf-8"))} for s in sorted((self.root / "design").glob("**/*.md"))
                if s.name not in ("README.md", "system.md")]

    def stage(self, item):
        return self.meta["stages"].get(item)

    def state(self, fid):
        """A feature's stage, or 'dropped', or 'with the MVP'."""
        return self.stage(fid) or ("dropped" if fid in self.meta.get("dropped", {}) else "with the MVP")

    def open_items(self):
        """Items with a stage of their own, in order: the MVP, then later features."""
        return ["mvp"] + [f["id"] for f in self.items("F") if f["id"] in self.meta["stages"]]


# ------------------------------------------------------------------ stages
def move_checks(p, item, target):
    """List of (passed, description) that must all pass before `item` moves to `target`."""
    out = []
    if item == "mvp":
        if target == "discovering":
            left = unfilled(p.read("vision.md"))
            out.append((not left, "vision filled in" + (f" (still empty: {', '.join(left)})" if left else "")))
        elif target == "scoped":
            for name in ("vision.md", "mvp.md"):
                left = unfilled(p.read(name))
                out.append((not left, f"{name} filled in" + (f" (still empty: {', '.join(left)})" if left else "")))
            mvp_topics = [t for t in p.topics() if t["label"] == "MVP"]
            left = [t["id"] for t in mvp_topics if t["status"] != "covered"]
            out.append((not left, f"all {len(mvp_topics)} MVP topics covered" + (f" (not yet: {', '.join(left)})" if left else "")))
            feats = [f for f in p.items("F") if f.get("Label") == "MVP"]
            no_ac = [f["id"] for f in feats if not has_criteria(f["text"])]
            out.append((bool(feats) and not no_ac, "every MVP feature has acceptance criteria"
                        + (f" (missing: {', '.join(no_ac)})" if no_ac else "" if feats else " (no MVP feature yet)")))
            out.append(((p.root / "toolset.json").exists(), "toolset.json written from the stack decision"))
    else:
        f = p.feature(item)
        if target == "scoped":
            out.append((not unfilled(f["text"]) and has_criteria(f["text"]), f"{item} has a goal and acceptance criteria"))
            live = {q["id"] for q in p.items("Q") if q.get("Status") in ("open", "discussing")}
            still = [q for q in ids(section(f["text"], "Open points")) if q in live]
            out.append((not still, f"no open point left in {item}" + (f" ({', '.join(still)})" if still else "")))
    if target == "scoped":
        blocking = [q["id"] for q in p.items("Q") if q.get("Status") in ("open", "discussing") and q.get("Blocking") == "yes"]
        out.append((not blocking, "no blocking question open" + (f" ({', '.join(blocking)})" if blocking else "")))
        proposed = [d["id"] for d in p.items("D") if d.get("Status") == "proposed"]
        out.append((not proposed, "no decision waiting for the owner" + (f" ({', '.join(proposed)})" if proposed else "")))
    elif target == "designed":
        out.append((fields(p.read("design/system.md")).get("Status") == "approved", "design system approved"))
        mine = [s for s in p.screens() if s.get("Item") == item]
        pending = [s["path"].stem for s in mine if s.get("Status") != "approved"]
        out.append((bool(mine) and not pending, f"every screen for {item} approved"
                    + (f" (pending: {', '.join(pending)})" if pending else "" if mine else " (no screen yet)")))
    elif target == "building" and item != "mvp":
        out.append((p.stage("mvp") == "shipped", "the MVP is shipped"))
    elif target == "shipped":
        out.append(((p.root / "build" / item / "summary.md").exists(), f"build/{item}/summary.md written"))
    return out


def next_stage(stage):
    return STAGES[STAGES.index(stage) + 1] if stage != "shipped" else None


def check_item(p, item):
    if item != "mvp":
        f = p.feature(item)
        if not f:
            raise SystemExit(f"{item} not found")
        if f.get("Label") == "MVP":
            raise SystemExit(f"{item} is labelled MVP: it travels with the MVP (use `mvp`)")
    if not p.stage(item):
        raise SystemExit(f"{item} has no stage in product.json")


def cmd_stage(args):
    p = Product(args.dir)
    check_item(p, args.item)
    now = p.stage(args.item)
    nxt = next_stage(now)
    if not args.to:
        print(f"{args.item}: {now}")
        if nxt:
            for ok, text in move_checks(p, args.item, nxt):
                print(("PASS   " if ok else "OPEN   ") + text)
            print(f"next: {nxt} (" + (f"starts with {STARTED_BY[nxt]})" if nxt in STARTED_BY else "needs /chef:approve)"))
        return
    if args.to != nxt:
        raise SystemExit(f"{args.item} is {now}; it can only move to {nxt or 'nothing (shipped)'}, one stage at a time")
    failed = [t for ok, t in move_checks(p, args.item, nxt) if not ok]
    if failed:
        print(f"refused: {args.item} cannot move to {nxt} yet")
        for t in failed:
            print("MISSING", t)
        sys.exit(1)
    p.meta["stages"][args.item] = nxt
    p.save()
    print(f"{args.item}: {now} -> {nxt}")


def focus(p):
    """The item to work on: the MVP until shipped, then the most advanced unfinished feature."""
    if p.stage("mvp") != "shipped":
        return "mvp"
    live = [i for i in p.open_items() if p.stage(i) != "shipped"]
    return max(live, key=lambda i: STAGES.index(p.stage(i)), default=None)


def next_move(p):
    """(command, why): the one move Chef suggests now."""
    left = unfilled(p.read("vision.md"))
    if left:
        return "/chef:vision", "finish the vision: " + ", ".join(left)
    item = focus(p)
    proposed = [d for d in p.items("D") if d.get("Status") == "proposed"]
    if proposed:
        d = proposed[0]
        topics = [q.get("Topic") for q in p.items("Q") if q["id"] in ids(d.get("Answers"))]
        return f"/chef:discover {topics[0] if topics else item or 'mvp'}", f"{d['id']} ({d['title']}) waits for your yes or no"
    if item is None:
        return "/chef:idea", "everything is shipped: capture the next idea"
    stage = p.stage(item)
    nxt = next_stage(stage)
    failed = [t for ok, t in move_checks(p, item, nxt) if not ok]
    if nxt in STARTED_BY:
        if nxt == "designing" and fields(p.read("design/system.md")).get("Status") != "approved":
            return "/chef:design system", "set the shared look before designing screens"
        return f"{STARTED_BY[nxt]} {item}", ("first: " + failed[0]) if failed else f"move {item} to {nxt}"
    if not failed:
        return f"/chef:approve {item}", f"{item} is ready to be {nxt}: say yes or no"
    if stage == "discovering" and item == "mvp":
        topics = sorted((t for t in p.topics() if t["label"] == "MVP" and t["status"] != "covered"),
                        key=lambda t: t["status"] != "in progress")
        if topics:
            return f"/chef:discover {topics[0]['id']}", f"settle the MVP topic '{topics[0]['name']}'"
    command = {"discovering": "/chef:discover", "designing": "/chef:design", "building": "/chef:build"}[stage]
    return f"{command} {item}", "still missing: " + failed[0]


def waiting_on_owner(p):
    out = [f"{d['id']}: {d['title']} (decision)" for d in p.items("D") if d.get("Status") == "proposed"]
    for item in p.open_items():
        nxt = next_stage(p.stage(item))
        if nxt and nxt not in STARTED_BY and all(ok for ok, _ in move_checks(p, item, nxt)):
            out.append(f"{item}: ready to be {nxt} (/chef:approve {item})")
    return out


def cmd_next(args):
    command, why = next_move(Product(args.dir))
    print(f"{command}\n{why}")


# ------------------------------------------------------------------ records
def cmd_init(args):
    root = Path(args.dir)
    if (root / "product.json").exists():
        raise SystemExit(f"{root} already holds a product")
    shutil.copytree(KIT / "templates" / "product", root, dirs_exist_ok=True)
    meta = {"name": args.name, "created": today(), "chef_version": kit_version(),
            "stages": {"mvp": "idea"}, "separation_terms": []}
    (root / "product.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    for path in root.rglob("*.md"):
        path.write_text(path.read_text(encoding="utf-8").replace("{{PRODUCT}}", args.name), encoding="utf-8")
    print(f"created {root} for {args.name}")


def fill(template, **values):
    text = (KIT / "templates" / template).read_text(encoding="utf-8")
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def cmd_add_topic(args):
    p = Product(args.dir)
    if not re.match(r"^[a-z0-9][a-z0-9-]*$", args.id):
        raise SystemExit("topic id: lowercase letters, digits and dashes only")
    if args.id in {t["id"] for t in p.topics()}:
        raise SystemExit(f"topic {args.id!r} already exists")
    row = f"| {args.id} | {args.name} | {args.label} | open | {args.scope or '-'} |"
    (p.root / "topics.md").write_text(p.read("topics.md").rstrip("\n") + "\n" + row + "\n", encoding="utf-8")
    print(args.id)


def cmd_add_question(args):
    p = Product(args.dir)
    known = {t["id"] for t in p.topics()}
    if args.topic not in known:
        raise SystemExit(f"unknown topic {args.topic!r}; add it first with add-topic ({', '.join(sorted(known))})")
    qid = p.next_id("Q")
    body = fill("question.md", ID=qid, TITLE=args.title, TOPIC=args.topic, BLOCKING="yes" if args.blocking else "no",
                DATE=today(), CONTEXT=args.context or "", OPTIONS=args.options or "-")
    (p.root / "questions" / f"{qid}-{slug(args.title)}.md").write_text(body, encoding="utf-8")
    print(qid)


def cmd_add_decision(args):
    p = Product(args.dir)
    answers = ids(args.answers)
    missing = [a for a in answers if a not in {q["id"] for q in p.items("Q")}]
    if missing:
        raise SystemExit(f"unknown questions: {', '.join(missing)}")
    did = p.next_id("D")
    body = fill("decision.md", ID=did, TITLE=args.title, STATUS="accepted" if args.accepted else "proposed",
                DATE=today(), ANSWERS=", ".join(answers) or "-", SOURCE=args.source or "-",
                DECISION=args.decision, WHY=args.why or "", CONSEQUENCES=args.consequences or "")
    (p.root / "decisions" / f"{did}-{slug(args.title)}.md").write_text(body, encoding="utf-8")
    if args.accepted:
        mark_answered(p, did, answers)
    else:
        for q in p.items("Q"):
            if q["id"] in answers and q.get("Status") == "open":
                q["path"].write_text(set_field(q["text"], "Status", "discussing"), encoding="utf-8")
    print(did)


def mark_answered(p, did, answers):
    for q in p.items("Q"):
        if q["id"] in answers:
            text = set_field(q["text"], "Status", "decided")
            q["path"].write_text(set_field(text, "Answered by", did), encoding="utf-8")


def cmd_accept(args):
    p = Product(args.dir)
    for d in p.items("D"):
        if d["id"] == args.id:
            if d.get("Status") == "accepted":
                print(f"{args.id} is already accepted")
                return
            d["path"].write_text(set_field(set_field(d["text"], "Status", "accepted"), "Date", today()), encoding="utf-8")
            mark_answered(p, args.id, ids(d.get("Answers")))
            print(f"accepted {args.id}")
            return
    raise SystemExit(f"{args.id} not found")


def cmd_add_feature(args):
    p = Product(args.dir)
    fid = p.next_id("F")
    body = fill("feature.md", ID=fid, TITLE=args.title, LABEL=args.label, GOAL=args.goal or "TODO")
    (p.root / "features" / f"{fid}-{slug(args.title)}.md").write_text(body, encoding="utf-8")
    if args.label == "later":
        p.meta["stages"][fid] = "idea"
        p.save()
    print(fid)


def cmd_topic(args):
    p = Product(args.dir)
    text = p.read("topics.md")
    pattern = re.compile(r"^(\|\s*" + re.escape(args.id) + r"\s*\|[^|]*\|[^|]*\|\s*)([^|]*?)(\s*\|)", re.M)
    if not pattern.search(text):
        raise SystemExit(f"unknown topic {args.id!r}")
    (p.root / "topics.md").write_text(pattern.sub(lambda m: m.group(1) + args.status + m.group(3), text, count=1),
                                      encoding="utf-8")
    print(f"{args.id}: {args.status}")


def cmd_drop(args):
    """Park a later feature for good. The file stays, so its id is never reused."""
    p = Product(args.dir)
    check_item(p, args.id)
    if p.stage(args.id) not in ("idea", "discovering"):
        raise SystemExit(f"{args.id} is {p.stage(args.id)}; only an idea or a feature in discovery can be dropped")
    del p.meta["stages"][args.id]
    p.meta.setdefault("dropped", {})[args.id] = f"{today()}: {args.reason}"
    p.save()
    print(f"dropped {args.id}")


# ------------------------------------------------------------------ checks
def separation_problems(p):
    """Chef must never mention a product, so it stays reusable."""
    errs = []
    if KIT.resolve() in p.root.resolve().parents or KIT.resolve() == p.root.resolve():
        return errs                                             # a product inside Chef (tests)
    name = p.meta.get("name", "")
    tokens = {name.lower(), slug(name), name.lower().replace(" ", "")} | {t.lower() for t in p.meta.get("separation_terms", [])}
    tokens = {t for t in tokens if len(t) > 3}
    for path in KIT.rglob("*"):
        if {"tests", ".git"} & set(path.relative_to(KIT).parts):
            continue                                            # test fixtures use sample names
        if path.is_file() and path.suffix in (".md", ".py", ".json", ".html", ".txt", ".css", ".js"):
            text = path.read_text(encoding="utf-8", errors="ignore").lower()
            for tok in sorted(tokens):
                if tok in text:
                    errs.append(f"separation: {path.relative_to(KIT.parent)} mentions {tok!r}")
    return errs


def problems(p):
    errs = []
    topics = p.topics()
    for t in topics:
        if t["status"] not in TOPIC_STATUSES:
            errs.append(f"topics.md: {t['id']} has status {t['status']!r}, expected one of {TOPIC_STATUSES}")
        if t["label"] not in LABELS:
            errs.append(f"topics.md: {t['id']} has label {t['label']!r}, expected one of {LABELS}")
    known_topics = {t["id"] for t in topics}
    qs, ds, fs = p.items("Q"), p.items("D"), p.items("F")
    known = {i["id"] for i in qs + ds + fs}
    accepted = {d["id"] for d in ds if d.get("Status") == "accepted"}
    for q in qs:
        where = q["path"].name
        for key in ("Status", "Topic", "Blocking", "Raised", "Answered by"):
            if key not in q:
                errs.append(f"{where}: missing field {key}")
        if q.get("Status") not in Q_STATUSES:
            errs.append(f"{where}: status {q.get('Status')!r} not in {Q_STATUSES}")
        if q.get("Topic") not in known_topics:
            errs.append(f"{where}: topic {q.get('Topic')!r} is not in topics.md")
        if q.get("Status") == "decided" and not (set(ids(q.get("Answered by"))) & accepted):
            errs.append(f"{where}: decided, but no accepted decision answers it")
    for d in ds:
        where = d["path"].name
        if d.get("Status") not in D_STATUSES:
            errs.append(f"{where}: status {d.get('Status')!r} not in {D_STATUSES}")
        if not section(d["text"], "Decision"):
            errs.append(f"{where}: empty Decision section")
    for f in fs:
        if f.get("Label") not in LABELS:
            errs.append(f"{f['path'].name}: label {f.get('Label')!r} not in {LABELS}")
        elif f.get("Label") == "MVP" and f["id"] in p.meta["stages"]:
            errs.append(f"product.json: {f['id']} is labelled MVP, so it has no stage of its own")
        elif f.get("Label") == "later" and f["id"] not in p.meta["stages"] and f["id"] not in p.meta.get("dropped", {}):
            errs.append(f"product.json: {f['id']} is labelled later but has no stage")
    for item in qs + ds + fs:
        for ref in ids(item["text"]):
            if ref not in known:
                errs.append(f"{item['path'].name}: refers to unknown {ref}")
    for item, stage in p.meta["stages"].items():
        if stage not in STAGES:
            errs.append(f"product.json: {item} has stage {stage!r}, expected one of {STAGES}")
        if item != "mvp" and item not in {f["id"] for f in fs}:
            errs.append(f"product.json: stage for unknown item {item}")
    if "mvp" not in p.meta["stages"]:
        errs.append("product.json: no stage for mvp")
    toolset = p.root / "toolset.json"
    if toolset.exists():
        try:
            json.loads(toolset.read_text(encoding="utf-8"))
        except ValueError as exc:
            errs.append(f"toolset.json: not valid JSON ({exc})")
    return errs + separation_problems(p)


def cmd_check(args):
    errs = problems(Product(args.dir))
    for e in errs:
        print("ERROR", e)
    print(f"{len(errs)} problem(s)")
    sys.exit(1 if errs else 0)


def cmd_status(args):
    p = Product(args.dir)
    qs, ds = p.items("Q"), p.items("D")
    live = [q for q in qs if q.get("Status") in ("open", "discussing")]
    print(f"{p.meta['name']}: MVP {p.stage('mvp')}")
    for f in p.items("F"):
        print(f"  {f['id']} {f['title']:<40} {p.state(f['id'])}")
    print(f"questions: {len(live)} open of {len(qs)} ({sum(q.get('Blocking') == 'yes' for q in live)} blocking)")
    print(f"decisions: {sum(d.get('Status') == 'accepted' for d in ds)} accepted, "
          f"{sum(d.get('Status') == 'proposed' for d in ds)} waiting for the owner")
    for w in waiting_on_owner(p):
        print(f"waiting on you: {w}")
    command, why = next_move(p)
    print(f"next: {command}  ({why})")


# ------------------------------------------------------------------ dependencies and settings
def enabled_plugins(project):
    out = {}
    for path in (Path.home() / ".claude" / "settings.json", project / ".claude" / "settings.json",
                 project / ".claude" / "settings.local.json"):
        try:
            out.update(json.loads(path.read_text(encoding="utf-8")).get("enabledPlugins", {}))
        except (OSError, ValueError, AttributeError):
            pass
    return out


def plugin_found(name, project):
    if any(k.split("@")[0] == name and v for k, v in enabled_plugins(project).items()):
        return True
    root = Path.home() / ".claude" / "plugins"
    return any(root.glob(f"*/{name}/.claude-plugin")) or any(root.glob(f"*/*/{name}/.claude-plugin"))


def dep_checks(project):
    out = [(sys.version_info >= (3, 9), "Python 3.9+ for chef.py", "install Python 3.9 or newer")]
    for name, hint in PLUGINS.items():
        out.append((plugin_found(name, project), f"plugin {name}", f"install {hint}"))
    out.append((bool(shutil.which("uv")), "uv", "install uv: https://docs.astral.sh/uv/"))
    out.append((bool(shutil.which("graphify")), "Graphify CLI", "install Graphify with uv (needs Python 3.11+)"))
    return out


def cmd_deps(args):
    missing = 0
    for ok, name, hint in dep_checks(Path(args.project)):
        print(f"OK      {name}" if ok else f"MISSING {name}: {hint}")
        missing += not ok
    sys.exit(1 if missing else 0)


def merge_settings(project, product_dir):
    """Add Chef's project settings without overwriting anything the owner set. Returns what changed."""
    path = project / ".claude" / "settings.json"
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    changed = []
    env = data.setdefault("env", {})
    if "PONYTAIL_DEFAULT_MODE" not in env:
        env["PONYTAIL_DEFAULT_MODE"] = "off"
        changed.append("Ponytail off by default")
    try:
        rel = Path(os.path.relpath(Path(product_dir).resolve(), project.resolve())).as_posix()
    except ValueError:                                      # another drive on Windows
        rel = Path(product_dir).resolve().as_posix()
    glob = f"{rel}/**"
    globs = [g.strip() for g in env.get("GATEGUARD_EXEMPT_GLOBS", "").split(",") if g.strip()]
    if glob not in globs:
        env["GATEGUARD_EXEMPT_GLOBS"] = ",".join(globs + [glob])
        changed.append(f"GateGuard skips {glob}")
    markets = data.setdefault("extraKnownMarketplaces", {})
    if "ponytail" not in markets:
        markets["ponytail"] = {"source": {"source": "github", "repo": "DietrichGebert/ponytail"}}
        changed.append("Ponytail marketplace declared")
    plugins = data.setdefault("enabledPlugins", {})
    if "ponytail@ponytail" not in plugins:
        plugins["ponytail@ponytail"] = True
        changed.append("Ponytail plugin enabled (its level stays off until Build)")
    if changed:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return changed


def cmd_settings(args):
    changed = merge_settings(Path(args.project), args.dir)
    print("\n".join(changed) if changed else "settings already in place")


# ------------------------------------------------------------------ dashboard
def cmd_dashboard(args):
    p = Product(args.dir)
    out = Path(args.out) if args.out else p.root / "dashboard.html"
    out.write_text(render_dashboard(p), encoding="utf-8")
    print(f"wrote {out}")
    if args.open:
        webbrowser.open(out.resolve().as_uri())


def esc(s):
    return html.escape(str(s or ""))


def first_para(text, limit=280):
    para = re.split(r"\n\s*\n", text.strip())[0] if text.strip() else ""
    para = re.sub(r"\s+", " ", para)
    return para if len(para) <= limit else para[:limit].rsplit(" ", 1)[0] + "..."


CSS = """
:root{--bg:#f6f2ea;--panel:#fffdf8;--ink:#2a2230;--muted:#6f6474;--line:#e6dccb;--accent:#1f7f86;--warm:#b5650f;--bad:#b4462f;--ok:#2f7d4f;--soft:#efe6d6}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#17121c;--panel:#221a29;--ink:#f3eadb;--muted:#b3a6b5;--line:#3a2f43;--accent:#5fc0c7;--warm:#f0a84a;--bad:#ef7a62;--ok:#6cc98f;--soft:#2c2235}}
:root[data-theme="dark"]{--bg:#17121c;--panel:#221a29;--ink:#f3eadb;--muted:#b3a6b5;--line:#3a2f43;--accent:#5fc0c7;--warm:#f0a84a;--bad:#ef7a62;--ok:#6cc98f;--soft:#2c2235}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1180px;margin:0 auto;padding:28px 16px 60px}
header{display:flex;justify-content:space-between;align-items:flex-end;flex-wrap:wrap;gap:14px;margin-bottom:20px}
h1{margin:0;font-size:30px;letter-spacing:-.5px}h1 small{display:block;font-size:14px;color:var(--muted);font-weight:500;letter-spacing:0}
h2{font-size:19px;margin:30px 0 12px}h3{font-size:14px;margin:18px 0 8px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em}
.stats{display:flex;gap:10px;flex-wrap:wrap}.stat{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:8px 14px;min-width:96px}
.stat b{font-size:22px;display:block;line-height:1.1}.stat span{font-size:12px;color:var(--muted)}.stat.warn b{color:var(--bad)}
.next{background:var(--panel);border:2px solid var(--accent);border-radius:16px;padding:16px 20px}
.next .k{font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:var(--accent);font-weight:700}
.next code.cmd{display:block;font:700 20px ui-monospace,Consolas,monospace;color:var(--ink);margin:2px 0;overflow-wrap:anywhere}.next p{margin:0;color:var(--muted)}
.wait{margin:0;padding:0;list-style:none}.wait li{background:var(--panel);border:1px dashed var(--warm);border-radius:10px;padding:6px 12px;margin:6px 0}
ol.track{list-style:none;padding:0;margin:0;display:grid;grid-template-columns:repeat(7,1fr);gap:6px}
ol.track li{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:8px 6px;text-align:center;font-size:13px;color:var(--muted)}
ol.track li.done{background:color-mix(in srgb,var(--ok) 14%,var(--panel));color:var(--ok)}
ol.track li.now{border:2px solid var(--accent);color:var(--ink);font-weight:700}
.checks{margin:10px 0 0;padding:0;list-style:none}.checks li{padding:3px 0 3px 26px;position:relative}
.checks li:before{position:absolute;left:2px;top:3px;font-weight:700}.checks li.ok:before{content:"\\2713";color:var(--ok)}.checks li.todo:before{content:"\\25CB";color:var(--warm)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:10px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:12px 14px}
.card p{margin:4px 0 0;color:var(--muted);font-size:13px}.th{display:flex;justify-content:space-between;gap:8px;align-items:baseline}
.pill{font-size:11px;padding:2px 8px;border-radius:99px;background:var(--soft);color:var(--muted);white-space:nowrap}
.pill.covered,.pill.shipped{background:color-mix(in srgb,var(--ok) 20%,transparent);color:var(--ok)}
.pill.in-progress,.pill.discovering,.pill.designing,.pill.building{background:color-mix(in srgb,var(--warm) 22%,transparent);color:var(--warm)}
.cols{display:grid;grid-template-columns:3fr 2fr;gap:24px}
details{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:8px 12px;margin:6px 0}
summary{cursor:pointer}details p{margin:8px 0 2px;color:var(--muted);font-size:13.5px}
code{font:600 12px ui-monospace,Consolas,monospace;color:var(--accent);margin-right:4px}.count{font-size:12px;background:var(--soft);border-radius:99px;padding:1px 8px;margin-left:4px;color:var(--ink)}
.tag{font-size:11px;border-radius:99px;padding:1px 8px;margin-left:6px;white-space:nowrap}.tag.blk{background:color-mix(in srgb,var(--bad) 18%,transparent);color:var(--bad)}
.tag.disc{background:color-mix(in srgb,var(--warm) 20%,transparent);color:var(--warm)}
details.d.proposed{border-style:dashed;border-color:var(--warm)}details.d small{color:var(--muted);white-space:nowrap}
footer{margin-top:40px;color:var(--muted);font-size:12px}
:root{color-scheme:light dark}:root[data-theme="light"]{color-scheme:light}:root[data-theme="dark"]{color-scheme:dark}
.top{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.theme{font:600 13px system-ui,sans-serif;color:var(--ink);background:var(--panel);border:1px solid var(--line);border-radius:99px;padding:6px 12px;cursor:pointer}
.theme:hover{border-color:var(--accent)}.theme:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
@media (max-width:820px){ol.track{grid-template-columns:repeat(4,1fr)}.cols{grid-template-columns:1fr}}
@media (max-width:480px){ol.track{grid-template-columns:repeat(2,1fr)}h1{font-size:25px}.next code.cmd{font-size:17px}}
"""


# Theme: auto follows the system; the button cycles auto -> dark -> light and remembers the choice
# in this browser. Storage can be blocked for file:// pages, so every access is guarded.
THEME_EARLY_JS = ("try{var t=localStorage.getItem('chef-theme');"
                  "if(t==='dark'||t==='light')document.documentElement.dataset.theme=t}catch(e){}")
THEME_JS = """(function(){var b=document.getElementById('theme'),r=document.documentElement,order=['auto','dark','light'];
function show(t){b.textContent='Theme: '+t}
show(r.dataset.theme||'auto');
b.addEventListener('click',function(){var t=order[(order.indexOf(r.dataset.theme||'auto')+1)%3];
if(t==='auto')delete r.dataset.theme;else r.dataset.theme=t;
try{localStorage.setItem('chef-theme',t)}catch(e){}show(t)})})();"""


def render_dashboard(p):
    qs, ds, feats, topics = p.items("Q"), p.items("D"), p.items("F"), p.topics()
    open_qs = [q for q in qs if q.get("Status") in ("open", "discussing")]
    blocking = [q for q in open_qs if q.get("Blocking") == "yes"]
    accepted = [d for d in ds if d.get("Status") == "accepted"]
    proposed = [d for d in ds if d.get("Status") == "proposed"]
    command, why = next_move(p)
    waiting = "".join(f"<li>{esc(w)}</li>" for w in waiting_on_owner(p))

    item = focus(p) or "mvp"
    stage = p.stage(item)
    track = "".join(f'<li class="{"done" if STAGES.index(stage) > i else "now" if s == stage else ""}">{s}</li>'
                    for i, s in enumerate(STAGES))
    nxt = next_stage(stage)
    checks = "".join(f'<li class="{"ok" if ok else "todo"}">{esc(t)}</li>'
                     for ok, t in (move_checks(p, item, nxt) if nxt else []))
    item_name = "MVP" if item == "mvp" else f"{item} {esc(p.feature(item)['title'])}"

    def feature_card(f):
        st = p.state(f["id"])
        return (f'<div class="card"><div class="th"><b><code>{f["id"]}</code>{esc(f["title"])}</b>'
                f'<span class="pill {esc(st.replace(" ", "-"))}">{esc(st)}</span></div>'
                f'<p>{esc(first_para(section(f["text"], "Goal"), 160))}</p></div>')

    def topic_card(t):
        mine = [q for q in qs if q.get("Topic") == t["id"]]
        left = [q for q in mine if q.get("Status") in ("open", "discussing")]
        return (f'<div class="card"><div class="th"><b>{esc(t["name"])}</b>'
                f'<span class="pill {esc(t["status"].replace(" ", "-"))}">{esc(t["status"])}</span></div>'
                f'<p>{esc(t["scope"])}</p><p>{len(mine) - len(left)} of {len(mine)} questions decided</p></div>')

    def q_row(q):
        tags = '<span class="tag blk">blocking</span>' if q.get("Blocking") == "yes" else ""
        if q.get("Status") == "discussing":
            tags += '<span class="tag disc">has a proposal</span>'
        return (f'<details class="q"><summary><code>{q["id"]}</code>{esc(q["title"])}{tags}</summary>'
                f'<p>{esc(first_para(section(q["text"], "Context")))}</p></details>')

    def d_row(d):
        ans = ", ".join(ids(d.get("Answers")))
        return (f'<details class="d {esc(d.get("Status"))}"><summary><code>{d["id"]}</code>{esc(d["title"])}'
                f'{f" <small>answers {esc(ans)}</small>" if ans else ""}</summary>'
                f'<p>{esc(first_para(section(d["text"], "Decision"), 420))}</p></details>')

    def block(name, cards):
        return f'<h3>{name}</h3><div class="grid">{cards}</div>' if cards else ""

    groups = []
    for t in topics:
        mine = sorted((q for q in open_qs if q.get("Topic") == t["id"]), key=lambda q: (q.get("Blocking") != "yes", q["id"]))
        if mine:
            groups.append(f'<h3>{esc(t["name"])}<span class="count">{len(mine)}</span></h3>' + "".join(q_row(q) for q in mine))
    features = (block("MVP", "".join(feature_card(f) for f in feats if f.get("Label") == "MVP"))
                + block("Later", "".join(feature_card(f) for f in feats if f.get("Label") != "MVP")))
    topic_html = (block("MVP", "".join(topic_card(t) for t in topics if t["label"] == "MVP"))
                  + block("Later", "".join(topic_card(t) for t in topics if t["label"] != "MVP")))

    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(p.meta['name'])} &middot; Chef</title><style>{CSS}</style>
<script>{THEME_EARLY_JS}</script></head>
<body><main>
<header><div class="top"><h1>{esc(p.meta['name'])}<small>Chef dashboard &middot; generated {today()}</small></h1>
<button class="theme" id="theme" type="button" title="Switch between auto, dark and light">Theme: auto</button></div>
<div class="stats"><div class="stat"><b>{len(open_qs)}</b><span>open questions</span></div>
<div class="stat {'warn' if blocking else ''}"><b>{len(blocking)}</b><span>blocking</span></div>
<div class="stat"><b>{len(proposed)}</b><span>awaiting your yes</span></div>
<div class="stat"><b>{len(accepted)}</b><span>decided</span></div>
<div class="stat"><b>{len(feats)}</b><span>features</span></div></div></header>
<section class="next"><div class="k">Next move</div><code class="cmd">{esc(command)}</code><p>{esc(why)}</p></section>
{f'<h3>Waiting on you</h3><ul class="wait">{waiting}</ul>' if waiting else ''}
<h2>{item_name}</h2><ol class="track">{track}</ol>
{f'<ul class="checks">{checks}</ul>' if checks else ''}
<h2>Features</h2>{features or '<p>None yet.</p>'}
<h2>Topics</h2>{topic_html or '<p>None yet.</p>'}
<div class="cols"><section><h2>Open questions</h2>{''.join(groups) or '<p>None open.</p>'}</section>
<section><h2>Awaiting your decision</h2>{''.join(d_row(d) for d in proposed) or '<p>Nothing waiting.</p>'}
<h2>Decided</h2>{''.join(d_row(d) for d in reversed(accepted)) or '<p>Nothing yet.</p>'}</section></div>
<footer>Generated by Chef from the product folder. Edit the files, not this page.</footer>
</main><script>{THEME_JS}</script></body></html>"""


# ------------------------------------------------------------------ entry point
def kit_version():
    try:
        return json.loads((KIT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
    except (OSError, KeyError, ValueError):
        return "unknown"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dir", default="product", help="product folder (default: ./product)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("init")
    s.add_argument("--name", required=True)
    s = sub.add_parser("add-topic")
    s.add_argument("--id", required=True)
    s.add_argument("--name", required=True)
    s.add_argument("--label", choices=LABELS, required=True)
    s.add_argument("--scope")
    s = sub.add_parser("add-question")
    s.add_argument("--title", required=True)
    s.add_argument("--topic", required=True)
    s.add_argument("--blocking", action="store_true")
    s.add_argument("--context")
    s.add_argument("--options")
    s = sub.add_parser("add-decision")
    s.add_argument("--title", required=True)
    s.add_argument("--decision", required=True)
    s.add_argument("--why")
    s.add_argument("--consequences")
    s.add_argument("--answers", default="")
    s.add_argument("--source")
    s.add_argument("--accepted", action="store_true", help="only on the owner's explicit word")
    s = sub.add_parser("accept")
    s.add_argument("id")
    s = sub.add_parser("add-feature")
    s.add_argument("--title", required=True)
    s.add_argument("--label", choices=LABELS, required=True)
    s.add_argument("--goal")
    s = sub.add_parser("topic")
    s.add_argument("id")
    s.add_argument("status", choices=TOPIC_STATUSES)
    s = sub.add_parser("drop")
    s.add_argument("id")
    s.add_argument("--reason", required=True)
    s = sub.add_parser("stage")
    s.add_argument("item")
    s.add_argument("to", nargs="?", choices=STAGES)
    for name in ("next", "status", "check"):
        sub.add_parser(name)
    s = sub.add_parser("dashboard")
    s.add_argument("--out")
    s.add_argument("--open", action="store_true", help="open it in the local browser")
    for name in ("deps", "settings"):
        s = sub.add_parser(name)
        s.add_argument("--project", default=".", help="the product's repository (default: .)")
    args = ap.parse_args(argv)
    {"init": cmd_init, "add-topic": cmd_add_topic, "add-question": cmd_add_question, "add-decision": cmd_add_decision,
     "accept": cmd_accept, "add-feature": cmd_add_feature, "topic": cmd_topic, "drop": cmd_drop, "stage": cmd_stage, "next": cmd_next, "status": cmd_status,
     "check": cmd_check, "dashboard": cmd_dashboard, "deps": cmd_deps, "settings": cmd_settings}[args.cmd](args)


if __name__ == "__main__":
    main()
