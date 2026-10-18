"""M2 and M3: provisional handling, retriever, support, relevance, admissibility
(invariants 3, 5, 9, 11)."""

from corrective_nav import audit, drafts as d
from corrective_nav.graph import ALL, Graph
from corrective_nav.ledger import LedgerError
from corrective_nav.status import admissible, door_state, promote, relevant, supported
from tests.helpers import EV, HUMAN, RETRIEVER, LedgerCase


class RetrieverTests(LedgerCase):
    def nominate(self, led):
        return led.append(d.nomination("claim:indep", "claim:c3", "shares_concept", "relevance",
                                       RETRIEVER, "emb", "1.0", self.clock()))

    def test_provisional_events_are_excluded_from_the_established_view_by_default(self):
        led = self.corpus(self.ledger())
        self.nominate(led)
        g = Graph.from_ledger(led)
        self.assertEqual(len(g.edges(rel_type="shares_concept")), 1)           # only the human one
        self.assertEqual(len(g.edges(rel_type="shares_concept", statuses=ALL)), 2)

    def test_removing_the_retriever_changes_no_established_relation(self):
        led = self.corpus(self.ledger())
        self.nominate(led)
        self.assertEqual(audit.audit_retriever(led), [])

    def test_promotion_is_an_explicit_adjudication_event(self):
        led = self.corpus(self.ledger())
        nom = self.nominate(led)
        promoted = promote(led, nom["id"], HUMAN, self.clock(), EV)
        g = Graph.from_ledger(led)
        edges = g.edges(rel_type="shares_concept")
        self.assertIn(promoted["id"], [e["event_id"] for e in edges])
        self.assertNotIn(nom["id"], [e["event_id"] for e in g.edges(statuses=ALL)])  # superseded
        self.assertEqual(led.get(nom["id"])["status"], "provisional")              # history kept
        self.assertEqual(audit.audit_retriever(led), [])

    def test_retriever_cannot_promote_its_own_nomination(self):
        led = self.corpus(self.ledger())
        nom = self.nominate(led)
        with self.assertRaises(Exception):
            promote(led, nom["id"], RETRIEVER, self.clock(), EV)


class UnverifiedTests(LedgerCase):
    def test_unverified_events_are_stored_but_not_in_the_established_view(self):
        led = self.ledger()
        led.append(d.assertion("work:may-memnet", HUMAN, self.clock(), status="unverified",
                               basis=[d.external("May MEMNET formulation")]))
        g = Graph.from_ledger(led)
        self.assertEqual(g.query("SELECT status FROM nodes WHERE id='work:may-memnet'"),
                         [("unverified",)])
        self.assertEqual(audit.audit_unverified_marking(led), [])


class SupportTests(LedgerCase):
    def setUp(self):
        super().setUp()
        self.led = self.corpus(self.ledger())

    def g(self):
        return Graph.from_ledger(self.led)

    def test_support_status_is_discrete_and_computed_from_events(self):
        self.assertEqual(supported(self.g(), "claim:c1"), "unassessed")
        s = self.led.append(d.support("claim:c1", HUMAN, self.clock(), EV))
        self.assertEqual(supported(self.g(), "claim:c1"), "supported")
        self.led.append(d.defeat("claim:c1", HUMAN, self.clock(), EV))
        self.assertEqual(supported(self.g(), "claim:c1"), "contested")
        self.led.append(d.defeat("claim:c1", HUMAN, self.clock(), EV, target_event=s["id"]))
        self.assertEqual(supported(self.g(), "claim:c1"), "defeated")

    def test_a_defeated_claim_stays_in_the_graph(self):
        self.led.append(d.defeat("claim:bad", HUMAN, self.clock(), EV))
        g = self.g()
        self.assertEqual(supported(g, "claim:bad"), "defeated")
        self.assertIn("claim:bad", g.node_ids())
        self.assertTrue(g.edges(rel_type="depends_on"))

    def test_provisional_support_does_not_count_by_default(self):
        self.led.append(d.support("claim:c1", HUMAN, self.clock(), EV, status="provisional"))
        self.assertEqual(supported(self.g(), "claim:c1"), "unassessed")
        self.assertEqual(supported(self.g(), "claim:c1", statuses=ALL), "supported")

    def test_relevance_does_not_imply_support_and_support_does_not_imply_relevance(self):
        g = self.g()
        self.assertTrue(relevant(g, "claim:indep", "claim:bad"))
        self.assertEqual(supported(g, "claim:indep"), "unassessed")
        self.led.append(d.support("claim:c3", HUMAN, self.clock(), EV))
        g = self.g()
        self.assertEqual(supported(g, "claim:c3"), "supported")
        self.assertFalse(relevant(g, "claim:c3", "claim:bad"))

    def test_admissibility_is_derived_and_changes_with_support_alone(self):
        self.led.append(d.admit("step:publish", ["claim:c1"], HUMAN, self.clock(), EV))
        g = self.g()
        self.assertEqual(door_state(g, "step:publish"), "dimmed")
        self.led.append(d.support("claim:c1", HUMAN, self.clock(), EV))
        g = self.g()
        self.assertEqual(door_state(g, "step:publish"), "open")
        self.assertEqual(door_state(g, "step:other"), "absent")
        self.assertEqual(audit.audit_derived_admissibility(g), [])

    def test_admissible_does_not_imply_supported(self):
        self.led.append(d.admit("step:publish", [], HUMAN, self.clock(), EV))
        g = self.g()
        self.assertTrue(admissible(g, "step:publish"))
        self.assertEqual(supported(g, "step:publish"), "unassessed")

    def test_channel_change_needs_a_superseding_event(self):
        # The same relation effective in two channels, with no promoting event, is a violation.
        self.led.append(d.relation("claim:indep", "claim:bad", "shares_concept", "support",
                                   HUMAN, self.clock(), EV))
        self.assertTrue(audit.audit_channel_separation(self.led))

    def test_channel_promotion_by_explicit_event_is_clean(self):
        old = [e for e in self.led.events() if e["kind"] == "relate"
               and e["rel_type"] == "shares_concept"][0]
        self.led.append(d.relation("claim:indep", "claim:bad", "shares_concept", "support",
                                   HUMAN, self.clock(), [d.event_ref(old["id"]), d.evidence("promoted")],
                                   supersedes=old["id"]))
        self.assertEqual(audit.audit_channel_separation(self.led), [])
