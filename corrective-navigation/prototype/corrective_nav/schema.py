"""M0: event schema, canonical serialization, identifier rule, validation.

The sets of kinds, relation types, channels and statuses live in
schema/schema.json so that the schema stays language neutral. This module
only interprets them.
"""

import copy
import hashlib
import json
import re
from pathlib import Path

from .flags import DEFAULT_FLAGS

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schema" / "schema.json"
SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
FIELDS = list(SCHEMA["fields"])

_TS = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_GIT = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")

_DEFAULTS = {
    "subject": None,
    "object": None,
    "rel_type": None,
    "channel": None,
    "basis": [],
    "caused_by": None,
    "supersedes": None,
    "git_ref": None,
    "payload": {},
}
_REQUIRED = ("t", "actor", "kind", "status")


class ValidationError(ValueError):
    def __init__(self, reasons):
        self.reasons = list(reasons)
        super().__init__("; ".join(self.reasons))


def canonical(event):
    """Canonical serialization: sorted keys, no whitespace, UTF-8."""
    return json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def event_id(event):
    """SHA-256 of the canonical form of the event without its id."""
    body = {k: v for k, v in event.items() if k != "id"}
    return hashlib.sha256(canonical(body).encode("utf-8")).hexdigest()


def _nonempty(v):
    return isinstance(v, str) and v != ""


def _check_basis(basis, errs):
    if not isinstance(basis, list):
        errs.append("basis must be a list")
        return
    for i, item in enumerate(basis):
        if not isinstance(item, dict) or len(item) != 1:
            errs.append(f"basis[{i}] must be an object with exactly one key")
            continue
        (key, val), = item.items()
        if key not in SCHEMA["basis_item_types"]:
            errs.append(f"basis[{i}]: unknown item type {key!r}")
        elif key in ("event", "evidence"):
            if not _nonempty(val):
                errs.append(f"basis[{i}].{key} must be a nonempty string")
        elif key == "model":
            if not (isinstance(val, dict) and set(val) == {"id", "version"}
                    and _nonempty(val["id"]) and _nonempty(val["version"])):
                errs.append(f"basis[{i}].model needs nonempty id and version")
        elif key == "external":
            if not (isinstance(val, dict) and set(val) == {"citation", "verified"}
                    and _nonempty(val["citation"]) and isinstance(val["verified"], bool)):
                errs.append(f"basis[{i}].external needs citation and boolean verified")


def _check_repair_payload(p, ev, errs):
    role = p.get("role")
    if role not in SCHEMA["repair_roles"]:
        errs.append(f"repair payload.role must be one of {SCHEMA['repair_roles']}")
        return
    if role == "dependent_status":
        if set(p) != {"role", "review_status", "repair"}:
            errs.append("dependent_status payload needs exactly role, review_status, repair")
        elif not (_nonempty(p["review_status"]) and _nonempty(p["repair"])):
            errs.append("dependent_status payload fields must be nonempty strings")
        if ev["caused_by"] is None:
            errs.append("dependent_status requires caused_by")
        return
    keys = {"role", "defect", "replacement", "scope", "graph_version", "completeness", "dependents", "limits"}
    if set(p) != keys:
        errs.append(f"{role} payload must have exactly the keys {sorted(keys)}")
        return
    if not _nonempty(p["defect"]):
        errs.append("repair defect must be a nonempty string")
    if p["replacement"] is not None and not _nonempty(p["replacement"]):
        errs.append("repair replacement must be null or a nonempty string")
    if not isinstance(p["scope"], dict):
        errs.append("repair scope must be an object")
    gv = p["graph_version"]
    if not (isinstance(gv, int) and not isinstance(gv, bool) and gv >= 0):
        errs.append("repair graph_version must be a nonnegative integer")
    if p["completeness"] not in SCHEMA["completeness"]:
        errs.append(f"repair completeness must be one of {SCHEMA['completeness']}")
    if not (isinstance(p["dependents"], list) and all(_nonempty(x) for x in p["dependents"])):
        errs.append("repair dependents must be a list of nonempty strings")
    if not isinstance(p["limits"], list):
        errs.append("repair limits must be a list")
    if role == "follow_up" and ev["caused_by"] is None:
        errs.append("follow_up repair requires caused_by")



def _is_number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and x == x and abs(x) != float("inf")


def _check_constraint_payload(p, ev, errs):
    """pin: {constraint, position:[x,y,z]}; group and separate: {constraint, members:[>=2 ids
    including the subject]}; release: {constraint}, and it must supersede a constraint."""
    c = p.get("constraint")
    if c not in SCHEMA["constraints"]:
        errs.append(f"constraint must be one of {SCHEMA['constraints']}")
    elif c == "pin":
        pos = p.get("position")
        if set(p) != {"constraint", "position"} or not (
                isinstance(pos, list) and len(pos) == 3 and all(_is_number(v) for v in pos)):
            errs.append("pin payload must be {'constraint': 'pin', 'position': [x, y, z]}")
    elif c in ("group", "separate"):
        m = p.get("members")
        if set(p) != {"constraint", "members"} or not (
                isinstance(m, list) and len(m) >= 2 and all(_nonempty(x) for x in m)
                and len(set(m)) == len(m) and ev["subject"] in m):
            errs.append(f"{c} payload must be {{'constraint': '{c}', 'members': [two or more "
                        "distinct ids including the subject]}")
    else:  # release
        if set(p) != {"constraint"}:
            errs.append("release payload must be {'constraint': 'release'}")
        if ev["supersedes"] is None:
            errs.append("release requires supersedes (the constraint it removes)")


def validate(draft, flags=DEFAULT_FLAGS):
    """Validate a draft event and return its normalized form (without id).

    Raises ValidationError listing every reason the event is rejected.
    """
    if not isinstance(draft, dict):
        raise ValidationError(["event must be an object"])
    errs = []
    unknown = sorted(set(draft) - set(FIELDS))
    if unknown:
        errs.append(f"unknown field(s): {unknown}")
    for req in _REQUIRED:
        if req not in draft:
            errs.append(f"missing required field: {req}")
    if errs:
        raise ValidationError(errs)

    ev = {}
    for k in FIELDS:
        if k == "id":
            continue
        ev[k] = copy.deepcopy(draft[k]) if k in draft else copy.deepcopy(_DEFAULTS[k])
    if "id" in draft and draft["id"] != event_id(ev):
        errs.append("id does not match the canonical hash of the event")

    if not (isinstance(ev["t"], str) and _TS.match(ev["t"])):
        errs.append("t must be a UTC timestamp like 2026-10-18T09:00:00Z")

    actor = ev["actor"]
    if not (isinstance(actor, dict) and set(actor) == {"id", "type"}
            and _nonempty(actor["id"]) and actor["type"] in SCHEMA["actor_types"]):
        errs.append(f"actor needs a nonempty id and a type in {SCHEMA['actor_types']}")
        actor = {"id": "", "type": ""}

    kind = ev["kind"]
    if kind not in SCHEMA["kinds"]:
        errs.append(f"kind must be one of {SCHEMA['kinds']}")
    if ev["status"] not in SCHEMA["statuses"]:
        errs.append(f"status must be one of {SCHEMA['statuses']}")
    if kind not in SCHEMA["kinds"]:
        raise ValidationError(errs)

    if not _nonempty(ev["subject"]):
        errs.append("subject must be a nonempty string")

    if kind == "relate":
        if not _nonempty(ev["object"]):
            errs.append("relate requires an object")
        if ev["rel_type"] not in SCHEMA["rel_types"]:
            errs.append(f"rel_type must be one of {SCHEMA['rel_types']}")
        if not (isinstance(ev["channel"], str) and ev["channel"] in SCHEMA["channels"]):
            errs.append(f"a relation belongs to exactly one channel, one of {SCHEMA['channels']}")
    else:
        for k in ("object", "rel_type", "channel"):
            if ev[k] is not None:
                errs.append(f"{k} must be null for kind {kind}")

    _check_basis(ev["basis"], errs)
    if kind != "assert" and isinstance(ev["basis"], list) and not ev["basis"]:
        errs.append(f"kind {kind} requires a nonempty basis")

    for k in ("caused_by", "supersedes"):
        if ev[k] is not None and not _nonempty(ev[k]):
            errs.append(f"{k} must be null or a nonempty string")
    if kind == "unrelate" and ev["supersedes"] is None:
        errs.append("unrelate requires supersedes (the relation it withdraws)")

    if ev["git_ref"] is not None and not (isinstance(ev["git_ref"], str) and _GIT.match(ev["git_ref"])):
        errs.append("git_ref must be null or a lowercase hex commit hash")

    # Actors and status
    basis = ev["basis"] if isinstance(ev["basis"], list) else []
    if actor["type"] == "retriever":
        if kind != "relate":
            errs.append("a retriever may only nominate relations")
        if flags.enforce_retriever_provisional and ev["status"] != "provisional":
            errs.append("retriever output must enter as provisional")
        if not any(isinstance(b, dict) and "model" in b for b in basis):
            errs.append("a retriever event must record model id and version in its basis")
    if flags.enforce_unverified_marking and ev["status"] != "unverified":
        for b in basis:
            if isinstance(b, dict) and isinstance(b.get("external"), dict) \
                    and b["external"].get("verified") is False:
                errs.append("an event citing unchecked external material must have status unverified")
                break

    # Kind-specific payload
    p = ev["payload"]
    if not isinstance(p, dict):
        errs.append("payload must be an object")
    elif kind == "repair":
        _check_repair_payload(p, ev, errs)
    elif kind == "admit":
        if set(p) != {"requires"} or not (isinstance(p["requires"], list)
                                          and all(_nonempty(x) for x in p["requires"])):
            errs.append("admit payload must be {'requires': [claim ids]}")
    elif kind == "constrain":
        _check_constraint_payload(p, ev, errs)
    elif kind == "defeat":
        if p and not (set(p) == {"target_event"} and _nonempty(p["target_event"])):
            errs.append("defeat payload may only contain target_event")
    elif p:
        errs.append(f"payload must be empty for kind {kind}")

    if errs:
        raise ValidationError(errs)
    return ev
