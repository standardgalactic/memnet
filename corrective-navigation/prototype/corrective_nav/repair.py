"""M6: repair, dependency traversal, scope and honest completeness.

Assumptions to confirm (see README, "Decisions to review"):
  * depends_on is directed: an edge A depends_on B makes A a dependent of B.
  * shares_obligation is symmetric.
  * A node's namespace is the part of its id before the first '/'; ids with no
    '/' are local. Remote namespaces model federated peers.
"""

import copy

from .graph import Graph
from .schema import SCHEMA

DEFAULT_DEPS = tuple(SCHEMA["default_dependency_types"])
_SYMMETRIC = set(SCHEMA["symmetric_dependency_types"])


def _namespace(node):
    return node.split("/", 1)[0] if "/" in node else ""


def _normalize_scope(scope, deps):
    scope = dict(scope or {})
    return {
        "max_depth": scope.get("max_depth"),
        "accessible": sorted(scope["accessible"]) if scope.get("accessible") is not None else None,
        "confirmed_peers": dict(sorted(scope.get("confirmed_peers", {}).items())),
        "deps": sorted(scope.get("deps", deps)),
    }


def _neighbors(graph, node, deps, established):
    """Candidate dependents of `node` over the dependency types `deps`."""
    out = set()
    op = "=" if established else "!="
    for rel in deps:
        rows = graph.query(
            f"SELECT subject, object FROM edges WHERE rel_type=? AND status {op} 'established' "
            "AND (subject=? OR object=?)", (rel, node, node))
        for subject, object_ in rows:
            if rel in _SYMMETRIC:
                out.add(object_ if subject == node else subject)
            elif object_ == node:  # subject depends on node
                out.add(subject)
    out.discard(node)
    return out


def traverse(graph, target, scope):
    """Breadth-first traversal of dependents. Returns (dependents, limits).

    `limits` lists every real reason the traversal may be incomplete:
      depth         dependents exist beyond max_depth
      inaccessible  dependents sit in a remote namespace that is neither accessible
                    nor confirmed by its peer
      unadjudicated provisional or unverified dependency edges touch visited nodes
      target_absent the target is not in the graph at this version
    """
    deps = scope["deps"]
    if target not in set(graph.node_ids()):
        return [], [{"kind": "target_absent", "nodes": [target]}]
    accessible, confirmed, max_depth = scope["accessible"], scope["confirmed_peers"], scope["max_depth"]
    visited, frontier, depth = {target}, [target], 0
    dependents, truncated, inaccessible, unadjudicated = [], set(), set(), set()
    while frontier:
        nxt = []
        for node in sorted(frontier):
            unadjudicated |= _neighbors(graph, node, deps, established=False)
            for cand in sorted(_neighbors(graph, node, deps, established=True)):
                if cand in visited:
                    continue
                if max_depth is not None and depth >= max_depth:
                    truncated.add(cand)
                    continue
                ns = _namespace(cand)
                if ns != "" and accessible is not None and ns not in accessible:
                    if ns in confirmed:  # the peer confirmed its own traversal
                        visited.add(cand)
                        dependents.append(cand)
                    else:
                        inaccessible.add(cand)
                    continue
                visited.add(cand)
                dependents.append(cand)
                nxt.append(cand)
        frontier, depth = nxt, depth + 1
    limits = []
    for kind, nodes in (("depth", truncated - visited), ("inaccessible", inaccessible - visited),
                        ("unadjudicated", unadjudicated - visited)):
        if nodes:
            limits.append({"kind": kind, "nodes": sorted(nodes)})
    return sorted(dependents), limits


def _completeness(limits):
    if any(l["kind"] == "target_absent" for l in limits):
        return "unknown"
    return "partial" if limits else "complete"


def lineage(ledger, repair_id):
    """The repair and its earlier repairs, following caused_by."""
    out, cur = [], repair_id
    while cur is not None:
        e = ledger.get(cur)
        if e["kind"] != "repair" or e["payload"].get("role") not in ("correction", "follow_up"):
            break
        out.append(cur)
        cur = e["caused_by"]
    return out


def _has_status_event(ledger, repair_ids, dependent):
    return any(e["kind"] == "repair" and e["payload"].get("role") == "dependent_status"
               and e["subject"] == dependent and e["caused_by"] in repair_ids
               for e in ledger.events())


def repair(ledger, target, defect, who, t, basis, replacement=None, scope=None,
           deps=DEFAULT_DEPS, supersede_target=False, role="correction", caused_by=None):
    """Record a correction and a status event for every dependent found.

    Returns (repair_event, [dependent_status_events]).
    """
    flags = ledger.flags
    scope = _normalize_scope(scope, deps)
    version = len(ledger)
    graph = Graph.from_ledger(ledger, version)
    try:
        dependents, limits = traverse(graph, target, scope)
    finally:
        graph.close()
    completeness = _completeness(limits)
    if not flags.honest_completeness:
        completeness = "complete"
    recorded = dependents if flags.repair_records_dependents else []
    supersedes = None
    if supersede_target:
        if not ledger.has(target):
            raise ValueError("supersede_target requires the target to be an event id")
        supersedes = target
    event = ledger.append({
        "t": t, "actor": who, "kind": "repair", "subject": target, "status": "established",
        "basis": list(basis), "caused_by": caused_by, "supersedes": supersedes,
        "payload": {"role": role, "defect": defect, "replacement": replacement, "scope": scope,
                    "graph_version": version, "completeness": completeness,
                    "dependents": recorded, "limits": limits},
    })
    lin = lineage(ledger, event["id"])
    statuses = []
    for d in recorded:
        if role == "follow_up" and _has_status_event(ledger, lin, d):
            continue
        statuses.append(ledger.append({
            "t": t, "actor": who, "kind": "repair", "subject": d, "status": "established",
            "basis": [{"event": event["id"]}], "caused_by": event["id"],
            "payload": {"role": "dependent_status", "review_status": "needs_review",
                        "repair": event["id"]},
        }))
    return event, statuses


def follow_up_repair(ledger, prior_repair_id, who, t, basis, scope=None):
    """Re-run the traversal on the current graph and record the extended dependent set.

    The prior repair record is not rewritten. The follow-up references it and
    only dependents without a status event yet receive a new one.
    """
    prior = ledger.get(prior_repair_id)
    if prior["kind"] != "repair" or prior["payload"].get("role") not in ("correction", "follow_up"):
        raise ValueError("a follow-up must reference a correction or follow_up repair")
    p = copy.deepcopy(prior["payload"])
    return repair(ledger, prior["subject"], p["defect"], who, t, basis,
                  replacement=p["replacement"], scope=scope or p["scope"],
                  role="follow_up", caused_by=prior_repair_id)
