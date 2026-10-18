"""Build a small sample ledger for trying the text client.

    python3 -m corrective_nav.demo demo.jsonl
    python3 -m corrective_nav.clients.text demo.jsonl --actor nate -c "show claim:bad"
"""

import sys

from . import drafts as d
from .ledger import Ledger
from .status import promote

HUMAN = d.actor("nate")
RETRIEVER = d.actor("embedder", "retriever")


def build(path):
    ledger = Ledger(path)
    n = iter(range(10_000))
    t = lambda: f"2026-10-18T09:{next(n) // 60:02d}:{next(n) % 60:02d}Z"
    ev = [d.evidence("demo corpus")]
    for node in ("claim:bad", "claim:c1", "claim:c2", "claim:indep", "peer1/z", "claim:near"):
        ledger.append(d.assertion(node, HUMAN, t()))
    rel = lambda s, o, r, c: ledger.append(d.relation(s, o, r, c, HUMAN, t(), ev))
    rel("claim:c1", "claim:bad", "depends_on", "support")
    rel("claim:c2", "claim:c1", "depends_on", "support")
    rel("peer1/z", "claim:c2", "depends_on", "support")
    rel("claim:indep", "claim:bad", "shares_concept", "relevance")
    s = ledger.append(d.support("claim:c1", HUMAN, t(), [d.evidence("source A")]))
    ledger.append(d.defeat("claim:c1", HUMAN, t(), [d.evidence("source A retracted")],
                           target_event=s["id"]))
    nom = ledger.append(d.nomination("claim:bad", "claim:near", "shares_concept", "relevance",
                                     RETRIEVER, "embedder", "0.1", t()))
    ledger.append(d.assertion("claim:old", HUMAN, t(), status="unverified",
                              basis=[d.external("Smith 1998, unchecked")]))
    promote(ledger, nom["id"], HUMAN, t(), [d.evidence("read both passages")])
    return ledger


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "demo.jsonl")
