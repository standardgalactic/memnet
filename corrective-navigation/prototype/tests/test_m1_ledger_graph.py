"""M1: ledger, effective set, derived graph (invariant 1: ledger primacy)."""

import os

from corrective_nav import audit, drafts as d
from corrective_nav.graph import ALL, Graph
from corrective_nav.ledger import Ledger, LedgerError
from tests.helpers import EV, HUMAN, LedgerCase


class LedgerTests(LedgerCase):
    def test_reload_reproduces_the_ledger_exactly(self):
        led = self.corpus(self.ledger())
        again = Ledger(led.path)
        self.assertEqual(led.events(), again.events())

    def test_tampering_is_detected_on_load(self):
        led = self.corpus(self.ledger())
        lines = led.path.read_text(encoding="utf-8").splitlines()
        self.assertIn("claim:c1", lines[1])
        lines[1] = lines[1].replace("claim:c1", "claim:cX")
        led.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        with self.assertRaises(LedgerError):
            Ledger(led.path)

    def test_duplicate_and_dangling_references_are_rejected(self):
        led = self.ledger()
        draft = d.assertion("a", HUMAN, self.clock())
        led.append(draft)
        with self.assertRaises(LedgerError):
            led.append(draft)
        with self.assertRaises(LedgerError):
            led.append(d.support("a", HUMAN, self.clock(), [d.event_ref("f" * 64)]))

    def test_an_event_cannot_be_superseded_twice(self):
        led = self.ledger()
        r = led.append(d.relation("a", "b", "cites", "relevance", HUMAN, self.clock(), EV))
        led.append(d.unrelation(r, HUMAN, self.clock(), EV))
        with self.assertRaises(LedgerError):
            led.append(d.relation("a", "b", "cites", "relevance", HUMAN, self.clock(), EV,
                                  supersedes=r["id"]))

    def test_versions_are_prefixes(self):
        led = self.corpus(self.ledger())
        self.assertEqual(led.events(3), led.events()[:3])
        with self.assertRaises(LedgerError):
            led.events(len(led) + 1)


class GraphTests(LedgerCase):
    def test_unrelate_removes_the_edge_but_the_ledger_keeps_the_history(self):
        led = self.ledger()
        r = led.append(d.relation("a", "b", "cites", "relevance", HUMAN, self.clock(), EV))
        g = Graph.from_ledger(led)
        self.assertEqual(len(g.edges()), 1)
        led.append(d.unrelation(r, HUMAN, self.clock(), EV))
        g2 = Graph.from_ledger(led)
        self.assertEqual(g2.edges(statuses=ALL), [])
        self.assertEqual(len(led), 2)

    def test_rebuild_after_deleting_the_index_is_identical(self):
        led = self.corpus(self.ledger())
        path = str(self.dir / "graph.sqlite")
        first = Graph.from_ledger(led, path=path)
        fingerprint = first.fingerprint()
        first.close()
        os.remove(path)
        second = Graph.from_ledger(led, path=path)
        self.assertEqual(second.fingerprint(), fingerprint)

    def test_graph_at_an_earlier_version_matches_the_prefix(self):
        led = self.corpus(self.ledger())
        early = Graph.from_ledger(led, version=8)
        self.assertEqual(early.version, 8)
        self.assertNotIn("claim:indep", [e["subject"] for e in early.edges()])

    def test_primacy_audit_passes_on_a_faithful_graph(self):
        led = self.corpus(self.ledger())
        self.assertEqual(audit.audit_ledger_primacy(led, Graph.from_ledger(led)), [])

    def test_primacy_audit_catches_a_fact_the_ledger_does_not_hold(self):
        led = self.corpus(self.ledger())
        g = Graph.from_ledger(led)
        g.conn.execute("INSERT INTO edges VALUES('forged','claim:c1','claim:c3','depends_on',"
                       "'support','established','nate','human')")
        problems = audit.audit_ledger_primacy(led, g)
        self.assertTrue(problems)
        self.assertTrue(any("forged" in p for p in problems))

    def test_provenance_split_semantic_events_need_no_commit(self):
        led = self.corpus(self.ledger())
        self.assertTrue(all(e["git_ref"] is None for e in led.events()))
        self.assertEqual(audit.audit_provenance_split(led), [])
