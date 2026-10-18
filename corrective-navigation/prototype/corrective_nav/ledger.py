"""M1 (part): the append-only event ledger.

The ledger is a newline-delimited JSON file in canonical form. Each event is
identified by the SHA-256 of its canonical form without the id. It is the only
authoritative store; everything else is derived and disposable.
"""

import json
import os
from pathlib import Path

from .flags import DEFAULT_FLAGS
from .schema import ValidationError, canonical, event_id, validate


class LedgerError(Exception):
    pass


class Ledger:
    def __init__(self, path, flags=DEFAULT_FLAGS):
        self.path = Path(path)
        self.flags = flags
        self._events = []
        self._index = {}
        self._superseded = {}
        if self.path.exists():
            self._load()
        else:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.touch()

    # -- reading -----------------------------------------------------------
    def __len__(self):
        return len(self._events)

    def events(self, version=None):
        """The first `version` events (the ledger at version v), or all of them."""
        if version is None:
            return list(self._events)
        if not 0 <= version <= len(self._events):
            raise LedgerError(f"version {version} out of range 0..{len(self._events)}")
        return list(self._events[:version])

    def get(self, ident):
        return self._index[ident]

    def has(self, ident):
        return ident in self._index

    def resolve(self, prefix):
        """Resolve a unique event-id prefix (at least 6 characters) to a full id."""
        if len(prefix) < 6:
            raise LedgerError("event reference too short: use at least 6 characters")
        matches = [i for i in self._index if i.startswith(prefix)]
        if not matches:
            raise LedgerError(f"no event with reference {prefix!r}")
        if len(matches) > 1:
            raise LedgerError(f"reference {prefix!r} is ambiguous ({len(matches)} events)")
        return matches[0]

    # -- writing -----------------------------------------------------------
    def append(self, draft):
        """Validate, hash and append an event. Returns the stored event."""
        ev = validate(draft, self.flags)
        ev["id"] = event_id(ev)
        self._check_references(ev)
        line = canonical(ev)
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        self._accept(ev)
        return ev

    # -- internals ---------------------------------------------------------
    def _check_references(self, ev):
        if ev["id"] in self._index:
            raise LedgerError(f"duplicate event {ev['id']}")
        refs = [b["event"] for b in ev["basis"] if "event" in b]
        for k in ("caused_by", "supersedes"):
            if ev[k] is not None:
                refs.append(ev[k])
        for r in refs:
            if r not in self._index:
                raise LedgerError(f"reference to unknown earlier event {r}")
        target = ev["supersedes"]
        if target is not None:
            if target in self._superseded:
                raise LedgerError(f"event {target} is already superseded by {self._superseded[target]}")
            if ev["kind"] == "unrelate" and self._index[target]["kind"] != "relate":
                raise LedgerError("unrelate must target a relate event")
            if ev["kind"] == "constrain" and ev["payload"].get("constraint") == "release" \
                    and self._index[target]["kind"] != "constrain":
                raise LedgerError("release must target a constrain event")

    def _accept(self, ev):
        self._events.append(ev)
        self._index[ev["id"]] = ev
        if ev["supersedes"] is not None:
            self._superseded[ev["supersedes"]] = ev["id"]

    def _load(self):
        text = self.path.read_text(encoding="utf-8")
        for n, line in enumerate(text.splitlines(), start=1):
            if not line.strip():
                raise LedgerError(f"line {n}: blank line in ledger")
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise LedgerError(f"line {n}: not valid JSON ({exc})") from exc
            try:
                ev = validate(obj, self.flags)
            except ValidationError as exc:
                raise LedgerError(f"line {n}: {exc}") from exc
            ev["id"] = event_id(ev)
            if obj.get("id") != ev["id"]:
                raise LedgerError(f"line {n}: stored id does not match content (tampered or corrupt)")
            if canonical(obj) != line:
                raise LedgerError(f"line {n}: not in canonical form")
            self._check_references(ev)
            self._accept(ev)
