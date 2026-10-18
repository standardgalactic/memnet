"""M0: schema, canonical form, identifiers, validation (invariants 3 structural, 8, and parts of 5 and 11)."""

import unittest

from corrective_nav import drafts as d
from corrective_nav.schema import ValidationError, canonical, event_id, validate
from tests.helpers import EV, HUMAN, RETRIEVER

T = "2026-10-18T09:00:00Z"


def rel(**over):
    base = d.relation("a", "b", "cites", "relevance", HUMAN, T, EV)
    base.update(over)
    return base


class SchemaTests(unittest.TestCase):
    def rejected(self, draft, fragment):
        with self.assertRaises(ValidationError) as cm:
            validate(draft)
        self.assertTrue(any(fragment in r for r in cm.exception.reasons), cm.exception.reasons)

    def test_valid_assertion_without_basis(self):
        ev = validate(d.assertion("a", HUMAN, T))
        self.assertEqual(ev["basis"], [])
        self.assertIsNone(ev["git_ref"])

    def test_relation_needs_exactly_one_channel(self):
        self.rejected(rel(channel=None), "exactly one channel")
        self.rejected(rel(channel=["relevance", "support"]), "exactly one channel")
        self.rejected(rel(channel="trust"), "exactly one channel")

    def test_non_assert_kinds_need_a_basis(self):
        self.rejected(d.relation("a", "b", "cites", "relevance", HUMAN, T, []), "nonempty basis")
        self.rejected(d.support("a", HUMAN, T, []), "nonempty basis")
        self.rejected(d.defeat("a", HUMAN, T, []), "nonempty basis")

    def test_declared_sets_are_enforced(self):
        self.rejected(rel(rel_type="resembles"), "rel_type")
        bad = d.assertion("a", HUMAN, T)
        bad["kind"] = "invent"
        self.rejected(bad, "kind")
        self.rejected(d.assertion("a", HUMAN, T, status="trusted"), "status")

    def test_git_ref_is_nullable_and_checked(self):
        validate(d.assertion("a", HUMAN, T, git_ref=None))
        validate(d.assertion("a", HUMAN, T, git_ref="a" * 40))
        self.rejected(d.assertion("a", HUMAN, T, git_ref="HEAD"), "git_ref")

    def test_no_git_history_can_be_copied_in(self):
        bad = d.assertion("a", HUMAN, T)
        bad["git_log"] = "commit abc ..."
        self.rejected(bad, "unknown field")

    def test_retriever_output_must_be_provisional_and_model_stamped(self):
        ok = d.nomination("a", "b", "shares_concept", "relevance", RETRIEVER, "emb", "1.0", T)
        validate(ok)
        self.rejected(d.relation("a", "b", "cites", "relevance", RETRIEVER, T,
                                 [d.model("emb", "1.0")], status="established"), "provisional")
        self.rejected(d.relation("a", "b", "cites", "relevance", RETRIEVER, T, EV,
                                 status="provisional"), "model id and version")
        self.rejected(d.assertion("a", RETRIEVER, T, status="provisional"), "only nominate")

    def test_unchecked_external_material_must_be_marked_unverified(self):
        cite = [d.external("May MEMNET formulation", verified=False)]
        self.rejected(d.assertion("a", HUMAN, T, status="established", basis=cite), "unverified")
        validate(d.assertion("a", HUMAN, T, status="unverified", basis=cite))
        validate(d.assertion("a", HUMAN, T, status="established",
                             basis=[d.external("checked source", verified=True)]))

    def test_payloads_are_strict(self):
        bad_admit = d.admit("door", [], HUMAN, T, EV)
        bad_admit["payload"] = {"requires": "not-a-list"}
        self.rejected(bad_admit, "requires")
        bad = d.assertion("a", HUMAN, T)
        bad["payload"] = {"x": 1}
        self.rejected(bad, "payload must be empty")

    def test_identifier_is_content_addressed_and_order_independent(self):
        ev = validate(d.assertion("a", HUMAN, T))
        reordered = dict(reversed(list(ev.items())))
        self.assertEqual(event_id(ev), event_id(reordered))
        self.assertEqual(canonical(ev), canonical(reordered))
        other = validate(d.assertion("b", HUMAN, T))
        self.assertNotEqual(event_id(ev), event_id(other))

    def test_stated_id_must_match_content(self):
        ev = validate(d.assertion("a", HUMAN, T))
        ev["id"] = "0" * 64
        self.rejected(ev, "id does not match")


if __name__ == "__main__":
    unittest.main()
