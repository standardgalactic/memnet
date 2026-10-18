import dataclasses
import unittest

from corrective_nav import audit
from corrective_nav import drafts as d
from corrective_nav import projection as pj
from corrective_nav import testbed as tb
from corrective_nav.clients.spatial.page import render_html, write_page
from corrective_nav.clients.spatial.runner import available, run_view
from corrective_nav.clients.spatial.scene import build_scene
from corrective_nav.flags import Flags
from corrective_nav.ledger import Ledger

from .helpers import LedgerCase

ALL = {"statuses": ["established", "provisional", "unverified"]}


@unittest.skipUnless(available(), "Node is required")
class S(LedgerCase):
    def plant(self, name="s"):
        led, truth = tb.generate(self.dir / f"{name}.jsonl", self.dir / f"{name}.json", seed=1)
        led.append(d.assertion("claim:old", d.actor("planter"), "2026-10-18T12:00:00Z", status="unverified",
                               basis=[d.external("Smith 1998, unchecked")]))
        return led

    def ablated(self, **kw):
        """The same planted ledger read under flags with one display switch off."""
        led = self.plant("ablated" + "_".join(kw))
        return Ledger(led.path, dataclasses.replace(Flags(), **kw))


class TestScene(S):
    def test_scene_is_plain_data_with_separate_encodings(self):
        led = self.plant()
        sc = build_scene(led, theta=ALL)
        self.assertEqual({e["channel"] for e in sc["edges"]}, {"relevance", "support"})
        self.assertIn("node:claim:old", sc["explanations"])
        node = {n["id"]: n for n in sc["nodes"]}
        self.assertEqual(node["claim:old"]["assertion"], "unverified")
        self.assertEqual(node["claim:t"]["support"], "unassessed")

    def test_scene_is_reproducible(self):
        led = self.plant()
        a, b = build_scene(led, theta=ALL), build_scene(led, theta=ALL)
        self.assertEqual(a, b)

    def test_l_switch_adds_review_status_only(self):
        led = self.plant()
        a, b = build_scene(led, L=False), build_scene(led, L=True)
        self.assertTrue(all(n["review"] == [] for n in a["nodes"]))
        self.assertTrue(any(n["review"] for n in b["nodes"]))
        strip = lambda s: [{k: v for k, v in n.items() if k != "review"} for n in s["nodes"]]
        self.assertEqual(strip(a), strip(b))
        self.assertEqual(a["edges"], b["edges"])

    def test_movement_text_cites_events(self):
        led = self.plant()
        sc = build_scene(led, since=len(led) // 2)
        self.assertTrue(sc["movement"])
        self.assertTrue(any("moved because of" in t for t in sc["movement"].values()))


class TestDisplayAudit(S):
    def test_full_system_display_passes(self):
        led = self.plant()
        for theta in (None, ALL):
            self.assertEqual(audit.audit_spatial(led, build_scene(led, theta=theta)), [], theta)

    def test_provisional_hidden_by_default_and_dashed_when_shown(self):
        led = self.plant()
        sc = build_scene(led, theta=ALL)
        hidden = run_view(sc)["items"]
        shown = run_view(sc, show_provisional=True)["items"]
        self.assertFalse([i for i in hidden if i["kind"] == "edge" and i["status"] != "established"])
        prov = [i for i in shown if i["kind"] == "edge" and i["status"] == "provisional"]
        self.assertTrue(prov and all(i["dash"] == "dashed" for i in prov))
        old = [i for i in shown if i.get("id") == "claim:old"][0]
        self.assertEqual(old["glyph"], "dotted-ring")

    def test_door_and_support_marks_follow_derived_state(self):
        led = self.plant()
        led.append(d.admit("claim:d1", ["claim:d2"], d.actor("planter"), "2026-10-18T12:01:00Z",
                           [d.evidence("gate")]))
        sc = build_scene(led)
        nodes = {i["id"]: i for i in run_view(sc)["items"] if i["kind"] == "node"}
        self.assertEqual(nodes["claim:d1"]["door"], "dimmed")
        led.append(d.support("claim:d2", d.actor("planter"), "2026-10-18T12:02:00Z", [d.evidence("s")]))
        nodes = {i["id"]: i for i in run_view(build_scene(led))["items"] if i["kind"] == "node"}
        self.assertEqual(nodes["claim:d1"]["door"], "open")
        self.assertEqual(nodes["claim:d2"]["mark"], "+")

    def test_proximity_alone_draws_no_line(self):
        led = self.plant()
        items = run_view(build_scene(led), show_provisional=True)["items"]
        self.assertTrue(all(i["event"] for i in items if i["kind"] == "edge"))

    def test_ablations_are_caught(self):
        for flag in ("display_channel_separation", "display_status_markers", "display_explanations"):
            led = self.ablated(**{flag: False})
            self.assertTrue(audit.audit_spatial(led, build_scene(led, theta=ALL)), flag)


class TestPage(S):
    def test_page_is_self_contained(self):
        led = self.plant()
        html = render_html(build_scene(led))
        self.assertIn("CNView", html)
        self.assertNotIn("src=", html)
        self.assertNotIn("http://", html.replace("http://www.w3.org", ""))
        write_page(build_scene(led), self.dir / "v.html")

    def test_browser_draws_what_the_audit_checked(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            self.skipTest("playwright is not installed")
        led = self.plant()
        sc = build_scene(led, theta=ALL, L=True)
        write_page(sc, self.dir / "v.html")
        with sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium"
                                         if (__import__("os").path.exists("/opt/pw-browsers/chromium")) else None)
            page = browser.new_page(viewport={"width": 1100, "height": 700})
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"file://{self.dir / 'v.html'}")
            strip = lambda items: sorted((i["kind"], i.get("id") or i.get("event"), i.get("shape"),
                                          i.get("dash"), i.get("glyph"), i.get("support"), i.get("door"))
                                         for i in items)
            self.assertEqual(strip(page.evaluate("window.__items")), strip(run_view(sc)["items"]))
            page.click("#prov")
            self.assertEqual(strip(page.evaluate("window.__items")),
                             strip(run_view(sc, show_provisional=True)["items"]))
            # a real click on a node routes to the resolver's text for that node
            x, y = page.evaluate("window.__screen('node:claim:t')")
            page.mouse.click(x, y)
            expected = run_view(sc, inspect=["node:claim:t"])["inspections"]["node:claim:t"]
            self.assertEqual(page.evaluate("window.__panel"), expected)
            self.assertEqual(page.evaluate("window.__items.filter(i=>i.kind==='trail').length"), 0)
            x, y = page.evaluate("window.__screen('node:claim:d1')")
            page.mouse.click(x, y)
            self.assertEqual(page.evaluate("window.__items.filter(i=>i.kind==='trail').length"), 1)
            page.screenshot(path=str(self.dir / "shot.png"))
            browser.close()
        self.assertEqual(errors, [])
