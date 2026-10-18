"""M6: repair, scope, completeness (invariants 6 and 7)."""

from corrective_nav import audit, drafts as d
from corrective_nav.graph import Graph
from corrective_nav.repair import follow_up_repair, repair
from tests.helpers import EV, HUMAN, RETRIEVER, LedgerCase

KNOWN = ["claim:c1", "claim:c2", "claim:c3", "peer1/z"]


class RepairTests(LedgerCase):
    def setUp(self):
        super().setUp()
        self.led = self.corpus(self.ledger())

    def fix(self, **kw):
        return repair(self.led, "claim:bad", "unsupported assertion", HUMAN, self.clock(), EV, **kw)

    def test_full_scope_is_complete_and_records_every_known_dependent(self):
        r, statuses = self.fix()
        p = r["payload"]
        self.assertEqual(p["dependents"], KNOWN)
        self.assertEqual(p["completeness"], "complete")
        self.assertEqual(p["graph_version"], 11)
        self.assertEqual(sorted(s["subject"] for s in statuses), KNOWN)
        self.assertTrue(all(s["caused_by"] == r["id"] for s in statuses))
        self.assertEqual(audit.run_all(self.led), {k: [] for k in audit.run_all(self.led)})

    def test_the_independent_claim_is_not_a_dependent(self):
        r, _ = self.fix()
        self.assertNotIn("claim:indep", r["payload"]["dependents"])

    def test_out_of_scope_dependent_makes_the_repair_partial_with_a_reason(self):
        r, _ = self.fix(scope={"accessible": []})
        p = r["payload"]
        self.assertEqual(p["completeness"], "partial")
        self.assertEqual(p["dependents"], ["claim:c1", "claim:c2", "claim:c3"])
        self.assertEqual(p["limits"], [{"kind": "inaccessible", "nodes": ["peer1/z"]}])
        self.assertEqual(audit.audit_honest_completeness(self.led), [])

    def test_a_peer_that_confirms_its_traversal_lets_the_repair_be_complete(self):
        r, _ = self.fix(scope={"accessible": [], "confirmed_peers": {"peer1": 7}})
        self.assertEqual(r["payload"]["completeness"], "complete")
        self.assertIn("peer1/z", r["payload"]["dependents"])

    def test_depth_limit_is_partial(self):
        r, _ = self.fix(scope={"max_depth": 1})
        p = r["payload"]
        self.assertEqual(p["dependents"], ["claim:c1"])
        self.assertEqual(p["completeness"], "partial")
        self.assertEqual(p["limits"], [{"kind": "depth", "nodes": ["claim:c2"]}])

    def test_unadjudicated_dependency_edges_prevent_a_complete_claim(self):
        self.led.append(d.nomination("claim:indep", "claim:c2", "depends_on", "support",
                                     RETRIEVER, "emb", "1.0", self.clock()))
        r, _ = self.fix()
        self.assertEqual(r["payload"]["completeness"], "partial")
        self.assertEqual(r["payload"]["limits"][0]["kind"], "unadjudicated")
        self.assertNotIn("claim:indep", r["payload"]["dependents"])  # nominated, not established

    def test_unknown_target_is_unknown(self):
        r, statuses = repair(self.led, "claim:nowhere", "defect", HUMAN, self.clock(), EV)
        self.assertEqual(r["payload"]["completeness"], "unknown")
        self.assertEqual(statuses, [])

    def test_dependent_status_events_show_in_the_graph_as_logged_consequences(self):
        r, _ = self.fix()
        g = Graph.from_ledger(self.led)
        rows = g.query("SELECT subject, review_status, repair_id FROM dependent_status ORDER BY subject")
        self.assertEqual([x[0] for x in rows], sorted(KNOWN))
        self.assertTrue(all(x[1] == "needs_review" and x[2] == r["id"] for x in rows))

    def test_follow_up_extends_without_rewriting_the_original(self):
        first, _ = self.fix(scope={"accessible": []})
        before = self.led.events()
        self.led.append(d.assertion("claim:c4", HUMAN, self.clock()))
        self.led.append(d.relation("claim:c4", "claim:c3", "depends_on", "support",
                                   HUMAN, self.clock(), EV))
        later, statuses = follow_up_repair(self.led, first["id"], HUMAN, self.clock(), EV)
        self.assertEqual(later["caused_by"], first["id"])
        self.assertEqual(self.led.events()[:len(before)], before)          # original untouched
        self.assertEqual(later["payload"]["dependents"],
                         ["claim:c1", "claim:c2", "claim:c3", "claim:c4"])
        self.assertEqual([s["subject"] for s in statuses], ["claim:c4"])  # only the new one
        self.assertEqual(audit.audit_repair_accountability(self.led), [])

    def test_a_repair_can_supersede_a_defective_event(self):
        bad = [e for e in self.led.events() if e["subject"] == "claim:bad" and e["kind"] == "assert"][0]
        r, _ = repair(self.led, bad["id"], "defect", HUMAN, self.clock(), EV, supersede_target=True)
        self.assertEqual(r["supersedes"], bad["id"])
        self.assertTrue(self.led.has(bad["id"]))
