import re

from corrective_nav import audit
from corrective_nav import drafts as d
from corrective_nav import testbed as tb
from corrective_nav.clients.arms import ARMS, ArmNavigator, arm
from corrective_nav.graph import Graph
from corrective_nav.repair import DEFAULT_DEPS, _normalize_scope, traverse

from .helpers import LedgerCase


class T(LedgerCase):
    def plant(self, seed=1, name="tb", **kw):
        led, truth = tb.generate(self.dir / f"{name}.jsonl", self.dir / f"{name}.json", seed=seed, **kw)
        return led, truth


class TestGenerator(T):
    def test_deterministic_for_a_seed(self):
        self.plant(1, "a")
        self.plant(1, "b")
        self.assertEqual((self.dir / "a.jsonl").read_bytes(), (self.dir / "b.jsonl").read_bytes())
        self.assertEqual((self.dir / "a.json").read_bytes(), (self.dir / "b.json").read_bytes())
        self.plant(2, "c")
        self.assertNotEqual((self.dir / "a.jsonl").read_bytes(), (self.dir / "c.jsonl").read_bytes())

    def test_planted_ledger_passes_every_audit(self):
        led, _ = self.plant()
        self.assertEqual({k: v for k, v in audit.run_all(led).items() if v}, {})

    def test_graph_explicit_labels_match_an_independent_traversal(self):
        for seed in (0, 1, 2, 3):
            led, truth = self.plant(seed, f"s{seed}")
            g = Graph.from_ledger(led)
            found, limits = traverse(g, truth["target"], _normalize_scope({}, DEFAULT_DEPS))
            g.close()
            explicit = {k for k, v in truth["dependents"].items() if v["label"] == "graph_explicit"}
            self.assertEqual(set(found), explicit, seed)
            self.assertEqual([l["kind"] for l in limits], ["unadjudicated"])

    def test_human_inferred_are_not_recorded_by_any_established_edge(self):
        led, truth = self.plant()
        g = Graph.from_ledger(led)
        edge_nodes = {x for e in g.edges() for x in (e["subject"], e["object"])
                      if e["channel"] == "support"}
        g.close()
        for k, v in truth["dependents"].items():
            if v["label"] in ("human_inferred", "disputed"):
                self.assertNotIn(k, edge_nodes)

    def test_prior_repair_is_partial_and_names_its_limits(self):
        led, truth = self.plant()
        rep = [e for e in led.events() if e["kind"] == "repair"
               and e["payload"]["role"] == "correction"][0]
        self.assertEqual(rep["payload"]["completeness"], "partial")
        kinds = {l["kind"] for l in rep["payload"]["limits"]}
        self.assertIn("depth", kinds)


class TestScoring(T):
    def test_exact_selection_scores_one(self):
        _, truth = self.plant()
        sel = [k for k, v in truth["dependents"].items() if v["label"] != "disputed"]
        s = tb.score_selection(truth, sel)
        self.assertEqual((s["recall"], s["precision"]), (1.0, 1.0))

    def test_graph_only_selection_misses_the_implicit_ones(self):
        _, truth = self.plant()
        sel = [k for k, v in truth["dependents"].items() if v["label"] == "graph_explicit"]
        s = tb.score_selection(truth, sel)
        self.assertEqual(s["recall_by_label"]["graph_explicit"], 1.0)
        self.assertEqual(s["recall_by_label"]["human_inferred"], 0.0)
        self.assertLess(s["recall"], 1.0)
        self.assertEqual(s["precision"], 1.0)

    def test_disputed_and_target_are_excluded_from_both_denominators(self):
        _, truth = self.plant()
        s = tb.score_selection(truth, ["claim:x1", truth["target"]])
        self.assertEqual(s["precision_rows"], [])
        self.assertIsNone(s["precision"])
        self.assertTrue(all(r["label"] != "disputed" for r in s["recall_rows"]))

    def test_wrong_candidates_lower_precision_only(self):
        _, truth = self.plant()
        sel = [k for k, v in truth["dependents"].items() if v["label"] == "graph_explicit"] + ["claim:k1"]
        s = tb.score_selection(truth, sel)
        self.assertLess(s["precision"], 1.0)
        self.assertEqual(s["recall_by_label"]["graph_explicit"], 1.0)

    def test_completeness_scoring(self):
        _, truth = self.plant()
        self.assertEqual(tb.score_completeness(truth, "partial")["correct"], 1)
        self.assertEqual(tb.score_completeness(truth, "complete")["correct"], 0)

    def test_rows_csv(self):
        _, truth = self.plant()
        s = tb.score_selection(truth, ["claim:d1"])
        rows = [dict(r, participant="p1", arm="typed", task="T2") for r in s["recall_rows"]]
        tb.write_rows(self.dir / "r.csv", rows, ["participant", "arm", "task", "dependent", "label", "hit"])
        self.assertEqual((self.dir / "r.csv").read_text().splitlines()[0],
                         "participant,arm,task,dependent,label,hit")


class TestBaselines(T):
    def test_keyword_returns_the_contrasting_claim_too(self):
        led, truth = self.plant()
        hits = tb.keyword(led, truth["target"])
        self.assertIn("claim:k1", hits)  # mentions the target but does not rely on it
        s = tb.score_selection(truth, hits)
        self.assertLess(s["precision"], 1.0)
        self.assertGreater(s["recall_by_label"]["human_inferred"], 0.0)

    def test_directory_groups_by_namespace(self):
        led, _ = self.plant()
        groups = tb.directory(led)
        self.assertIn("peer1", groups)
        self.assertIn("claim:t", groups[""])

    def test_similarity_returns_neighbours(self):
        led, truth = self.plant()
        self.assertTrue(tb.similar(led, truth["target"], 3))


def walk(nav, target):
    """A scripted reader that uses only the interface: follows incoming depends_on links
    and shares_obligation links in the Support section."""
    seen, queue = {target}, [target]
    while queue:
        node = queue.pop(0)
        out = nav.execute(f"show {node}")
        support = out.split("\nSupport\n")[1].split("\nAdmissibility")[0]
        for m in re.finditer(r"^\s+\d+\. (->|<-) (\S+)\s+(\S+)\s+#", support, re.M):
            arrow, rel, other = m.groups()
            if (rel == "depends_on" and arrow == "<-") or rel == "shares_obligation":
                if other not in seen:
                    seen.add(other)
                    queue.append(other)
    return seen - {target}


class TestArms(T):
    def navs(self, led):
        return {name: ArmNavigator(led, d.actor("p"), arm(name), clock=self.clock) for name in ARMS}

    def test_gating(self):
        led, _ = self.plant()
        navs = self.navs(led)
        for name, (L, G) in ARMS.items():
            self.assertEqual(not navs[name].execute("repairs").startswith("error"), L, name)
            self.assertEqual(not navs[name].execute("near claim:t").startswith("error"), G, name)
            for banned in ("suggest", "promote", "repair"):
                self.assertTrue(navs[name].execute(banned).startswith("error"), (name, banned))

    def test_all_arms_read_one_store_and_write_nothing(self):
        led, _ = self.plant()
        before = led.path.read_bytes()
        for nav in self.navs(led).values():
            for c in ("show claim:t", "follow 1", "back", "path", "explain 1", "why claim:t"):
                nav.execute(c)
            nav.execute("repairs"), nav.execute("status claim:d1"), nav.execute("near claim:t")
        self.assertEqual(led.path.read_bytes(), before)

    def test_shared_views_differ_only_by_the_review_line(self):
        led, _ = self.plant()
        navs = self.navs(led)
        plain = navs["typed"].execute("show claim:d1")
        self.assertEqual(navs["geometry"].execute("show claim:d1"), plain)
        with_l = navs["ledger"].execute("show claim:d1")
        self.assertIn("Review: needs_review", with_l)
        self.assertEqual(re.sub(r"Review: .*\n", "", with_l), plain)
        self.assertEqual(navs["full"].execute("show claim:d1"), with_l)

    def test_displayed_output_passes_the_audit_in_every_arm(self):
        led, _ = self.plant()
        for name, nav in self.navs(led).items():
            for c in ("show claim:t", "show claim:d1", "show peer1/r1"):
                self.assertEqual(audit.audit_displayed(led, nav.execute(c)), [], (name, c))

    def test_repair_provenance_is_not_visible_without_l(self):
        led, _ = self.plant()
        navs = self.navs(led)
        rep = [e for e in led.events() if e["kind"] == "repair"][0]
        self.assertTrue(navs["typed"].execute(f"explain {rep['id'][:10]}").startswith("error"))
        self.assertNotIn("repair", navs["typed"].execute("show claim:d1"))
        self.assertIn("limit depth", navs["ledger"].execute("repairs"))

    def test_walker_finds_the_graph_explicit_dependents_in_every_arm(self):
        led, truth = self.plant()
        explicit = {k for k, v in truth["dependents"].items() if v["label"] == "graph_explicit"}
        for name, nav in self.navs(led).items():
            found = walk(nav, truth["target"])
            self.assertEqual(found, explicit, name)
            s = tb.score_selection(truth, found)
            self.assertEqual(s["precision"], 1.0)
            self.assertEqual(s["recall_by_label"]["human_inferred"], 0.0)

    def test_ledger_arm_exposes_the_stated_limits_that_explain_the_gap(self):
        led, _ = self.plant()
        out = self.navs(led)["ledger"].execute("repairs")
        self.assertIn("limit unadjudicated: claim:i1", out)


class TestReading(T):
    def test_read_is_available_in_every_arm_and_exposes_the_implicit_dependents(self):
        led, truth = self.plant()
        for name in ARMS:
            nav = ArmNavigator(led, d.actor("p"), arm(name), clock=self.clock)
            found = {n for n in truth["dependents"] if truth["target"] in nav.execute(f"read {n}")}
            self.assertTrue({k for k, v in truth["dependents"].items()
                             if v["label"] == "human_inferred"} <= found, name)
            self.assertIn("claim:k1", {n for n in truth["distractors"]
                                       if truth["target"] in nav.execute(f"read {n}")})
