"""M8 (part): a planted-defect corpus generator, ground truth, scoring and baselines.

The generator plants one defective claim in a synthetic corpus and writes two
things: a ledger (what a participant's interface reads) and a ground-truth file
(never read by any interface). Truth is assigned when each dependent is planted,
not computed from the graph, so a graph-explicit label is a construction fact and
a human-inferred dependent is one that no graph edge records. A test cross-checks
the repair traversal against the graph-explicit labels.

Labels follow the pilot design: graph_explicit, human_inferred, disputed.
Disputed dependents are excluded from the primary scores.

The baselines are plain retrieval functions over the same ledger. The
similarity baseline is a TF-IDF cosine over claim text and is a stand-in for an
embedding model, not an embedding.
"""

import json
import math
import random
import re

from . import drafts as d
from .ledger import Ledger
from .repair import repair

HUMAN = d.actor("planter")
RETRIEVER = d.actor("planted-retriever", "retriever")
LABELS = ("graph_explicit", "human_inferred", "disputed")


class _Clock:
    def __init__(self):
        self.n = 0

    def __call__(self):
        self.n += 1
        return f"2026-10-18T10:{self.n // 60:02d}:{self.n % 60:02d}Z"


def generate(ledger_path, truth_path, seed=0, n_direct=3, n_inferred=2, n_distractors=6,
             n_unrelated=6, prior_repair=True):
    """Plant a defect. Returns (ledger, truth)."""
    rng = random.Random(seed)
    led, t = Ledger(ledger_path), _Clock()
    target = "claim:t"
    text = {target: "Reports the measured value that later claims cite."}
    truth_dep, dep_edges, nodes_order = {}, [], [target]

    def node(name, evidence):
        text[name] = evidence
        nodes_order.append(name)

    counter = {"d": 0}

    def new_dependent(parent, kind="depends_on", label_extra=None):
        counter["d"] += 1
        name = f"claim:d{counter['d']}"
        node(name, f"Argues from the result of {parent}.")
        dep_edges.append((name, parent, kind, "support"))
        truth_dep[name] = {"label": "graph_explicit", "accessible": True}
        return name

    level1 = [new_dependent(target) for _ in range(n_direct)]
    level2 = [new_dependent(p) for p in level1 for _ in range(rng.randint(0, 2))]
    level3 = [new_dependent(p) for p in level2 if rng.random() < 0.5]
    mid = rng.choice(level2 or level1)
    counter["d"] += 1
    sym = f"claim:o{counter['d']}"
    node(sym, f"Shares a commitment with {mid}.")
    dep_edges.append((sym, mid, "shares_obligation", "support"))
    truth_dep[sym] = {"label": "graph_explicit", "accessible": True}
    remote = "peer1/r1"
    node(remote, "A peer system's claim that builds on a local result.")
    dep_edges.append((remote, rng.choice(level2 or level1), "depends_on", "support"))
    truth_dep[remote] = {"label": "graph_explicit", "accessible": False}

    inferred = []
    for i in range(n_inferred):
        name = f"claim:i{i + 1}"
        node(name, f"Builds its estimate on the figure reported in {target}.")
        truth_dep[name] = {"label": "human_inferred", "accessible": True}
        inferred.append(name)
    node("claim:x1", f"Reasoning is similar to {target} and may rely on it.")
    truth_dep["claim:x1"] = {"label": "disputed", "accessible": True}

    contrast = "claim:k1"
    node(contrast, f"Contrasts with {target} and does not rely on it.")
    distractors = [contrast]
    relevance = [(contrast, target, "shares_concept", "relevance")]
    pool = [target] + level1 + level2
    for i in range(n_distractors):
        name = f"claim:n{i + 1}"
        node(name, "Covers a nearby topic without using the result.")
        distractors.append(name)
        relevance.append((name, rng.choice(pool), "shares_concept", "relevance"))
    unrelated = []
    for i in range(n_unrelated):
        name = f"claim:u{i + 1}"
        node(name, "Unrelated background material.")
        unrelated.append(name)
    for a, b in zip(unrelated, unrelated[1:]):
        relevance.append((a, b, "shares_concept", "relevance"))
    for name in inferred:  # connected to the corpus, but not to the target by any edge
        relevance.append((name, rng.choice(unrelated or distractors), "shares_concept", "relevance"))
    node("peer1/q1", "A peer claim near the target topic.")
    distractors.append("peer1/q1")
    relevance.append(("peer1/q1", target, "shares_concept", "relevance"))

    basis = [d.evidence("planted corpus")]
    for name in nodes_order:
        led.append(d.assertion(name, HUMAN, t(), basis=[d.evidence(text[name])]))
    for s, o, r, c in dep_edges + relevance:
        led.append(d.relation(s, o, r, c, HUMAN, t(), basis))
    led.append(d.nomination(inferred[0] if inferred else contrast, target, "depends_on", "support",
                            RETRIEVER, "planted-retriever", "0", t()))
    if inferred:
        truth_dep[inferred[0]]["provisional_edge"] = True

    if prior_repair:
        repair(led, target, "the measured value was misread", d.actor("reviewer"), t(),
               [d.evidence("earlier partial review")], scope={"max_depth": 1, "accessible": []})

    expected = "partial"  # a remote dependent and a provisional dependency edge are planted
    truth = {"seed": seed, "target": target, "defect": "the measured value was misread",
             "dependents": truth_dep, "distractors": sorted(distractors),
             "expected_completeness": expected, "prior_repair": prior_repair}
    with open(truth_path, "w", encoding="utf-8") as fh:
        json.dump(truth, fh, sort_keys=True, indent=1)
        fh.write("\n")
    return led, truth


def load_truth(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


# -- scoring ---------------------------------------------------------------------

def score_selection(truth, selected, labels=("graph_explicit", "human_inferred")):
    """Dependent-level recall rows and candidate-level precision rows.

    Disputed dependents are excluded from both denominators. `selected` may contain the
    target itself, which is neither a dependent nor an error and is ignored."""
    deps = {k: v for k, v in truth["dependents"].items() if v["label"] in labels}
    chosen = sorted(set(selected) - {truth["target"]})
    excluded = {k for k, v in truth["dependents"].items() if v["label"] == "disputed"}
    recall_rows = [{"dependent": k, "label": v["label"], "hit": int(k in chosen)}
                   for k, v in sorted(deps.items())]
    precision_rows = [{"candidate": c, "correct": int(c in deps)}
                      for c in chosen if c not in excluded]
    nr, np_ = len(recall_rows), len(precision_rows)
    hits = sum(r["hit"] for r in recall_rows)
    right = sum(r["correct"] for r in precision_rows)
    by_label = {}
    for lab in labels:
        rows = [r for r in recall_rows if r["label"] == lab]
        by_label[lab] = sum(r["hit"] for r in rows) / len(rows) if rows else None
    return {"recall_rows": recall_rows, "precision_rows": precision_rows,
            "recall": hits / nr if nr else None, "precision": right / np_ if np_ else None,
            "recall_by_label": by_label}


def score_completeness(truth, claimed):
    return {"claimed": claimed, "expected": truth["expected_completeness"],
            "correct": int(claimed == truth["expected_completeness"])}


def write_rows(path, rows, fields):
    """Flat CSV of dependent-level rows for the mixed-effects models."""
    import csv
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


# -- baselines -------------------------------------------------------------------

def claim_texts(ledger):
    """Node id -> text of its effective assertion's evidence."""
    from .graph import effective
    out = {}
    for e in effective(ledger.events()):
        if e["kind"] == "assert":
            out[e["subject"]] = " ".join(b["evidence"] for b in e["basis"] if "evidence" in b)
    return out


def directory(ledger):
    """Baseline: nodes grouped by namespace, no relations."""
    groups = {}
    for n in sorted(claim_texts(ledger)):
        groups.setdefault(n.split("/", 1)[0] if "/" in n else "", []).append(n)
    return groups


def keyword(ledger, query):
    """Baseline: nodes whose id or text contains every query word."""
    words = [w.lower() for w in query.split()]
    return sorted(n for n, tx in claim_texts(ledger).items()
                  if all(w in (n + " " + tx).lower() for w in words))


def _tfidf(texts):
    docs = {n: re.findall(r"\w+", tx.lower()) for n, tx in texts.items()}
    df = {}
    for ws in docs.values():
        for w in set(ws):
            df[w] = df.get(w, 0) + 1
    N = len(docs)
    vecs = {}
    for n, ws in docs.items():
        v = {}
        for w in ws:
            v[w] = v.get(w, 0.0) + math.log((1 + N) / (1 + df[w])) + 1
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        vecs[n] = {w: x / norm for w, x in v.items()}
    return vecs


def similar(ledger, node, n=5):
    """Baseline: nearest nodes by TF-IDF cosine over claim text (a stand-in for embeddings)."""
    vecs = _tfidf(claim_texts(ledger))
    if node not in vecs:
        return []
    sims = sorted(((sum(x * vecs[m].get(w, 0.0) for w, x in vecs[node].items()), m)
                   for m in vecs if m != node), key=lambda p: (-p[0], p[1]))
    return [m for s, m in sims[:n] if s > 0]


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Plant a defect in a synthetic corpus")
    ap.add_argument("ledger")
    ap.add_argument("truth")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args(argv)
    _, truth = generate(args.ledger, args.truth, seed=args.seed)
    print(f"planted {truth['target']} with {len(truth['dependents'])} labelled dependents")


if __name__ == "__main__":
    main()
