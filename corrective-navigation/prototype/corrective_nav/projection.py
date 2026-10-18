"""M4: the spatial projection, its key, and the attribution diff.

A projection is plain data: {"key", "inputs", "positions"}. The key is
(v, a, theta, s): ledger version, algorithm identifier, parameters, seed. The
inputs are exactly what the layout reads (nodes, layout edges, constraints),
derived from the effective ledger events at version v. The layout is a pure
function of inputs and key, so the same ledger version and key give the same
file, and anyone holding the file can recompute and check it.

Layout policy: proximity encodes the relevance channel only, so the support and
admissibility channels are not collapsed into distance (they are encoded by
other means in a client). Which channels and statuses the layout reads is part
of theta.

Attribution: to say why a position changed between two projections, each
factor (graph, constraints, algorithm) is swapped in alone and the layout is
recomputed. A node is attributed to every factor whose single change moves it;
a node moved only by the combination is reported as an interaction; a node that
moves when no factor changed is reported as unexplained, which is an invariant
violation, not an attribution.
"""

import hashlib
import json
import math
import os

from .flags import DEFAULT_FLAGS
from .graph import effective

ALGORITHM = "fr3d/1"
DEFAULT_THETA = {
    "iterations": 150,
    "k": 1.0,
    "channels": ["relevance"],
    "statuses": ["established"],
    "group_weight": 3.0,
    "separate_factor": 4.0,
}
EPS = 1e-5
_NODE_KINDS = ("assert", "relate", "support", "defeat", "admit")
FACTORS = ("graph", "constraints", "algorithm")


def _theta(theta):
    out = dict(DEFAULT_THETA)
    out.update(theta or {})
    out["channels"] = sorted(out["channels"])
    out["statuses"] = sorted(out["statuses"])
    return out


# -- inputs ------------------------------------------------------------------

def derive_inputs(events, theta):
    """What the layout reads, from the effective events of a ledger prefix."""
    statuses, channels = set(theta["statuses"]), set(theta["channels"])
    nodes, edges, constraints = set(), set(), []
    for e in effective(events):
        if e["kind"] in _NODE_KINDS and e["status"] in statuses:
            nodes.add(e["subject"])
            if e["kind"] == "relate":
                nodes.add(e["object"])
                if e["channel"] in channels:
                    edges.add((e["subject"], e["object"], e["rel_type"], e["channel"]))
        elif e["kind"] == "constrain" and e["status"] == "established" \
                and e["payload"]["constraint"] != "release":
            c = {"event": e["id"], "constraint": e["payload"]["constraint"], "subject": e["subject"]}
            for k in ("position", "members"):
                if k in e["payload"]:
                    c[k] = e["payload"][k]
            constraints.append(c)
    constraints.sort(key=lambda c: c["event"])
    return {"nodes": sorted(nodes), "edges": [list(x) for x in sorted(edges)],
            "constraints": constraints}


# -- layout ------------------------------------------------------------------

def _start(seed, node, spread):
    h = hashlib.sha256(f"{seed}|{node}".encode()).digest()
    return [((int.from_bytes(h[i * 8:(i + 1) * 8], "big") / 2 ** 64) - 0.5) * 2 * spread
            for i in range(3)]


def layout(inputs, key, flags=DEFAULT_FLAGS):
    """Deterministic force-directed layout in three dimensions. Pure in (inputs, key)."""
    theta, seed = key["theta"], key["s"]
    if not flags.reproducible_projection:  # ablated: the seed is not what the layout uses
        seed = os.urandom(8).hex()
    nodes = inputs["nodes"]
    index = {n: i for i, n in enumerate(nodes)}
    n = len(nodes)
    k, T = theta["k"], theta["iterations"]
    spread = k * max(1, n) ** (1 / 3)
    pos = [_start(seed, node, spread) for node in nodes]

    attract, apart, pinned = {}, set(), {}
    for s, o, _, _ in inputs["edges"]:
        if s in index and o in index and s != o:
            pair = tuple(sorted((index[s], index[o])))
            attract[pair] = max(attract.get(pair, 0.0), 1.0)
    for c in inputs["constraints"]:
        if c["constraint"] == "pin" and c["subject"] in index:
            pinned[index[c["subject"]]] = [float(v) for v in c["position"]]
        elif c["constraint"] in ("group", "separate"):
            present = sorted(index[m] for m in c["members"] if m in index)
            for a in range(len(present)):
                for b in range(a + 1, len(present)):
                    pair = (present[a], present[b])
                    if c["constraint"] == "group":
                        attract[pair] = attract.get(pair, 0.0) + theta["group_weight"]
                    else:
                        apart.add(pair)
    for i, p in pinned.items():
        pos[i] = list(p)

    t0 = spread
    for step in range(T):
        temp = t0 * (1 - step / T)
        disp = [[0.0, 0.0, 0.0] for _ in range(n)]
        for i in range(n):
            for j in range(i + 1, n):
                d = [pos[i][a] - pos[j][a] for a in range(3)]
                dist = math.sqrt(d[0] * d[0] + d[1] * d[1] + d[2] * d[2])
                if dist < 1e-9:
                    d, dist = [1e-3, 0.0, 0.0], 1e-3
                f = k * k / dist
                if (i, j) in apart:
                    f *= theta["separate_factor"]
                for a in range(3):
                    disp[i][a] += d[a] / dist * f
                    disp[j][a] -= d[a] / dist * f
        for (i, j), w in sorted(attract.items()):
            d = [pos[i][a] - pos[j][a] for a in range(3)]
            dist = math.sqrt(d[0] * d[0] + d[1] * d[1] + d[2] * d[2])
            if dist < 1e-9:
                continue
            f = w * dist * dist / k
            for a in range(3):
                disp[i][a] -= d[a] / dist * f
                disp[j][a] += d[a] / dist * f
        for i in range(n):
            if i in pinned:
                continue
            m = math.sqrt(sum(v * v for v in disp[i]))
            if m > 1e-12:
                scale = min(m, temp) / m
                for a in range(3):
                    pos[i][a] += disp[i][a] * scale
    return {node: [round(v, 6) + 0.0 for v in pos[index[node]]] for node in nodes}


# -- projections ---------------------------------------------------------------

def make_key(version, seed, theta=None):
    return {"v": version, "a": ALGORITHM, "theta": _theta(theta), "s": seed}


def build(inputs, key, flags=DEFAULT_FLAGS):
    return {"key": key, "inputs": inputs, "positions": layout(inputs, key, flags)}


def project(ledger, seed=0, theta=None, version=None):
    """The projection of the ledger at `version` under (a, theta, seed)."""
    if version is None:
        version = len(ledger)
    key = make_key(version, seed, theta)
    return build(derive_inputs(ledger.events(version), key["theta"]), key, ledger.flags)


def serialize(proj):
    return json.dumps(proj, sort_keys=True, separators=(",", ":"))


def digest(proj):
    return hashlib.sha256(serialize(proj).encode()).hexdigest()


def key_id(key):
    return hashlib.sha256(json.dumps(key, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:12]


def write(proj, path):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(serialize(proj) + "\n")


def read(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def verify(proj, ledger=None):
    """Recompute from the file's own inputs and key; optionally recheck the inputs against the ledger."""
    flags = ledger.flags if ledger is not None else DEFAULT_FLAGS
    out = []
    if layout(proj["inputs"], proj["key"], flags) != proj["positions"]:
        out.append("positions are not the layout of the recorded inputs and key")
    if ledger is not None:
        want = derive_inputs(ledger.events(proj["key"]["v"]), proj["key"]["theta"])
        if want != proj["inputs"]:
            out.append("inputs are not those of the ledger at the recorded version")
    return out


# -- attribution -----------------------------------------------------------------

def _graph_part(p):
    return {"nodes": p["inputs"]["nodes"], "edges": p["inputs"]["edges"]}


def _algo_part(p):
    k = p["key"]
    return {"a": k["a"], "theta": k["theta"], "s": k["s"]}


def _compose(g, c, al, flags):
    key = {"v": 0, "a": al["a"], "theta": al["theta"], "s": al["s"]}
    return layout({"nodes": g["nodes"], "edges": g["edges"], "constraints": c}, key, flags)


def _displaced(p, q):
    return sorted(n for n in set(p) & set(q)
                  if math.dist(p[n], q[n]) > EPS)


def attribute(a, b, flags=DEFAULT_FLAGS):
    """Why positions differ between projections `a` and `b`, by single-factor counterfactuals."""
    pa, pb = a["positions"], b["positions"]
    added, removed = sorted(set(pb) - set(pa)), sorted(set(pa) - set(pb))
    moved = _displaced(pa, pb)
    parts = {
        "graph": (_graph_part(a), _graph_part(b)),
        "constraints": (a["inputs"]["constraints"], b["inputs"]["constraints"]),
        "algorithm": (_algo_part(a), _algo_part(b)),
    }
    changed = {f: parts[f][0] != parts[f][1] for f in FACTORS}
    ga, ca, aa = _graph_part(a), a["inputs"]["constraints"], _algo_part(a)
    swapped = {
        "graph": _compose(_graph_part(b), ca, aa, flags),
        "constraints": _compose(ga, b["inputs"]["constraints"], aa, flags),
        "algorithm": _compose(ga, ca, _algo_part(b), flags),
    }
    base = _compose(ga, ca, aa, flags)
    effects = {f: (_displaced(base, swapped[f]) if changed[f] else []) for f in FACTORS}
    causes = {}
    for node in moved:
        hit = [f for f in FACTORS if node in effects[f]]
        if hit:
            causes[node] = hit
        else:
            causes[node] = ["interaction"] if any(changed.values()) else ["unexplained"]
    for node in added + removed:
        causes[node] = ["graph"]
    result = {
        "from": key_id(a["key"]), "to": key_id(b["key"]),
        "versions": [a["key"]["v"], b["key"]["v"]],
        "changed": changed, "added": added, "removed": removed, "moved": moved,
        "effects": effects, "causes": causes,
        "interaction": sorted(n for n, c in causes.items() if c == ["interaction"]),
        "unexplained": sorted(n for n, c in causes.items() if c == ["unexplained"]),
    }
    if not flags.faithful_attribution:  # ablated: the graph is blamed for everything
        everything = sorted(set(moved) | set(added) | set(removed))
        result.update({
            "changed": {"graph": True, "constraints": False, "algorithm": False},
            "effects": {"graph": everything, "constraints": [], "algorithm": []},
            "causes": {n: ["graph"] for n in everything},
            "interaction": [], "unexplained": [],
        })
    return result


def render_attribution(attr, limit=8):
    def names(xs):
        xs = list(xs)
        return ", ".join(xs[:limit]) + (f" (+{len(xs) - limit} more)" if len(xs) > limit else "") if xs else "none"

    ch = attr["changed"]
    lines = [f"Movement from version {attr['versions'][0]} (key {attr['from']}) "
             f"to version {attr['versions'][1]} (key {attr['to']})",
             "Changed: " + ", ".join(f"{f} {'yes' if ch[f] else 'no'}" for f in FACTORS),
             f"Added nodes: {names(attr['added'])}",
             f"Removed nodes: {names(attr['removed'])}",
             f"Moved nodes: {len(attr['moved'])}"]
    for f in FACTORS:
        if attr["effects"][f]:
            lines.append(f"  moved by the {f} change alone: {names(attr['effects'][f])}")
    if attr["interaction"]:
        lines.append(f"  moved only by factors in combination: {names(attr['interaction'])}")
    if attr["unexplained"]:
        lines.append(f"  UNEXPLAINED (no factor changed): {names(attr['unexplained'])}")
    return "\n".join(lines)


def main(argv=None):
    import argparse
    from .ledger import Ledger
    ap = argparse.ArgumentParser(description="Write the projection data file for a ledger")
    ap.add_argument("ledger")
    ap.add_argument("out")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--version", type=int, default=None)
    args = ap.parse_args(argv)
    proj = project(Ledger(args.ledger), args.seed, version=args.version)
    write(proj, args.out)
    print(f"wrote {args.out}: key {key_id(proj['key'])}, {len(proj['positions'])} nodes, "
          f"digest {digest(proj)[:12]}")


if __name__ == "__main__":
    main()
