"""M5: the explanation resolver used by every client.

For any event, the resolver returns the chain of events that stands behind it:
the event itself, every event cited in its basis, its cause, and what it
superseded, followed transitively, in ledger order. Evidence, retriever model
stamps and external citations are surfaced with the event that carries them.

Explaining a change of position between two projections arrives with M4; it
will extend this module with the attribution diff.
"""

from .status import supported


def short(event_id):
    return event_id[:8]


def _closure(ledger, event_id):
    seen, links, stack = set(), {}, [event_id]
    while stack:
        cur = stack.pop()
        if cur in seen:
            continue
        seen.add(cur)
        e = ledger.get(cur)
        refs = [("basis", b["event"]) for b in e["basis"] if "event" in b]
        refs += [(via, e[via]) for via in ("caused_by", "supersedes") if e[via] is not None]
        for via, ref in refs:
            links.setdefault(ref, []).append({"from": cur, "via": via})
            stack.append(ref)
    return seen, links


def _notes(event):
    notes = []
    for b in event["basis"]:
        if "evidence" in b:
            notes.append({"type": "evidence", "value": b["evidence"]})
        elif "model" in b:
            notes.append({"type": "model", "value": dict(b["model"])})
        elif "external" in b:
            notes.append({"type": "external", "value": dict(b["external"])})
    return notes


def explain_event(ledger, event_id):
    """The event chain behind an event. `available` is False only in the ablated variant."""
    if not ledger.flags.explanation_available:
        return {"event": event_id, "available": False, "chain": []}
    seen, links = _closure(ledger, event_id)
    chain = []
    for e in ledger.events():
        if e["id"] in seen:
            chain.append({
                "id": e["id"], "kind": e["kind"], "subject": e["subject"], "object": e["object"],
                "rel_type": e["rel_type"], "channel": e["channel"], "actor": dict(e["actor"]),
                "status": e["status"], "t": e["t"], "role": e["payload"].get("role"),
                "links": links.get(e["id"], []), "notes": _notes(e),
            })
    return {"event": event_id, "available": True, "chain": chain}


def explain_relation(ledger, graph, event_id):
    """Explanation of a displayed relation: its event chain, plus whether the graph holds it."""
    e = ledger.get(event_id)
    if e["kind"] != "relate":
        raise ValueError("not a relation event")
    out = explain_event(ledger, event_id)
    out["relation"] = {k: e[k] for k in ("subject", "object", "rel_type", "channel", "status")}
    out["in_graph"] = any(r["event_id"] == event_id for r in graph.edges(statuses=None))
    return out


def explain_support(ledger, graph, claim):
    """Why a claim has its support status: every support and defeat event on it."""
    rows = graph.query(
        "SELECT event_id, 'support', status, NULL FROM supports WHERE subject=? "
        "UNION ALL SELECT event_id, 'defeat', status, target_event FROM defeats WHERE subject=? "
        "ORDER BY 1", (claim, claim))
    return {
        "claim": claim,
        "status": supported(graph, claim),
        "contributions": [
            {"event": eid, "kind": kind, "status": status, "target_event": target,
             "notes": _notes(ledger.get(eid))}
            for eid, kind, status, target in rows
        ],
    }


# -- text rendering ----------------------------------------------------------

def _describe(step):
    k = step["kind"]
    if k == "relate":
        return f"relate {step['subject']} {step['rel_type']} {step['object']} [{step['channel']}]"
    if k == "repair":
        return f"repair {step['subject']} ({step['role']})"
    return f"{k} {step['subject']}"


def _render_note(note):
    v = note["value"]
    if note["type"] == "evidence":
        return f"evidence: {v}"
    if note["type"] == "model":
        return f"retriever model: {v['id']} {v['version']}"
    checked = "verified" if v["verified"] else "UNVERIFIED"
    return f"external: {v['citation']} ({checked})"


def render_chain(expl):
    target = short(expl["event"])
    if not expl["available"]:
        return f"Explanation for #{target}\n  unavailable: no event chain is returned"
    lines = [f"Explanation for #{target}"]
    if "relation" in expl:
        r = expl["relation"]
        lines.append(f"  relation: {r['subject']} {r['rel_type']} {r['object']} "
                     f"[{r['channel']}], {r['status']}")
    for i, step in enumerate(expl["chain"], start=1):
        a = step["actor"]
        lines.append(f"  {i}. #{short(step['id'])} {_describe(step)} by {a['id']} ({a['type']}), "
                     f"{step['t']}, {step['status']}")
        for note in step["notes"]:
            lines.append(f"       {_render_note(note)}")
        for link in step["links"]:
            lines.append(f"       reached as {link['via']} of #{short(link['from'])}")
    return "\n".join(lines)


def render_support(expl):
    lines = [f"Support status of {expl['claim']}: {expl['status']}"]
    if not expl["contributions"]:
        lines.append("  no support or defeat events")
    for i, c in enumerate(expl["contributions"], start=1):
        extra = f", targets #{short(c['target_event'])}" if c["target_event"] else ""
        lines.append(f"  {i}. #{short(c['event'])} {c['kind']} [{c['status']}]{extra}")
        for note in c["notes"]:
            lines.append(f"       {_render_note(note)}")
    lines.append("Only established events count. Use 'explain REF' for the full chain behind one.")
    return "\n".join(lines)


# -- why a position changed (M4) -----------------------------------------------

_LAYOUT_KINDS = ("assert", "relate", "unrelate", "constrain")


def explain_move(ledger, a, b, node, attr=None):
    """The reasons a node's position differs between projections a and b, with the ledger
    events behind each reason. Graph and constraint causes cite the events added between
    the two ledger versions; `direct` marks those that mention the node itself."""
    from .projection import attribute
    attr = attr or attribute(a, b, ledger.flags)
    causes = attr["causes"].get(node, [])
    lo, hi = sorted((a["key"]["v"], b["key"]["v"]))
    window = ledger.events(hi)[lo:]
    events = []
    for e in window:
        if e["kind"] not in _LAYOUT_KINDS:
            continue
        members = e["payload"].get("members", []) if e["kind"] == "constrain" else []
        direct = node in (e["subject"], e["object"]) or node in members
        if ("graph" in causes and e["kind"] != "constrain") or \
                ("constraints" in causes and e["kind"] == "constrain"):
            events.append({"id": e["id"], "kind": e["kind"], "direct": direct})
    ka, kb = a["key"], b["key"]
    algorithm = {f: [ka[f], kb[f]] for f in ("a", "theta", "s") if ka[f] != kb[f]} \
        if "algorithm" in causes else {}
    return {"node": node, "causes": causes, "events": events, "algorithm": algorithm,
            "interaction": "interaction" in causes, "unexplained": "unexplained" in causes}


def render_move(expl):
    if not expl["causes"]:
        return f"{expl['node']} did not move between the two projections."
    lines = [f"{expl['node']} moved because of: {', '.join(expl['causes'])}"]
    if expl["unexplained"]:
        lines.append("  no input changed, so this movement is a violation of reproducibility")
    ordered = sorted(expl["events"], key=lambda e: not e["direct"])
    for ev in ordered[:8]:
        lines.append(f"  #{short(ev['id'])} {ev['kind']}" + (" (mentions this node)" if ev["direct"] else ""))
    if len(ordered) > 8:
        lines.append(f"  and {len(ordered) - 8} more events between the two versions")
    for field, (old, new) in expl["algorithm"].items():
        lines.append(f"  algorithm {field}: {old} -> {new}")
    return "\n".join(lines)
