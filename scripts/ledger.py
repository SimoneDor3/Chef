#!/usr/bin/env python3
"""Product ledger: the files that carry a product from first idea to maintenance.

Usage: python ledger.py [--dir PRODUCT_DIR] <command> [options]

Commands
  init --name NAME              create a product folder from the kit templates
  add-question ...              record a new open question (prints its id)
  add-decision ...              record a decision, proposed unless --accepted (prints its id)
  accept D-001                  accept a decision; questions it answers become decided
  status                        one-screen summary: phase, topics, open questions, decisions
  gate PHASE                    check a phase's exit criteria (frame, discover, design, build)
  check                         validate every file, every link, and the kit/product separation
  dashboard [--out FILE]        write a self-contained HTML overview

Standard library only, so it runs anywhere Python 3.9+ does. The product folder defaults to
./product; pass --dir to point elsewhere.
"""
import argparse
import datetime as dt
import html
import json
import re
import shutil
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
PHASES = ["frame", "discover", "design", "build"]
PHASE_TITLES = {"frame": "Frame", "discover": "Discover", "design": "Design", "build": "Build & maintain"}
Q_STATUSES = ["open", "discussing", "decided", "dropped"]
D_STATUSES = ["proposed", "accepted", "superseded", "rejected"]
TOPIC_STATUSES = ["open", "in progress", "covered"]


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


class Product:
    def __init__(self, root):
        self.root = Path(root)
        meta = self.root / "product.json"
        if not meta.exists():
            raise SystemExit(f"{meta} not found: run `ledger.py --dir {root} init --name ...` first")
        self.meta = json.loads(meta.read_text(encoding="utf-8"))

    def items(self, kind):
        folder = {"Q": "questions", "D": "decisions", "F": "features"}[kind]
        out = []
        for path in sorted((self.root / folder).glob(f"{kind}-[0-9][0-9][0-9]*.md")):
            text = path.read_text(encoding="utf-8")
            out.append({"id": path.name[:5], "path": path, "text": text, "title": title(text), **fields(text)})
        return out

    def next_id(self, kind):
        nums = [int(i["id"][2:]) for i in self.items(kind)]
        return f"{kind}-{(max(nums) if nums else 0) + 1:03d}"

    def table_rows(self, name, min_cells):
        rows = []
        for line in (self.root / name).read_text(encoding="utf-8").splitlines():
            if not line.startswith("|"):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= min_cells and not set("".join(cells)) <= set("-: "):
                rows.append(cells)
        return rows

    def topics(self):
        return [{"id": c[0], "name": c[1], "status": c[2], "scope": c[3]}
                for c in self.table_rows("topics.md", 4) if re.match(r"^[a-z0-9-]+$", c[0]) and c[0] != "id"]

    def gates(self):
        return {c[0].lower(): {"status": c[1], "date": c[2], "note": c[3] if len(c) > 3 else ""}
                for c in self.table_rows("gates.md", 3) if c[0].lower() in PHASES}


# ------------------------------------------------------------------ commands
def cmd_init(args):
    root = Path(args.dir)
    if (root / "product.json").exists():
        raise SystemExit(f"{root} already holds a product")
    shutil.copytree(KIT / "templates" / "product", root, dirs_exist_ok=True)
    meta = {"name": args.name, "phase": "frame", "kit_version": kit_version(), "created": today(),
            "separation_terms": []}
    (root / "product.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    for path in root.rglob("*.md"):
        path.write_text(path.read_text(encoding="utf-8").replace("{{PRODUCT}}", args.name), encoding="utf-8")
    print(f"created {root} for {args.name}")


def fill(template, **values):
    text = (KIT / "templates" / template).read_text(encoding="utf-8")
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def cmd_add_question(args):
    p = Product(args.dir)
    known = {t["id"] for t in p.topics()}
    if args.topic not in known:
        raise SystemExit(f"unknown topic {args.topic!r}; add it to topics.md first ({', '.join(sorted(known))})")
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


GATE_RULES = {
    "frame": "vision filled in",
    "discover": "topics covered, nothing blocking, features specified",
    "design": "every screen approved",
    "build": "owner sign-off per release",
}


def gate_checks(p, phase):
    """List of (passed, description) for a phase's exit criteria."""
    out = []
    if phase == "frame":
        vision = (p.root / "vision.md").read_text(encoding="utf-8")
        for name in re.findall(r"^## (.+)$", vision, re.M):
            body = section(vision, name)
            out.append((bool(body) and "TODO" not in body, f"vision: '{name}' filled in"))
    elif phase == "discover":
        topics = p.topics()
        left = [t["id"] for t in topics if t["status"] != "covered"]
        out.append((not left, f"all {len(topics)} topics covered" + (f" ({len(left)} not yet)" if left else "")))
        blocking = [q["id"] for q in p.items("Q") if q.get("Status") in ("open", "discussing") and q.get("Blocking") == "yes"]
        out.append((not blocking, "no blocking question open" + (f" ({len(blocking)} open)" if blocking else "")))
        proposed = [d["id"] for d in p.items("D") if d.get("Status") == "proposed"]
        out.append((not proposed, "no decision waiting for the owner" + (f" ({len(proposed)} waiting)" if proposed else "")))
        feats = p.items("F")
        no_ac = [f["id"] for f in feats if not re.search(r"^- \*\*AC-\d+", section(f["text"], "Acceptance criteria"), re.M)]
        out.append((bool(feats) and not no_ac, f"{len(feats)} features written, each with acceptance criteria"
                    + (f" ({len(no_ac)} missing criteria)" if no_ac else "")))
        for folder in ("journeys", "data-sources"):
            n = len([x for x in (p.root / folder).glob("*.md") if x.name != "README.md"])
            out.append((n > 0, f"{folder}: {n} written"))
    elif phase == "design":
        screens = [s for s in (p.root / "design").glob("**/*.md") if s.name != "README.md"]
        pending = [s for s in screens if fields(s.read_text(encoding="utf-8")).get("Status") != "approved"]
        out.append((bool(screens) and not pending, f"{len(screens)} screens, all approved"
                    + (f" ({len(pending)} pending)" if pending else "")))
    elif phase == "build":
        out.append((p.gates().get("design", {}).get("status") == "passed", "design gate signed"))
    return out


def cmd_gate(args):
    p = Product(args.dir)
    checks = gate_checks(p, args.phase)
    for ok, text in checks:
        print(("PASS   " if ok else "OPEN   ") + text)
    signed = p.gates().get(args.phase, {}).get("status") == "passed"
    print(("SIGNED " if signed else "WAITING") + f" owner sign-off in gates.md for {args.phase}")
    sys.exit(0 if all(ok for ok, _ in checks) else 1)


def separation_problems(p):
    """The kit must never mention the product, so it can be extracted as its own project."""
    errs = []
    if KIT.resolve() in p.root.resolve().parents or KIT.resolve() == p.root.resolve():
        return errs                                             # a product inside the kit (tests)
    name = p.meta.get("name", "")
    tokens = {name.lower(), slug(name), name.lower().replace(" ", "")} | {t.lower() for t in p.meta.get("separation_terms", [])}
    tokens = {t for t in tokens if len(t) > 3}
    for path in KIT.rglob("*"):
        if "tests" in path.relative_to(KIT).parts:
            continue                                            # test fixtures use sample names
        if path.is_file() and path.suffix in (".md", ".py", ".json", ".html", ".txt", ".css", ".js"):
            text = path.read_text(encoding="utf-8", errors="ignore").lower()
            for tok in sorted(tokens):
                if tok in text:
                    errs.append(f"kit separation: {path.relative_to(KIT.parent)} mentions {tok!r}")
    return errs


def problems(p):
    errs = []
    topics = p.topics()
    for t in topics:
        if t["status"] not in TOPIC_STATUSES:
            errs.append(f"topics.md: {t['id']} has status {t['status']!r}, expected one of {TOPIC_STATUSES}")
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
    for item in qs + ds + fs:
        for ref in ids(item["text"]):
            if ref not in known:
                errs.append(f"{item['path'].name}: refers to unknown {ref}")
    if p.meta.get("phase") not in PHASES:
        errs.append(f"product.json: phase {p.meta.get('phase')!r} not in {PHASES}")
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
    print(f"{p.meta['name']}: phase {PHASE_TITLES.get(p.meta['phase'], p.meta['phase'])}")
    print(f"questions: {len(live)} open of {len(qs)} ({sum(q.get('Blocking') == 'yes' for q in live)} blocking)")
    print(f"decisions: {sum(d.get('Status') == 'accepted' for d in ds)} accepted, "
          f"{sum(d.get('Status') == 'proposed' for d in ds)} waiting for the owner")
    for t in p.topics():
        mine = [q for q in qs if q.get("Topic") == t["id"]]
        left = [q for q in mine if q.get("Status") in ("open", "discussing")]
        print(f"  {t['id']:<22} {t['status']:<12} {len(left):>2} open of {len(mine):>2}")


# ------------------------------------------------------------------ dashboard
def cmd_dashboard(args):
    p = Product(args.dir)
    out = Path(args.out) if args.out else p.root / "dashboard.html"
    out.write_text(render_dashboard(p), encoding="utf-8")
    print(f"wrote {out}")


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
header{display:flex;justify-content:space-between;align-items:flex-end;flex-wrap:wrap;gap:14px;margin-bottom:22px}
h1{margin:0;font-size:30px;letter-spacing:-.5px}h1 small{display:block;font-size:14px;color:var(--muted);font-weight:500;letter-spacing:0}
h2{font-size:19px;margin:30px 0 12px}h3{font-size:14px;margin:20px 0 8px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em}
.stats{display:flex;gap:10px;flex-wrap:wrap}.stat{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:8px 14px;min-width:96px}
.stat b{font-size:22px;display:block;line-height:1.1}.stat span{font-size:12px;color:var(--muted)}.stat.warn b{color:var(--bad)}
ol.steps{list-style:none;padding:0;margin:0;display:grid;grid-template-columns:repeat(4,1fr);gap:10px}
.step{display:flex;gap:10px;align-items:flex-start;background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:12px}
.step .n{flex:none;width:28px;height:28px;border-radius:50%;display:grid;place-items:center;font-weight:700;background:var(--soft);color:var(--muted)}
.step small{display:block;color:var(--muted);font-size:12.5px}.step.now{border-color:var(--accent);box-shadow:0 0 0 2px color-mix(in srgb,var(--accent) 25%,transparent)}
.step.now .n{background:var(--accent);color:var(--panel)}.step.done .n{background:var(--ok);color:var(--panel)}.step.next{opacity:.72}
.gate{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:12px 16px;margin-top:10px}
.gate ul{margin:6px 0 0;padding:0;list-style:none}.gate li{padding:3px 0 3px 26px;position:relative}
.gate li:before{position:absolute;left:2px;top:3px;font-weight:700}.gate li.ok:before{content:"\\2713";color:var(--ok)}.gate li.todo:before{content:"\\25CB";color:var(--warm)}
.topics{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:10px}
.topic{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:12px 14px}
.topic p{margin:4px 0 8px;color:var(--muted);font-size:13px}.th{display:flex;justify-content:space-between;gap:8px;align-items:baseline}
.pill{font-size:11px;padding:2px 8px;border-radius:99px;background:var(--soft);color:var(--muted);white-space:nowrap}
.topic.covered .pill{background:color-mix(in srgb,var(--ok) 20%,transparent);color:var(--ok)}.topic.in-progress .pill{background:color-mix(in srgb,var(--warm) 22%,transparent);color:var(--warm)}
.bar{height:6px;background:var(--soft);border-radius:9px;overflow:hidden}.bar i{display:block;height:100%;background:var(--accent)}
.topic small{color:var(--muted);font-size:12px}.topic em{color:var(--bad);font-style:normal;font-weight:600}
.cols{display:grid;grid-template-columns:3fr 2fr;gap:24px}
details{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:8px 12px;margin:6px 0}
summary{cursor:pointer}details p{margin:8px 0 2px;color:var(--muted);font-size:13.5px}
code{font:600 12px ui-monospace,Consolas,monospace;color:var(--accent);margin-right:4px}.count{font-size:12px;background:var(--soft);border-radius:99px;padding:1px 8px;margin-left:4px;color:var(--ink)}
.tag{font-size:11px;border-radius:99px;padding:1px 8px;margin-left:6px;white-space:nowrap}.tag.blk{background:color-mix(in srgb,var(--bad) 18%,transparent);color:var(--bad)}
.tag.disc{background:color-mix(in srgb,var(--warm) 20%,transparent);color:var(--warm)}
details.d.proposed{border-style:dashed;border-color:var(--warm)}details.d small{color:var(--muted);white-space:nowrap}
footer{margin-top:40px;color:var(--muted);font-size:12px}
@media (max-width:820px){ol.steps{grid-template-columns:1fr 1fr}.cols{grid-template-columns:1fr}}
@media (max-width:480px){ol.steps{grid-template-columns:1fr}h1{font-size:25px}}
"""


def render_dashboard(p):
    qs, ds, feats, topics, gates = p.items("Q"), p.items("D"), p.items("F"), p.topics(), p.gates()
    phase = p.meta.get("phase", "frame")
    open_qs = [q for q in qs if q.get("Status") in ("open", "discussing")]
    blocking = [q for q in open_qs if q.get("Blocking") == "yes"]
    accepted = [d for d in ds if d.get("Status") == "accepted"]
    proposed = [d for d in ds if d.get("Status") == "proposed"]

    steps = []
    for i, ph in enumerate(PHASES):
        state = "done" if PHASES.index(phase) > i else ("now" if ph == phase else "next")
        checks = gate_checks(p, ph) if state != "next" else []
        detail = f"{sum(ok for ok, _ in checks)} of {len(checks)} exit checks met" if checks else GATE_RULES[ph]
        signed = " &middot; signed" if gates.get(ph, {}).get("status") == "passed" else ""
        steps.append(f'<li class="step {state}"><span class="n">{i + 1}</span><div><b>{PHASE_TITLES[ph]}</b>'
                     f'<small>{esc(detail)}{signed}</small></div></li>')
    gate_rows = "".join(f'<li class="{"ok" if ok else "todo"}">{esc(t)}</li>' for ok, t in gate_checks(p, phase))

    cards = []
    for t in topics:
        mine = [q for q in qs if q.get("Topic") == t["id"]]
        left = [q for q in mine if q.get("Status") in ("open", "discussing")]
        blk = sum(q.get("Blocking") == "yes" for q in left)
        done = len(mine) - len(left)
        pct = int(100 * done / len(mine)) if mine else (100 if t["status"] == "covered" else 0)
        cards.append(f'<div class="topic {t["status"].replace(" ", "-")}"><div class="th"><b>{esc(t["name"])}</b>'
                     f'<span class="pill">{esc(t["status"])}</span></div><p>{esc(t["scope"])}</p>'
                     f'<div class="bar"><i style="width:{pct}%"></i></div>'
                     f'<small>{done} of {len(mine)} decided{f" &middot; <em>{blk} blocking</em>" if blk else ""}</small></div>')

    def q_row(q):
        tags = '<span class="tag blk">blocking</span>' if q.get("Blocking") == "yes" else ""
        if q.get("Status") == "discussing":
            tags += '<span class="tag disc">has a proposal</span>'
        return (f'<details class="q"><summary><code>{q["id"]}</code>{esc(q["title"])}{tags}</summary>'
                f'<p>{esc(first_para(section(q["text"], "Context")))}</p></details>')

    groups = []
    for t in topics:
        mine = sorted((q for q in open_qs if q.get("Topic") == t["id"]), key=lambda q: (q.get("Blocking") != "yes", q["id"]))
        if mine:
            groups.append(f'<h3>{esc(t["name"])}<span class="count">{len(mine)}</span></h3>' + "".join(q_row(q) for q in mine))

    def d_row(d):
        ans = ", ".join(ids(d.get("Answers")))
        return (f'<details class="d {esc(d.get("Status"))}"><summary><code>{d["id"]}</code>{esc(d["title"])}'
                f'{f" <small>answers {esc(ans)}</small>" if ans else ""}</summary>'
                f'<p>{esc(first_para(section(d["text"], "Decision"), 420))}</p></details>')

    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(p.meta['name'])} ledger</title><style>{CSS}</style></head>
<body><main>
<header><h1>{esc(p.meta['name'])}<small>Product ledger &middot; generated {today()}</small></h1>
<div class="stats"><div class="stat"><b>{len(open_qs)}</b><span>open questions</span></div>
<div class="stat {'warn' if blocking else ''}"><b>{len(blocking)}</b><span>blocking</span></div>
<div class="stat"><b>{len(proposed)}</b><span>awaiting your yes</span></div>
<div class="stat"><b>{len(accepted)}</b><span>decided</span></div>
<div class="stat"><b>{len(feats)}</b><span>features</span></div></div></header>
<ol class="steps">{''.join(steps)}</ol>
<div class="gate"><b>To leave {PHASE_TITLES[phase]}</b><ul>{gate_rows or '<li class="todo">no checks defined</li>'}</ul></div>
<h2>Topics</h2><div class="topics">{''.join(cards)}</div>
<div class="cols"><section><h2>Open questions</h2>{''.join(groups) or '<p>None open.</p>'}</section>
<section><h2>Awaiting your decision</h2>{''.join(d_row(d) for d in proposed) or '<p>Nothing waiting.</p>'}
<h2>Decided</h2>{''.join(d_row(d) for d in reversed(accepted)) or '<p>Nothing yet.</p>'}</section></div>
<footer>Generated from the ledger files. Edit the files, not this page.</footer>
</main></body></html>"""


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
    sub.add_parser("status")
    sub.add_parser("check")
    s = sub.add_parser("gate")
    s.add_argument("phase", choices=PHASES)
    s = sub.add_parser("dashboard")
    s.add_argument("--out")
    args = ap.parse_args(argv)
    {"init": cmd_init, "add-question": cmd_add_question, "add-decision": cmd_add_decision, "accept": cmd_accept,
     "status": cmd_status, "check": cmd_check, "gate": cmd_gate, "dashboard": cmd_dashboard}[args.cmd](args)


if __name__ == "__main__":
    main()
