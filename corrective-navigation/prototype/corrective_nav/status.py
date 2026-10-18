"""M2 and M3: status values, adjudication, support, relevance, admissibility.

Support status, relevance and admissibility are three separate functions of the
graph. None implies another, and none is ever stored.

The policy for moving an event from provisional to established is an open
decision in the specification; `promote` is the simplest declared policy: a
non-retriever actor supersedes the provisional event with an established copy
and cites it.
"""

import copy
import json

from .graph import ALL  # noqa: F401  (re-exported for callers)
from .drafts import event_ref

ESTABLISHED = ("established",)


def promote(ledger, event_id, who, t, basis):
    """Adjudicate: supersede a provisional event with an established copy.

    The promoting actor must not be a retriever (the schema rejects that), and
    the new event cites the one it replaces. The provisional event stays in the
    ledger, so the history of the promotion is preserved.
    """
    old = ledger.get(event_id)
    if old["status"] == "established":
        raise ValueError("event is already established")
    draft = {k: copy.deepcopy(old[k]) for k in old if k != "id"}
    draft.update({
        "t": t,
        "actor": who,
        "status": "established",
        "supersedes": event_id,
        "caused_by": None,
        "basis": [event_ref(event_id)] + list(basis),
    })
    return ledger.append(draft)


def _status_filter(statuses):
    """SQL fragment and parameters restricting rows to the given statuses (None = all)."""
    if statuses is None:
        return "", ()
    return " AND status IN (%s)" % ",".join("?" * len(statuses)), tuple(statuses)


def supported(graph, claim, statuses=ESTABLISHED):
    """Discrete support status of a claim: unassessed | supported | contested | defeated."""
    clause, params = _status_filter(statuses)
    supports = {r[0] for r in graph.query(
        f"SELECT event_id FROM supports WHERE subject=?{clause}", (claim, *params))}
    defeats = graph.query(
        f"SELECT target_event FROM defeats WHERE subject=?{clause}", (claim, *params))
    defeated_supports = {t for (t,) in defeats if t is not None} & supports
    claim_defeats = [t for (t,) in defeats if t is None]
    live = supports - defeated_supports
    if live and claim_defeats:
        return "contested"
    if live:
        return "supported"
    if claim_defeats or defeated_supports:
        return "defeated"
    return "unassessed"


def relevant(graph, x, u, hops=1):
    """Relevant(x, u): x bears on context u through established relevance-channel edges."""
    adjacency = {}
    for e in graph.edges(channel="relevance"):
        adjacency.setdefault(e["subject"], set()).add(e["object"])
        adjacency.setdefault(e["object"], set()).add(e["subject"])
    seen, frontier = {u}, {u}
    reached = set()
    for _ in range(hops):
        frontier = {n for f in frontier for n in adjacency.get(f, ())} - seen
        seen |= frontier
        reached |= frontier
    return x in reached


def _governing_admits(graph, c, statuses=ESTABLISHED):
    clause, params = _status_filter(statuses)
    return graph.query(
        f"SELECT event_id, requires FROM admits WHERE subject=?{clause} ORDER BY event_id",
        (c, *params))


def admissible(graph, c):
    """Admissible(c | G_v): c has governing admit events and every requirement is supported."""
    admits = _governing_admits(graph, c)
    if not admits:
        return False
    requires = set()
    for _, req in admits:
        requires |= set(json.loads(req))
    return all(supported(graph, r) == "supported" for r in requires)


def door_state(graph, c):
    """Computed, never stored: 'absent' (no admit events), 'dimmed', or 'open'."""
    if not _governing_admits(graph, c):
        return "absent"
    return "open" if admissible(graph, c) else "dimmed"
