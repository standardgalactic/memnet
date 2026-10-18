import itertools
import tempfile
import unittest
from pathlib import Path

from corrective_nav import drafts as d
from corrective_nav.ledger import Ledger

HUMAN = d.actor("nate")
RETRIEVER = d.actor("embedder", "retriever")
EV = [d.evidence("fixture")]


class Clock:
    """Deterministic, strictly increasing timestamps."""

    def __init__(self):
        self._n = itertools.count()

    def __call__(self):
        n = next(self._n)
        return f"2026-10-18T09:{n // 60:02d}:{n % 60:02d}Z"


class LedgerCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)
        self.clock = Clock()

    def ledger(self, name="ledger.jsonl", flags=None):
        if flags is None:
            return Ledger(self.dir / name)
        return Ledger(self.dir / name, flags)

    def corpus(self, ledger):
        """A small linked corpus with a known dependency structure.

        claim:bad is the defective claim. Dependents:
          claim:c1 depends_on claim:bad          (distance 1)
          claim:c2 depends_on claim:c1           (distance 2)
          claim:c3 shares_obligation claim:c2    (distance 3, symmetric type)
          peer1/z  depends_on claim:c2           (distance 3, remote namespace)
        claim:indep is relevant to claim:bad but is not a dependent.
        """
        t = self.clock
        a = lambda n: ledger.append(d.assertion(n, HUMAN, t()))
        for n in ("claim:bad", "claim:c1", "claim:c2", "claim:c3", "claim:indep", "peer1/z"):
            a(n)
        rel = lambda s, o, r, c: ledger.append(d.relation(s, o, r, c, HUMAN, t(), EV))
        rel("claim:c1", "claim:bad", "depends_on", "support")
        rel("claim:c2", "claim:c1", "depends_on", "support")
        rel("claim:c3", "claim:c2", "shares_obligation", "support")
        rel("peer1/z", "claim:c2", "depends_on", "support")
        rel("claim:indep", "claim:bad", "shares_concept", "relevance")
        return ledger
