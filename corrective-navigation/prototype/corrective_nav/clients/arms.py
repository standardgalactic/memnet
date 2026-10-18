"""The four arms of the pilot as switches over one shared event store.

Every arm reads and writes the same ledger through the same text client. The
ledger switch L controls only whether repair provenance, repair entries and
completeness status are available. The geometry switch G controls only whether
the projection is available as proximity and movement. Everything else (channel
separation, explanation of relations, derived admissibility, the retriever
being absent) is held fixed, as the pilot design requires.
"""

from dataclasses import dataclass

from .. import explain as ex
from .. import projection as pj
from ..status import supported
from .text import TextNavigator

ARMS = {
    "typed": (False, False),
    "ledger": (True, False),
    "geometry": (False, True),
    "full": (True, True),
}
L_ONLY = ("repairs", "status")
G_ONLY = ("near", "moved")
NEVER = ("suggest", "repair", "promote")  # not part of any arm: participants read, they do not adjudicate


@dataclass(frozen=True)
class Arm:
    name: str
    L: bool
    G: bool


def arm(name):
    L, G = ARMS[name]
    return Arm(name, L, G)


class ArmNavigator(TextNavigator):
    def __init__(self, ledger, who, arm_, clock=None, seed=0):
        super().__init__(ledger, who, clock=clock)
        self.arm = arm_
        self.seed = seed

    def execute(self, line):
        parts = line.split()
        if parts:
            c = parts[0]
            if c in NEVER or (c in L_ONLY and not self.arm.L) or (c in G_ONLY and not self.arm.G):
                return f"error: command {c!r} is not available in this interface"
        return super().execute(line)

    # -- L: repair provenance --------------------------------------------------
    def _status_events(self, graph, node):
        return graph.query(
            "SELECT event_id, review_status, repair_id FROM dependent_status WHERE subject=? "
            "AND status='established' ORDER BY event_id", (node,))

    def cmd_show(self, *args):
        out = super().cmd_show(*args)
        if not self.arm.L:
            return out
        from ..graph import Graph
        node = self.path[-1]
        graph = Graph.from_ledger(self.ledger)
        try:
            rows = self._status_events(graph, node)
        finally:
            graph.close()
        if not rows:
            return out
        line = "Review: " + ", ".join(f"{r[1]} (repair #{ex.short(r[2])})" for r in rows)
        lines = out.split("\n")
        i = next(k for k, l in enumerate(lines) if l.startswith("Support status:"))
        lines.insert(i + 1, line)
        return "\n".join(lines)

    def cmd_explain(self, ref):
        if not self.arm.L and self.ledger.get(self._ref(ref))["kind"] != "relate":
            raise ValueError("only relations can be explained in this interface")
        return super().cmd_explain(ref)

    def cmd_repairs(self):
        reps = [e for e in self.ledger.events() if e["kind"] == "repair"
                and e["payload"].get("role") in ("correction", "follow_up")]
        if not reps:
            return "No repairs recorded."
        lines = []
        for e in reps:
            p = e["payload"]
            lines.append(f"Repair #{ex.short(e['id'])} of {e['subject']}: {p['completeness']} "
                         f"(graph version {p['graph_version']}, by {e['actor']['id']})")
            lines.append(f"  defect: {p['defect']}")
            lines.append(f"  flagged for review: {', '.join(p['dependents']) or 'none'}")
            for lim in p["limits"]:
                lines.append(f"  limit {lim['kind']}: {', '.join(lim['nodes'])}")
        return "\n".join(lines)

    def cmd_status(self, node):
        from ..graph import Graph
        graph = Graph.from_ledger(self.ledger)
        try:
            rows = self._status_events(graph, node)
        finally:
            graph.close()
        if not rows:
            return f"{node}: no review status recorded"
        return "\n".join(f"{node}: {r[1]} (repair #{ex.short(r[2])})" for r in rows)

    # -- G: proximity ----------------------------------------------------------
    def cmd_near(self, node=None, n="6"):
        node = node or self._current()
        proj = pj.project(self.ledger, self.seed)
        pos = proj["positions"]
        if node not in pos:
            raise ValueError(f"{node!r} is not in the projection")
        import math
        dist = sorted((math.dist(pos[node], v), m) for m, v in pos.items() if m != node)
        lines = [f"Proximity to {node} (layout distance; not a relation, key {pj.key_id(proj['key'])})"]
        lines += [f"  {m}  {d:.2f}" for d, m in dist[:int(n)]]
        return "\n".join(lines)
