import dataclasses

from corrective_nav import audit
from corrective_nav import drafts as d
from corrective_nav.clients.text import TextNavigator
from corrective_nav.explain import explain_event
from corrective_nav.flags import Flags
from corrective_nav.graph import Graph
from corrective_nav.ledger import LedgerError
from corrective_nav.status import promote

from .helpers import EV, HUMAN, RETRIEVER, LedgerCase


class M5Case(LedgerCase):
    def build(self, flags=None):
        led = self.corpus(self.ledger(flags=flags))
        self.nom = led.append(d.nomination("claim:bad", "claim:c3", "shares_concept", "relevance",
                                           RETRIEVER, "embedder", "0.1", self.clock()))
        self.nav = TextNavigator(led, HUMAN, clock=self.clock,
                                 similarity=lambda n: ["claim:c3", "claim:c2"],
                                 retriever=(RETRIEVER, "embedder", "0.1"))
        return led

    def graph_ok(self, led):
        g = Graph.from_ledger(led)
        self.addCleanup(g.close)
        return g


class TestDisplay(M5Case):
    def test_channels_are_separate_sections(self):
        self.build()
        out = self.nav.execute("show claim:bad")
        rel, sup, adm = (out.index(s) for s in ("\nRelevance\n", "\nSupport\n", "\nAdmissibility\n"))
        self.assertLess(rel, sup)
        self.assertLess(sup, adm)
        self.assertIn("claim:indep", out[rel:sup])
        self.assertIn("claim:c1", out[sup:adm])
        self.assertNotIn("claim:c1", out[rel:sup])

    def test_provisional_hidden_by_default_and_marked_when_shown(self):
        self.build()
        self.assertNotIn("claim:c3", self.nav.execute("show claim:bad"))
        shown = self.nav.execute("show claim:bad all")
        line = [l for l in shown.splitlines() if "claim:c3" in l][0]
        self.assertIn("[provisional]", line)

    def test_displayed_output_passes_the_audit(self):
        led = self.build()
        for cmd in ("show claim:bad", "show claim:bad all", "show claim:c2", "show peer1/z all"):
            self.assertEqual(audit.audit_displayed(led, self.nav.execute(cmd)), [], cmd)

    def test_navigation_writes_nothing(self):
        led = self.build()
        before = len(led)
        for cmd in ("show claim:bad", "follow 1", "back", "path", "explain 1", "why claim:c1"):
            self.nav.execute(cmd)
        self.assertEqual(len(led), before)

    def test_follow_back_and_path(self):
        self.build()
        self.nav.execute("show claim:bad")
        self.nav.execute("follow 2")
        self.assertEqual(self.nav.execute("path").count(">"), 1)
        self.nav.execute("back")
        self.assertEqual(self.nav.execute("path"), "claim:bad")

    def test_errors_are_strings(self):
        self.build()
        self.assertTrue(self.nav.execute("show nope").startswith("error:"))
        self.assertTrue(self.nav.execute("follow 99").startswith("error:"))
        self.assertTrue(self.nav.execute("frobnicate").startswith("error:"))


class TestExplain(M5Case):
    def test_explain_by_link_number_and_by_prefix(self):
        led = self.build()
        shown = self.nav.execute("show claim:bad")
        by_number = self.nav.execute("explain 1")
        eid = [l for l in shown.splitlines() if l.strip().startswith("1.")][0].split("#")[1][:8]
        self.assertEqual(self.nav.execute(f"explain {eid}"), by_number)
        self.assertIn("evidence: fixture", by_number)

    def test_promoted_chain_includes_the_retriever_model(self):
        led = self.build()
        new = promote(led, self.nom["id"], HUMAN, self.clock(), [d.evidence("read it")])
        text = self.nav.execute(f"explain {new['id'][:10]}")
        self.assertIn("retriever model: embedder 0.1", text)
        self.assertIn("evidence: read it", text)
        self.assertIn("reached as supersedes", text)

    def test_ambiguous_or_short_prefix_is_rejected(self):
        led = self.build()
        with self.assertRaises(LedgerError):
            led.resolve("ab")
        self.assertTrue(self.nav.execute("explain zzzzzz").startswith("error:"))

    def test_why_lists_support_and_defeat(self):
        led = self.build()
        s = led.append(d.support("claim:c1", HUMAN, self.clock(), EV))
        led.append(d.defeat("claim:c1", HUMAN, self.clock(), EV, target_event=s["id"]))
        text = self.nav.execute("why claim:c1")
        self.assertIn("defeated", text)
        self.assertIn("targets", text)

    def test_explanation_audit_passes(self):
        led = self.build()
        promote(led, self.nom["id"], HUMAN, self.clock(), EV)
        self.assertEqual(audit.audit_explanations(led, self.graph_ok(led)), [])
        self.assertTrue(all(not v for v in audit.run_all(led).values()))


class TestWriting(M5Case):
    def test_write_commands_append_events(self):
        led = self.build()
        n = len(led)
        self.nav.execute("assert claim:new")
        self.nav.execute('relate claim:new depends_on claim:bad support "reads it"')
        self.nav.execute('support claim:bad "source"')
        self.assertEqual(len(led), n + 3)
        self.assertIn("claim:new", self.nav.execute("show claim:bad"))

    def test_unrelate_withdraws_a_link(self):
        self.build()
        self.nav.execute("show claim:bad")
        self.nav.execute('unrelate 1 "mistaken"')
        self.assertNotIn("claim:indep", self.nav.execute("show claim:bad"))

    def test_retriever_cannot_use_promote(self):
        led = self.build()
        nav = TextNavigator(led, RETRIEVER, clock=self.clock)
        self.assertTrue(nav.execute(f'promote {self.nom["id"][:10]} "self approve"').startswith("error:"))

    def test_repair_reports_partial_with_reasons(self):
        self.build()
        out = self.nav.execute('repair claim:bad "wrong figure" "recomputed" local')
        self.assertIn(": partial", out)
        self.assertIn("limit inaccessible: peer1/z", out)

    def test_suggest_nominates_provisionally(self):
        led = self.build()
        out = self.nav.execute("suggest claim:bad")
        self.assertIn("claim:c2", out)  # c3 already has a nomination
        new = [e for e in led.events() if e["actor"]["type"] == "retriever"][-1]
        self.assertEqual(new["status"], "provisional")
        self.assertNotIn("claim:c2", self.nav.execute("show claim:bad"))
        self.assertIn("claim:c2", self.nav.execute("show claim:bad all"))
        self.assertEqual(audit.audit_retriever(led), [])


class TestAblations(M5Case):
    def test_proximity_ablation_is_caught_by_the_display_audit(self):
        flags = dataclasses.replace(Flags(), enforce_proximity_not_authority=False)
        led = self.build(flags)
        text = self.nav.execute("show claim:bad")
        violations = audit.audit_displayed(led, text)
        self.assertTrue(any("without a backing event" in v for v in violations))

    def test_explanation_ablation_is_caught(self):
        flags = dataclasses.replace(Flags(), explanation_available=False)
        led = self.build(flags)
        self.assertTrue(audit.audit_explanations(led, self.graph_ok(led)))
        self.nav.execute("show claim:bad")
        self.assertIn("unavailable", self.nav.execute("explain 1"))

    def test_default_flags_pass_both(self):
        led = self.build()
        self.assertEqual(audit.audit_displayed(led, self.nav.execute("show claim:bad")), [])
        self.assertEqual(audit.audit_explanations(led, self.graph_ok(led)), [])
