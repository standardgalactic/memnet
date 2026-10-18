"""M5: the text navigator, the first client.

It shows one node at a time with the three relations in separate sections,
follows links, and explains any displayed relation. It keeps no history of its
own beyond the user's path, which lives in memory and is not written to the
ledger. Every change goes through a ledger event.
"""

import argparse
import datetime
import shlex
import sys

from .. import drafts as d
from .. import explain as ex
from .. import projection as pj
from .. import repair as rp
from ..graph import Graph
from ..ledger import Ledger, LedgerError
from ..schema import ValidationError
from ..status import door_state, promote, supported

SECTIONS = (("relevance", "Relevance"), ("support", "Support"), ("admissibility", "Admissibility"))

HELP = """Commands:
  show [NODE] [all]       show a node; 'all' includes provisional and unverified relations
  read NODE               the text recorded with the node's assertion
  follow N                move to the node at link N of the last display
  back                    return along your path
  path                    print your path
  explain REF             event chain behind link number REF or an event id prefix
  why NODE                why the node has its support status
  assert NODE             record a claim
  relate A TYPE B CHANNEL "evidence"
  unrelate REF "evidence"
  support NODE "evidence"
  defeat NODE "evidence" [target=REF]
  promote REF "evidence"  adjudicate a provisional or unverified event
  repair NODE "defect" "evidence" [depth=N] [local]
  suggest [NODE]          ask the retriever to nominate (provisional) relations
  moved V1 V2 [NODE]      why positions differ between ledger versions V1 and V2 (seed 0)
  help
"""


def _now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class TextNavigator:
    def __init__(self, ledger, who, clock=None, similarity=None, retriever=None):
        """`similarity(node)` returns neighbouring node ids by proximity alone.
        `retriever` is (actor, model_id, model_version) and is used only by `suggest`."""
        self.ledger = ledger
        self.who = who
        self.clock = clock or _now
        self.similarity = similarity
        self.retriever = retriever
        self.path = []
        self.links = []  # event ids of the last display, in order; not persisted
        self._link_nodes = {}

    # -- dispatch -----------------------------------------------------------
    def execute(self, line):
        try:
            parts = shlex.split(line)
        except ValueError as exc:
            return f"error: {exc}"
        if not parts:
            return ""
        handler = getattr(self, "cmd_" + parts[0], None)
        if handler is None:
            return f"error: unknown command {parts[0]!r}; try 'help'"
        try:
            return handler(*parts[1:])
        except (ValidationError, LedgerError, ValueError, KeyError, IndexError, TypeError) as exc:
            return f"error: {exc.args[0] if exc.args else exc}"

    def cmd_help(self):
        return HELP

    # -- reading ------------------------------------------------------------
    def _current(self):
        if not self.path:
            raise ValueError("no current node; use 'show NODE'")
        return self.path[-1]

    def cmd_show(self, *args):
        include_all = "all" in args
        names = [a for a in args if a != "all"]
        node = names[0] if names else self._current()
        graph = Graph.from_ledger(self.ledger)
        try:
            if node not in set(graph.node_ids()):
                raise ValueError(f"unknown node {node!r}")
            if not self.path or self.path[-1] != node:
                self.path.append(node)
            return self._render_node(graph, node, include_all)
        finally:
            graph.close()

    def _render_node(self, graph, node, include_all):
        statuses = None if include_all else ("established",)
        edges = [e for e in graph.edges(statuses=statuses) if node in (e["subject"], e["object"])]
        row = graph.query("SELECT asserted_event, status FROM nodes WHERE id=?", (node,))[0]
        lines = [f"Node: {node}"]
        lines.append(f"Assertion: {row[1]} (#{ex.short(row[0])})" if row[0] else "Assertion: none")
        lines.append(f"Support status: {supported(graph, node)}")
        door = door_state(graph, node)
        if door != "absent":
            lines.append(f"Door: {door}")
        self.links = []
        n = 0
        for channel, title in SECTIONS:
            lines.append("")
            lines.append(title)
            rows = [e for e in edges if e["channel"] == channel]
            if channel == "relevance" and not self.ledger.flags.enforce_proximity_not_authority \
                    and self.similarity:
                for other in self.similarity(node):  # ablated: proximity shown as if it were a relation
                    n += 1
                    self.links.append(None)
                    lines.append(f"  {n}. -> {'shares_concept':<18} {other}")
            if not rows and not (channel == "relevance" and self.links):
                lines.append("  none")
            for e in rows:
                n += 1
                out = e["subject"] == node
                other = e["object"] if out else e["subject"]
                marker = "" if e["status"] == "established" else f"  [{e['status']}]"
                self.links.append(e["event_id"])
                lines.append(f"  {n}. {'->' if out else '<-'} {e['rel_type']:<18} {other}  "
                             f"#{ex.short(e['event_id'])}{marker}")
        self._link_nodes = {}
        for i, eid in enumerate(self.links):
            if eid is not None:
                ev = self.ledger.get(eid)
                self._link_nodes[i + 1] = ev["object"] if ev["subject"] == node else ev["subject"]
        return "\n".join(lines)

    def cmd_read(self, node=None):
        from ..testbed import claim_texts
        node = node or self._current()
        texts = claim_texts(self.ledger)
        if node not in texts:
            raise ValueError(f"no recorded text for {node!r}")
        return f"Text of {node}:\n  {texts[node] or '(none)'}"

    def cmd_follow(self, number):
        node = self._link_nodes.get(int(number))
        if node is None:
            raise ValueError(f"no link {number} in the last display")
        return self.cmd_show(node)

    def cmd_back(self):
        if len(self.path) < 2:
            raise ValueError("nothing to go back to")
        self.path.pop()
        return self.cmd_show(self.path.pop())

    def cmd_path(self):
        return " > ".join(self.path) if self.path else "(empty)"

    def _ref(self, ref):
        if ref.isdigit():
            n = int(ref)
            if not 1 <= n <= len(self.links) or self.links[n - 1] is None:
                raise ValueError(f"no link {ref} in the last display")
            return self.links[n - 1]
        return self.ledger.resolve(ref)

    def cmd_explain(self, ref):
        eid = self._ref(ref)
        if self.ledger.get(eid)["kind"] == "relate":
            graph = Graph.from_ledger(self.ledger)
            try:
                expl = ex.explain_relation(self.ledger, graph, eid)
            finally:
                graph.close()
        else:
            expl = ex.explain_event(self.ledger, eid)
        return ex.render_chain(expl)

    def cmd_why(self, node):
        graph = Graph.from_ledger(self.ledger)
        try:
            if node not in set(graph.node_ids()):
                raise ValueError(f"unknown node {node!r}")
            return ex.render_support(ex.explain_support(self.ledger, graph, node))
        finally:
            graph.close()

    # -- writing: always through ledger events --------------------------------
    def _basis(self, evidence):
        return [d.evidence(evidence)]

    def _done(self, ev, what):
        return f"recorded {what} #{ex.short(ev['id'])} [{ev['status']}]"

    def cmd_assert(self, node):
        return self._done(self.ledger.append(d.assertion(node, self.who, self.clock())), "assertion")

    def cmd_relate(self, a, rel_type, b, channel, evidence):
        ev = self.ledger.append(d.relation(a, b, rel_type, channel, self.who, self.clock(),
                                           self._basis(evidence)))
        return self._done(ev, f"relation {a} {rel_type} {b}")

    def cmd_unrelate(self, ref, evidence):
        target = self.ledger.get(self._ref(ref))
        ev = self.ledger.append(d.unrelation(target, self.who, self.clock(), self._basis(evidence)))
        return self._done(ev, "withdrawal")

    def cmd_support(self, node, evidence):
        return self._done(self.ledger.append(d.support(node, self.who, self.clock(),
                                                       self._basis(evidence))), "support")

    def cmd_defeat(self, node, evidence, *opts):
        target = None
        for o in opts:
            if o.startswith("target="):
                target = self.ledger.resolve(o[len("target="):])
        return self._done(self.ledger.append(d.defeat(node, self.who, self.clock(),
                                                      self._basis(evidence), target_event=target)),
                          "defeat")

    def cmd_promote(self, ref, evidence):
        ev = promote(self.ledger, self._ref(ref), self.who, self.clock(), self._basis(evidence))
        return self._done(ev, "promotion")

    def cmd_repair(self, node, defect, evidence, *opts):
        scope = {}
        for o in opts:
            if o.startswith("depth="):
                scope["max_depth"] = int(o[len("depth="):])
            elif o == "local":
                scope["accessible"] = []
            else:
                raise ValueError(f"unknown option {o!r}")
        event, statuses = rp.repair(self.ledger, node, defect, self.who, self.clock(),
                                    self._basis(evidence), scope=scope or None)
        p = event["payload"]
        lines = [f"Repair #{ex.short(event['id'])} of {node}: {p['completeness']}",
                 f"  graph version {p['graph_version']}; {len(p['dependents'])} dependent(s) flagged needs_review"]
        lines += [f"    {x}" for x in p["dependents"]]
        for lim in p["limits"]:
            lines.append(f"  limit {lim['kind']}: {', '.join(lim['nodes'])}")
        return "\n".join(lines)

    def cmd_moved(self, v1, v2, node=None):
        a = pj.project(self.ledger, 0, version=int(v1))
        b = pj.project(self.ledger, 0, version=int(v2))
        attr = pj.attribute(a, b, self.ledger.flags)
        if node is None:
            return pj.render_attribution(attr)
        return ex.render_move(ex.explain_move(self.ledger, a, b, node, attr))

    def cmd_suggest(self, node=None):
        """Retrieval nominates: each suggestion is a provisional event by a retriever."""
        node = node or self._current()
        if self.similarity is None:
            raise ValueError("no similarity source is configured")
        neighbours = self.similarity(node)
        if not self.ledger.flags.enforce_proximity_not_authority:
            return "Similarity neighbours (not recorded): " + ", ".join(neighbours)
        if self.retriever is None:
            raise ValueError("no retriever is configured")
        who, model_id, version = self.retriever
        graph = Graph.from_ledger(self.ledger)
        try:
            known = {(e["subject"], e["object"]) for e in graph.edges(statuses=None)}
            nodes = set(graph.node_ids())
        finally:
            graph.close()
        made = []
        for other in neighbours:
            if other in nodes and other != node and (node, other) not in known \
                    and (other, node) not in known:
                ev = self.ledger.append(d.nomination(node, other, "shares_concept", "relevance",
                                                     who, model_id, version, self.clock()))
                made.append(f"  #{ex.short(ev['id'])} {node} shares_concept {other} [provisional]")
        if not made:
            return "No new nominations."
        return "Nominated (provisional, not shown until promoted unless you use 'show all'):\n" \
            + "\n".join(made)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Corrective Navigation text navigator")
    ap.add_argument("ledger")
    ap.add_argument("--actor", default="user")
    ap.add_argument("-c", action="append", default=[], help="run a command and exit (repeatable)")
    args = ap.parse_args(argv)
    nav = TextNavigator(Ledger(args.ledger), d.actor(args.actor))
    if args.c:
        for line in args.c:
            print(nav.execute(line))
        return 0
    print("Corrective Navigation. Type 'help'.")
    for line in sys.stdin:
        line = line.strip()
        if line in ("quit", "exit"):
            break
        out = nav.execute(line)
        if out:
            print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
