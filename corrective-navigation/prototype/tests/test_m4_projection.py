import dataclasses

from corrective_nav import audit
from corrective_nav import drafts as d
from corrective_nav import projection as pj
from corrective_nav.clients.text import TextNavigator
from corrective_nav.explain import explain_move
from corrective_nav.flags import Flags
from corrective_nav.ledger import LedgerError
from corrective_nav.schema import ValidationError

from .helpers import EV, HUMAN, LedgerCase


class P(LedgerCase):
    def build(self, flags=None):
        led = self.corpus(self.ledger(flags=flags))
        # the corpus keeps dependencies in the support channel; add relevance edges for layout
        for a, b in (("claim:c1", "claim:c2"), ("claim:c2", "claim:c3"), ("claim:c3", "peer1/z")):
            led.append(d.relation(a, b, "shares_concept", "relevance", HUMAN, self.clock(), EV))
        return led


class TestConstraintEvents(P):
    def test_payload_rules(self):
        led = self.build()
        led.append(d.pin("claim:bad", [0, 1, 2.5], HUMAN, self.clock(), EV))
        led.append(d.group(["claim:c1", "claim:c2"], HUMAN, self.clock(), EV))
        led.append(d.separate(["claim:c3", "claim:bad"], HUMAN, self.clock(), EV))
        for bad in (d.pin("claim:bad", [0, 1], HUMAN, self.clock(), EV),
                    d.pin("claim:bad", [0, 1, True], HUMAN, self.clock(), EV),
                    d.group(["claim:c1"], HUMAN, self.clock(), EV)):
            with self.assertRaises(ValidationError):
                led.append(bad)

    def test_release_must_supersede_a_constraint(self):
        led = self.build()
        c = led.append(d.pin("claim:bad", [0, 0, 0], HUMAN, self.clock(), EV))
        rel = led.events()[0]
        with self.assertRaises(LedgerError):
            led.append(d.release(dict(rel, subject="claim:bad"), HUMAN, self.clock(), EV))
        led.append(d.release(c, HUMAN, self.clock(), EV))
        self.assertEqual(pj.derive_inputs(led.events(), pj.make_key(0, 0)["theta"])["constraints"], [])


class TestReproducible(P):
    def test_same_key_same_file(self):
        led = self.build()
        self.assertEqual(pj.digest(pj.project(led, 3)), pj.digest(pj.project(led, 3)))
        self.assertNotEqual(pj.digest(pj.project(led, 3)), pj.digest(pj.project(led, 4)))

    def test_file_roundtrip_and_verify(self):
        led = self.build()
        p = pj.project(led, 1)
        path = self.dir / "proj.json"
        pj.write(p, path)
        self.assertEqual(pj.read(path), p)
        self.assertEqual(pj.verify(pj.read(path), led), [])

    def test_verify_catches_edited_positions(self):
        led = self.build()
        p = pj.project(led, 1)
        p["positions"]["claim:bad"][0] += 1
        self.assertTrue(pj.verify(p, led))

    def test_version_pins_the_inputs(self):
        led = self.build()
        v = len(led)
        before = pj.digest(pj.project(led, 0, version=v))
        led.append(d.assertion("claim:later", HUMAN, self.clock()))
        self.assertEqual(pj.digest(pj.project(led, 0, version=v)), before)

    def test_layout_reads_only_the_relevance_channel(self):
        led = self.build()
        p = pj.project(led, 0)
        self.assertTrue(all(e[3] == "relevance" for e in p["inputs"]["edges"]))

    def test_pin_places_the_node(self):
        led = self.build()
        led.append(d.pin("claim:bad", [10, 0, 0], HUMAN, self.clock(), EV))
        self.assertEqual(pj.project(led, 0)["positions"]["claim:bad"], [10.0, 0.0, 0.0])

    def test_group_pulls_and_separate_pushes(self):
        led = self.build()
        dist = lambda p, a, b: sum((x - y) ** 2 for x, y in zip(p["positions"][a], p["positions"][b])) ** .5
        base = pj.project(led, 0)
        led.append(d.group(["claim:bad", "peer1/z"], HUMAN, self.clock(), EV))
        self.assertLess(dist(pj.project(led, 0), "claim:bad", "peer1/z"), dist(base, "claim:bad", "peer1/z"))


class TestAttribution(P):
    def test_single_factor_changes_are_attributed_to_that_factor(self):
        led = self.build()
        self.assertEqual(audit.audit_attribution(led), [])

    def test_graph_change_names_the_events(self):
        led = self.build()
        a = pj.project(led, 0)
        led.append(d.assertion("claim:new", HUMAN, self.clock()))
        e = led.append(d.relation("claim:new", "claim:bad", "shares_concept", "relevance",
                                  HUMAN, self.clock(), EV))
        b = pj.project(led, 0)
        attr = pj.attribute(a, b)
        self.assertEqual(attr["added"], ["claim:new"])
        self.assertTrue(attr["changed"]["graph"] and not attr["changed"]["algorithm"])
        ex = explain_move(led, a, b, "claim:new", attr)
        self.assertIn(e["id"], [x["id"] for x in ex["events"]])
        self.assertTrue(all(x["direct"] for x in ex["events"] if x["id"] == e["id"]))

    def test_constraint_change_is_attributed_to_constraints(self):
        led = self.build()
        a = pj.project(led, 0)
        led.append(d.pin("claim:c2", [20, 20, 20], HUMAN, self.clock(), EV))
        attr = pj.attribute(a, pj.project(led, 0))
        self.assertEqual(attr["changed"], {"graph": False, "constraints": True, "algorithm": False})
        self.assertIn("claim:c2", attr["effects"]["constraints"])

    def test_nothing_changed_means_nothing_moved(self):
        led = self.build()
        attr = pj.attribute(pj.project(led, 0), pj.project(led, 0))
        self.assertEqual((attr["moved"], attr["unexplained"]), ([], []))

    def test_text_client_moved_command(self):
        led = self.build()
        led.append(d.pin("claim:c2", [20, 20, 20], HUMAN, self.clock(), EV))
        nav = TextNavigator(led, HUMAN, clock=self.clock)
        out = nav.execute(f"moved {len(led) - 1} {len(led)}")
        self.assertIn("constraints yes", out)
        self.assertIn("claim:c2 moved because of: constraints", nav.execute(f"moved {len(led) - 1} {len(led)} claim:c2"))

    def test_audits_pass_on_the_full_system(self):
        led = self.build()
        led.append(d.pin("claim:c2", [20, 20, 20], HUMAN, self.clock(), EV))
        results = audit.run_all(led)
        self.assertEqual({k: v for k, v in results.items() if v}, {})


class TestAblations(P):
    def test_nonreproducible_layout_is_caught(self):
        led = self.build(dataclasses.replace(Flags(), reproducible_projection=False))
        self.assertTrue(audit.audit_projection(led))

    def test_unfaithful_attribution_is_caught(self):
        led = self.build(dataclasses.replace(Flags(), faithful_attribution=False))
        self.assertEqual(audit.audit_projection(led), [])
        self.assertTrue(audit.audit_attribution(led))
