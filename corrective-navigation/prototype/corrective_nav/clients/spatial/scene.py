"""M7: the scene the spatial client reads.

The scene is plain data built from the ledger and a projection: positions, the
separate encodings of the three relations, derived support and door state, and
the explanation text for every node and relation, produced by the same resolver
the text client uses. The browser page only draws the scene and displays that
text; it computes nothing about the graph.
"""

import json

from ... import explain as ex
from ... import projection as pj
from ...graph import Graph, effective
from ...status import door_state, supported


def node_explanation(ledger, graph, node, assertion_event):
    lines = [f"Node: {node}"]
    if assertion_event:
        lines.append(ex.render_chain(ex.explain_event(ledger, assertion_event)))
    lines.append(ex.render_support(ex.explain_support(ledger, graph, node)))
    return "\n".join(lines)


def build_scene(ledger, seed=0, theta=None, version=None, L=False, since=None):
    """`L` includes repair review status (the pilot's ledger switch). `since` is an earlier
    ledger version; if given, each node that moved since then carries its movement explanation."""
    proj = pj.project(ledger, seed, theta, version)
    v = proj["key"]["v"]
    events = ledger.events(v)
    graph = Graph.from_events(events, v)
    try:
        asserted = {r[0]: (r[1], r[2]) for r in graph.query("SELECT id, asserted_event, status FROM nodes")}
        review = {}
        if L:
            for node, status, rep in graph.query(
                    "SELECT subject, review_status, repair_id FROM dependent_status "
                    "WHERE status='established' ORDER BY event_id"):
                review.setdefault(node, []).append(status)
        flags = ledger.flags
        nodes = []
        explanations = {}
        for n, pos in sorted(proj["positions"].items()):
            ev, status = asserted.get(n, (None, None))
            nodes.append({"id": n, "pos": pos, "assertion": status if ev else "none",
                          "support": supported(graph, n), "door": door_state(graph, n),
                          "review": review.get(n, [])})
            explanations[f"node:{n}"] = node_explanation(ledger, graph, n, ev)
        edges = []
        for e in graph.edges(statuses=None):
            if e["subject"] in proj["positions"] and e["object"] in proj["positions"]:
                edges.append({"event": e["event_id"], "from": e["subject"], "to": e["object"],
                              "rel_type": e["rel_type"], "channel": e["channel"], "status": e["status"]})
                explanations[f"event:{e['event_id']}"] = ex.render_chain(
                    ex.explain_relation(ledger, graph, e["event_id"]))
    finally:
        graph.close()
    scene = {
        "format": "corrective-navigation-scene/1",
        "key": proj["key"], "projection": pj.digest(proj), "ledger_version": v,
        "arm": {"L": L}, "nodes": nodes, "edges": sorted(edges, key=lambda e: e["event"]),
        "explanations": explanations,
        "options": {"merge_channels": not flags.display_channel_separation,
                    "mark_status": flags.display_status_markers,
                    "explain_on_scan": flags.display_explanations},
        "movement": {},
    }
    if since is not None:
        old = pj.project(ledger, seed, theta, since)
        attr = pj.attribute(old, proj, flags)
        for n in attr["causes"]:
            if n in proj["positions"]:
                scene["movement"][n] = ex.render_move(ex.explain_move(ledger, old, proj, n, attr))
    return scene


def to_json(scene):
    return json.dumps(scene, sort_keys=True, separators=(",", ":"))
