"""Ablated variants: each flag violates exactly one invariant, and the audit must notice.

These show that the audit suite is sensitive: a suite that also passed on a
broken system would be evidence of nothing.
"""

from corrective_nav import audit, drafts as d
from corrective_nav.flags import Flags
from corrective_nav.repair import repair
from tests.helpers import EV, HUMAN, RETRIEVER, LedgerCase


class AblationTests(LedgerCase):
    def broken(self, **flag):
        return self.corpus(self.ledger(flags=Flags(**flag)))

    def test_full_system_passes_every_audit(self):
        led = self.corpus(self.ledger())
        repair(led, "claim:bad", "defect", HUMAN, self.clock(), EV, scope={"accessible": []})
        results = audit.run_all(led)
        self.assertTrue(all(v == [] for v in results.values()), results)

    def test_honest_completeness_ablation_is_caught(self):
        led = self.broken(honest_completeness=False)
        r, _ = repair(led, "claim:bad", "defect", HUMAN, self.clock(), EV, scope={"accessible": []})
        self.assertEqual(r["payload"]["completeness"], "complete")   # the ablated behaviour
        self.assertTrue(audit.audit_honest_completeness(led))

    def test_repair_accountability_ablation_is_caught(self):
        led = self.broken(repair_records_dependents=False)
        repair(led, "claim:bad", "defect", HUMAN, self.clock(), EV)
        self.assertTrue(audit.audit_repair_accountability(led))

    def test_retriever_ablation_is_caught(self):
        led = self.broken(enforce_retriever_provisional=False)
        led.append(d.relation("claim:indep", "claim:c3", "shares_concept", "relevance", RETRIEVER,
                              self.clock(), [d.model("emb", "1.0")], status="established"))
        problems = audit.audit_retriever(led)
        self.assertTrue(problems)
        self.assertTrue(any("removing the retriever" in p for p in problems))

    def test_unverified_marking_ablation_is_caught(self):
        led = self.broken(enforce_unverified_marking=False)
        led.append(d.assertion("work:old", HUMAN, self.clock(), status="established",
                               basis=[d.external("unchecked manuscript")]))
        self.assertTrue(audit.audit_unverified_marking(led))
