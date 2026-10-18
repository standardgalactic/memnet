"""The audit suite: one check per invariant that is testable at this stage.

Each function returns a list of violation strings; an empty list means the
invariant holds. The checks recompute from the ledger and do not trust what the
code that wrote the events claimed, so they can fail on an ablated variant.

Invariants 2 and 10 are covered for relations, as displayed by the text client,
and for position changes through the attribution diff. Invariant 4 is covered by
the projection audits.
"""

import re

from .graph import ALL, Graph, effective
from .repair import lineage, traverse
from .schema import FIELDS, SCHEMA


def audit_ledger_primacy(ledger, graph):
    """Invariant 1: the graph is the image of effective ledger events and holds nothing else."""
    out = []
    version = graph.version
    rebuilt = Graph.from_events(ledger.events(version), version)
    try:
        if rebuilt.fingerprint() != graph.fingerprint():
            out.append("graph differs from a rebuild from the ledger")
    finally:
        rebuilt.close()
    eff = {e["id"]: e for e in effective(ledger.events(version))}
    for row in graph.edges(statuses=ALL):
        e = eff.get(row["event_id"])
        if e is None or e["kind"] != "relate" or \
                (e["subject"], e["object"], e["rel_type"], e["channel"]) != \
                (row["subject"], row["object"], row["rel_type"], row["channel"]):
            out.append(f"edge {row['event_id']} has no matching effective relate event")
    return out


def audit_channel_separation(ledger):
    """Invariant 3: one channel per relation; a channel change needs a superseding event."""
    out = []
    by_triple = {}
    for e in effective(ledger.events()):
        if e["kind"] != "relate":
            continue
        if e["channel"] not in SCHEMA["channels"]:
            out.append(f"relation {e['id']} lacks a valid channel")
        by_triple.setdefault((e["subject"], e["object"], e["rel_type"]), set()).add(e["channel"])
    for triple, channels in by_triple.items():
        if len(channels) > 1:
            out.append(f"relation {triple} is effective in several channels {sorted(channels)} "
                       "without a promoting event")
    for e in ledger.events():
        if e["kind"] == "relate" and e["supersedes"] is not None:
            old = ledger.get(e["supersedes"])
            if old["kind"] == "relate" and old["channel"] != e["channel"] and not e["basis"]:
                out.append(f"channel change at {e['id']} has no basis")
    return out


def audit_retriever(ledger):
    """Invariant 5: retriever output is provisional and removing it changes no established view."""
    out = []
    events = ledger.events()
    retriever_ids = {e["id"] for e in events if e["actor"]["type"] == "retriever"}
    for e in events:
        if e["id"] in retriever_ids and e["status"] != "provisional":
            out.append(f"retriever event {e['id']} is {e['status']}, not provisional")
    full = Graph.from_events(events)
    without = Graph.from_events([e for e in events if e["id"] not in retriever_ids])
    try:
        if full.established_fingerprint() != without.established_fingerprint():
            out.append("removing the retriever changes the established view")
    finally:
        full.close()
        without.close()
    return out


def _correction_repairs(ledger):
    return [e for e in ledger.events()
            if e["kind"] == "repair" and e["payload"].get("role") in ("correction", "follow_up")]


def _recompute(ledger, repair_event):
    p = repair_event["payload"]
    graph = Graph.from_events(ledger.events(p["graph_version"]), p["graph_version"])
    try:
        return traverse(graph, repair_event["subject"], p["scope"])
    finally:
        graph.close()


def audit_repair_accountability(ledger):
    """Invariant 6: recorded dependents match the known dependents, and each has a status event."""
    out = []
    for r in _correction_repairs(ledger):
        p = r["payload"]
        dependents, _ = _recompute(ledger, r)
        if sorted(p["dependents"]) != dependents:
            out.append(f"repair {r['id']} records dependents {sorted(p['dependents'])} "
                       f"but the traversal at version {p['graph_version']} finds {dependents}")
        lin = set(lineage(ledger, r["id"]))
        for d in p["dependents"]:
            if not any(e["kind"] == "repair" and e["payload"].get("role") == "dependent_status"
                       and e["subject"] == d and e["caused_by"] in lin for e in ledger.events()):
                out.append(f"repair {r['id']}: dependent {d} has no logged status event")
    return out


def audit_honest_completeness(ledger):
    """Invariant 7: complete only when nothing limited the traversal."""
    out = []
    for r in _correction_repairs(ledger):
        _, limits = _recompute(ledger, r)
        if r["payload"]["completeness"] == "complete" and limits:
            kinds = sorted({l["kind"] for l in limits})
            out.append(f"repair {r['id']} is recorded complete but the traversal was limited by {kinds}")
    return out


def audit_provenance_split(ledger):
    """Invariant 8: git_ref is nullable, and the ledger holds no copied Git history."""
    out = []
    for e in ledger.events():
        extra = set(e) - set(FIELDS)
        if extra:
            out.append(f"event {e['id']} has fields outside the schema: {sorted(extra)}")
    return out


def audit_derived_admissibility(graph):
    """Invariant 9: the graph stores no admissibility or door state."""
    banned = ("door", "admissible", "open", "dimmed")
    out = []
    for table in ("nodes", "edges", "supports", "defeats", "admits", "dependent_status"):
        for col in graph.columns(table):
            if any(b in col.lower() for b in banned):
                out.append(f"{table}.{col} looks like stored admissibility or door state")
    return out


def audit_unverified_marking(ledger):
    """Invariant 11 (data half): events citing unchecked external material are marked unverified."""
    out = []
    for e in ledger.events():
        for b in e["basis"]:
            ext = b.get("external")
            if ext is not None and ext["verified"] is False and e["status"] != "unverified":
                out.append(f"event {e['id']} cites unchecked material but is {e['status']}")
    return out


_REL_LINE = re.compile(r"^\s+\d+\. (->|<-) ")
_FULL_LINE = re.compile(
    r"^\s+\d+\. (->|<-) (\S+)\s+(\S+)\s+#([0-9a-f]{8})(?:\s+\[(\w+)\])?$")
_SECTION_TITLES = {"Relevance": "relevance", "Support": "support", "Admissibility": "admissibility"}


def audit_displayed(ledger, text):
    """Invariants 2 and 3 against what a text display shows: every relation line cites an
    effective relate event, and its direction, type, channel section and status marker
    match that event."""
    out = []
    effective_ids = {e["id"]: e for e in effective(ledger.events())}
    node, section = None, None
    for line in text.splitlines():
        if line.startswith("Node: "):
            node = line[6:]
        elif line.strip() in _SECTION_TITLES and not line.startswith(" "):
            section = _SECTION_TITLES[line.strip()]
        elif line.startswith("Assertion: ") and node is not None:
            m = re.match(r"Assertion: (\w+) \(#([0-9a-f]{8})\)$", line)
            if m:
                hits = [e for i, e in effective_ids.items() if i.startswith(m.group(2))]
                if not hits or hits[0]["kind"] != "assert" or hits[0]["status"] != m.group(1):
                    out.append(f"assertion header for {node} does not match the ledger")
        elif _REL_LINE.match(line):
            m = _FULL_LINE.match(line)
            if not m:
                out.append(f"relation line without a backing event: {line.strip()!r}")
                continue
            arrow, rel_type, other, short_id, marker = m.groups()
            hits = [e for i, e in effective_ids.items() if i.startswith(short_id)]
            if len(hits) != 1 or hits[0]["kind"] != "relate":
                out.append(f"#{short_id} is not an effective relation event")
                continue
            e = hits[0]
            exp_subject, exp_object = (node, other) if arrow == "->" else (other, node)
            if (e["subject"], e["object"]) != (exp_subject, exp_object):
                out.append(f"#{short_id} shown with the wrong direction or endpoints")
            if e["rel_type"] != rel_type:
                out.append(f"#{short_id} shown as {rel_type}, is {e['rel_type']}")
            if e["channel"] != section:
                out.append(f"#{short_id} shown in {section}, belongs to {e['channel']}")
            if (marker or "established") != e["status"]:
                out.append(f"#{short_id} shown as {marker or 'established'}, is {e['status']}")
    return out


def audit_explanations(ledger, graph):
    """Invariant 10: every effective relation has an explanation, and the chain the resolver
    returns equals an independently computed closure, in ledger order, ending at the event."""
    from .explain import explain_relation
    out = []
    events = ledger.events()
    index = {e["id"]: e for e in events}
    for e in effective(events):
        if e["kind"] != "relate":
            continue
        expl = explain_relation(ledger, graph, e["id"])
        chain = [s["id"] for s in expl["chain"]]
        want, stack = set(), [e["id"]]
        while stack:
            cur = stack.pop()
            if cur in want:
                continue
            want.add(cur)
            ev = index[cur]
            stack += [b["event"] for b in ev["basis"] if "event" in b]
            stack += [ev[k] for k in ("caused_by", "supersedes") if ev[k] is not None]
        ordered = [x["id"] for x in events if x["id"] in want]
        if not expl["available"] or chain != ordered:
            out.append(f"explanation of {e['id']} does not match its event closure")
            continue
        if chain[-1] != e["id"] and e["id"] not in chain:
            out.append(f"explanation of {e['id']} omits the event itself")
        for step in expl["chain"]:
            if index[step["id"]]["actor"]["type"] == "retriever" and \
                    not any(n["type"] == "model" for n in step["notes"]):
                out.append(f"retriever step {step['id']} lacks its model note")
    return out


def audit_projection(ledger, seed=0):
    """Invariant 4 (reproducibility): the same version and key give the same file, the file
    recomputes from its own inputs, and its inputs match the ledger at its version."""
    from . import projection as pj
    out = []
    versions = sorted({len(ledger), max(1, len(ledger) // 2)})
    for v in versions:
        p1, p2 = pj.project(ledger, seed, version=v), pj.project(ledger, seed, version=v)
        if pj.digest(p1) != pj.digest(p2):
            out.append(f"two projections at version {v} with the same key differ")
        out += [f"version {v}: {m}" for m in pj.verify(p1, ledger)]
    return out


def audit_attribution(ledger, seed=0):
    """Invariant 4 (attribution): a change to exactly one factor is attributed to exactly that
    factor. The changes are made in memory on copies of the current projection."""
    from . import projection as pj
    out = []
    base = pj.project(ledger, seed)
    nodes = base["inputs"]["nodes"]
    if not nodes:
        return out
    flags = ledger.flags

    def check(name, variant, expected):
        attr = pj.attribute(base, variant, flags)
        if attr["changed"] != {f: f == expected for f in pj.FACTORS}:
            out.append(f"{name}: reported changed factors {attr['changed']}")
        for f in pj.FACTORS:
            if f != expected and attr["effects"][f]:
                out.append(f"{name}: movement attributed to {f}")
        if attr["unexplained"] or attr["interaction"]:
            out.append(f"{name}: movement left unexplained or interaction-only")

    other = pj.project(ledger, seed + 1)
    check("seed change", other, "algorithm")

    pin = {"event": "synthetic", "constraint": "pin", "subject": nodes[0],
           "position": [25.0, 25.0, 25.0]}
    inputs = dict(base["inputs"], constraints=base["inputs"]["constraints"] + [pin])
    check("added pin", pj.build(inputs, base["key"], flags), "constraints")

    have = {(e[0], e[1]) for e in base["inputs"]["edges"]} | {(e[1], e[0]) for e in base["inputs"]["edges"]}
    free = [(x, y) for i, x in enumerate(nodes) for y in nodes[i + 1:] if (x, y) not in have]
    if free:
        edge = [free[0][0], free[0][1], "shares_concept", "relevance"]
        inputs = dict(base["inputs"], edges=sorted(base["inputs"]["edges"] + [edge]))
        check("added edge", pj.build(inputs, base["key"], flags), "graph")
    return out


def audit_move_explanations(ledger, seed=0):
    """Invariants 2 and 10 for positions: every node that moved between an earlier ledger
    version and now has a stated cause, and every cited event lies between the two versions."""
    from . import projection as pj
    from .explain import explain_move
    out = []
    if len(ledger) < 2:
        return out
    a = pj.project(ledger, seed, version=max(1, len(ledger) // 2))
    b = pj.project(ledger, seed)
    attr = pj.attribute(a, b, ledger.flags)
    lo, hi = a["key"]["v"], b["key"]["v"]
    window = {e["id"] for e in ledger.events(hi)[lo:]}
    for node in sorted(attr["causes"]):
        ex = explain_move(ledger, a, b, node, attr)
        if not ex["causes"]:
            out.append(f"{node} moved with no stated cause")
        if ex["unexplained"]:
            out.append(f"{node} moved although no input changed")
        if ("graph" in ex["causes"] or "constraints" in ex["causes"]) and not ex["events"]:
            out.append(f"{node}: graph or constraint cause cites no ledger event")
        if any(ev["id"] not in window for ev in ex["events"]):
            out.append(f"{node}: cites an event outside the compared versions")
    return out


def audit_spatial(ledger, scene):
    """The spatial client audited against what it displays (plan, M7): the display list that
    the view code produces, with provisional relations hidden and shown, is checked against the
    ledger recomputed independently. Needs Node."""
    from . import projection as pj
    from .clients.spatial.runner import run_view
    from .clients.spatial.scene import node_explanation
    from .explain import explain_relation, render_chain
    from .status import door_state, supported
    out = []
    key = scene["key"]
    v = scene["ledger_version"]
    proj = pj.project(ledger, key["s"], key["theta"], v)
    positions = proj["positions"]
    events = ledger.events(v)
    graph = Graph.from_events(events, v)
    try:
        asserted = {r[0]: (r[1], r[2]) for r in graph.query("SELECT id, asserted_event, status FROM nodes")}
        want_nodes = {n: {"support": supported(graph, n), "door": door_state(graph, n),
                          "assertion": asserted[n][1] if asserted.get(n, (None,))[0] else "none"}
                      for n in positions}
        relates = {e["id"]: e for e in effective(events) if e["kind"] == "relate"
                   and e["subject"] in positions and e["object"] in positions}
        fresh = {f"node:{n}": node_explanation(ledger, graph, n, asserted.get(n, (None,))[0])
                 for n in positions}
        fresh.update({f"event:{i}": render_chain(explain_relation(ledger, graph, i)) for i in relates})
    finally:
        graph.close()

    for show in (False, True):
        tag = "provisional shown" if show else "provisional hidden"
        res = run_view(scene, show_provisional=show, inspect=sorted(fresh))
        items = res["items"]
        nodes = {i["id"]: i for i in items if i["kind"] == "node"}
        edges = [i for i in items if i["kind"] == "edge"]
        if set(nodes) != set(want_nodes):
            out.append(f"{tag}: displayed nodes differ from the projection")
        for n, w in want_nodes.items():
            it = nodes.get(n)
            if it is None:
                continue
            for field in ("support", "door", "assertion"):
                if it[field] != w[field]:
                    out.append(f"{tag}: {n} shows {field} {it[field]}, ledger derives {w[field]}")
            if (it["doorGlyph"] is None) != (w["door"] == "absent"):
                out.append(f"{tag}: {n} door glyph does not match door state {w['door']}")
        want_edges = {i for i, e in relates.items() if show or e["status"] == "established"}
        shown = [e["event"] for e in edges]
        if sorted(shown) != sorted(want_edges):
            out.append(f"{tag}: displayed relations differ from the effective relate events")
        for e in edges:
            r = relates.get(e["event"])
            if r is None:
                out.append(f"{tag}: a displayed line has no backing relation event")
                continue
            if (e["from"], e["to"], e["rel_type"], e["channel"], e["status"]) != \
                    (r["subject"], r["object"], r["rel_type"], r["channel"], r["status"]):
                out.append(f"{tag}: line for #{e['event'][:8]} does not match its event")
        # the three relations and the status of each must be visually distinct
        shapes, dashes = {}, {}
        for e in edges:
            shapes.setdefault(e["channel"], set()).add(e["shape"])
            dashes.setdefault(e["status"], set()).add(e["dash"])
        chans = sorted(shapes)
        for a in range(len(chans)):
            for b in range(a + 1, len(chans)):
                if shapes[chans[a]] & shapes[chans[b]]:
                    out.append(f"{tag}: {chans[a]} and {chans[b]} share a visual encoding")
        stats = sorted(dashes)
        for a in range(len(stats)):
            for b in range(a + 1, len(stats)):
                if dashes[stats[a]] & dashes[stats[b]]:
                    out.append(f"{tag}: {stats[a]} and {stats[b]} lines look the same")
        by_assertion = {}
        for i in nodes.values():
            by_assertion.setdefault(i["assertion"], set()).add(i["glyph"])
        kinds = sorted(by_assertion)
        for a in range(len(kinds)):
            for b in range(a + 1, len(kinds)):
                if by_assertion[kinds[a]] & by_assertion[kinds[b]]:
                    out.append(f"{tag}: {kinds[a]} and {kinds[b]} nodes look the same")
        for k, text in fresh.items():
            if res["inspections"].get(k) != text:
                out.append(f"{tag}: scanning {k} does not show the resolver's explanation")
        if not show and any(e["status"] != "established" for e in edges):
            out.append("provisional or unverified relations displayed by default")
    return out


def run_all(ledger, graph=None):
    """Run every audit available at this stage. Returns {invariant name: [violations]}."""
    own = graph is None
    graph = graph or Graph.from_ledger(ledger)
    try:
        return {
            "1 ledger primacy": audit_ledger_primacy(ledger, graph),
            "3 channel separation": audit_channel_separation(ledger),
            "5 retrieval nominates": audit_retriever(ledger),
            "6 repair accountability": audit_repair_accountability(ledger),
            "7 honest completeness": audit_honest_completeness(ledger),
            "8 provenance split": audit_provenance_split(ledger),
            "9 derived admissibility": audit_derived_admissibility(graph),
            "4 reproducible projection": audit_projection(ledger),
            "4 attribution": audit_attribution(ledger),
            "2, 10 position changes explained": audit_move_explanations(ledger),
            "10 explanation on demand": audit_explanations(ledger, graph),
            "11 unverified marking (data)": audit_unverified_marking(ledger),
        }
    finally:
        if own:
            graph.close()
