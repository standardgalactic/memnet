"""M1: effective set and the derived graph index.

The graph is a SQLite database built from the effective events. It is
disposable: deleting it and rebuilding it from the ledger gives an identical
graph (same fingerprint). Nothing in it is authoritative, and it stores no
derived judgements (support status, admissibility, door state); those are
functions in status.py.
"""

import hashlib
import json
import os
import sqlite3

ALL = None  # pass as `statuses` to include every status

_SCHEMA_SQL = """
CREATE TABLE nodes(id TEXT PRIMARY KEY, asserted_event TEXT, status TEXT);
CREATE TABLE edges(event_id TEXT PRIMARY KEY, subject TEXT NOT NULL, object TEXT NOT NULL,
                   rel_type TEXT NOT NULL, channel TEXT NOT NULL, status TEXT NOT NULL,
                   actor_id TEXT NOT NULL, actor_type TEXT NOT NULL);
CREATE TABLE supports(event_id TEXT PRIMARY KEY, subject TEXT NOT NULL, status TEXT NOT NULL);
CREATE TABLE defeats(event_id TEXT PRIMARY KEY, subject TEXT NOT NULL, target_event TEXT,
                     status TEXT NOT NULL);
CREATE TABLE admits(event_id TEXT PRIMARY KEY, subject TEXT NOT NULL, status TEXT NOT NULL,
                    requires TEXT NOT NULL);
CREATE TABLE dependent_status(event_id TEXT PRIMARY KEY, subject TEXT NOT NULL,
                              review_status TEXT NOT NULL, repair_id TEXT NOT NULL,
                              status TEXT NOT NULL);
"""
_TABLES = ("nodes", "edges", "supports", "defeats", "admits", "dependent_status")
_ESTABLISHED_TABLES = ("edges", "supports", "defeats", "admits", "dependent_status")


def effective(events):
    """Eff(L_v): events not superseded by a later event, in ledger order."""
    superseded = {e["supersedes"] for e in events if e["supersedes"] is not None}
    return [e for e in events if e["id"] not in superseded]


class Graph:
    def __init__(self, conn, version):
        self.conn = conn
        self.version = version

    # -- construction ------------------------------------------------------
    @classmethod
    def from_events(cls, events, version=None, path=":memory:"):
        events = list(events)
        if version is None:
            version = len(events)
        if path != ":memory:" and os.path.exists(path):
            os.remove(path)  # the index is disposable
        conn = sqlite3.connect(path)
        conn.executescript(_SCHEMA_SQL)
        ensure = "INSERT OR IGNORE INTO nodes(id) VALUES(?)"
        for e in effective(events):
            k, p = e["kind"], e["payload"]
            if k == "assert":
                conn.execute(
                    "INSERT INTO nodes(id, asserted_event, status) VALUES(?,?,?) "
                    "ON CONFLICT(id) DO UPDATE SET asserted_event=excluded.asserted_event, "
                    "status=excluded.status", (e["subject"], e["id"], e["status"]))
            elif k == "relate":
                conn.execute(ensure, (e["subject"],))
                conn.execute(ensure, (e["object"],))
                conn.execute("INSERT INTO edges VALUES(?,?,?,?,?,?,?,?)",
                             (e["id"], e["subject"], e["object"], e["rel_type"], e["channel"],
                              e["status"], e["actor"]["id"], e["actor"]["type"]))
            elif k == "support":
                conn.execute(ensure, (e["subject"],))
                conn.execute("INSERT INTO supports VALUES(?,?,?)", (e["id"], e["subject"], e["status"]))
            elif k == "defeat":
                conn.execute(ensure, (e["subject"],))
                conn.execute("INSERT INTO defeats VALUES(?,?,?,?)",
                             (e["id"], e["subject"], p.get("target_event"), e["status"]))
            elif k == "admit":
                conn.execute(ensure, (e["subject"],))
                conn.execute("INSERT INTO admits VALUES(?,?,?,?)",
                             (e["id"], e["subject"], e["status"], json.dumps(sorted(p["requires"]))))
            elif k == "repair" and p.get("role") == "dependent_status":
                conn.execute(ensure, (e["subject"],))
                conn.execute("INSERT INTO dependent_status VALUES(?,?,?,?,?)",
                             (e["id"], e["subject"], p["review_status"], p["repair"], e["status"]))
            # unrelate: its only effect is the supersession already applied by effective().
            # constrain: belongs to the projection (M4), not the graph.
        conn.commit()
        return cls(conn, version)

    @classmethod
    def from_ledger(cls, ledger, version=None, path=":memory:"):
        if version is None:
            version = len(ledger)
        return cls.from_events(ledger.events(version), version, path)

    def close(self):
        self.conn.close()

    def __del__(self):
        try:
            self.conn.close()
        except Exception:
            pass

    # -- queries -----------------------------------------------------------
    def query(self, sql, params=()):
        return self.conn.execute(sql, params).fetchall()

    def node_ids(self):
        return [r[0] for r in self.query("SELECT id FROM nodes ORDER BY id")]

    def edges(self, channel=None, rel_type=None, statuses=("established",)):
        """Edges as dicts. By default only established ones; pass statuses=ALL for everything."""
        sql = ("SELECT event_id, subject, object, rel_type, channel, status, actor_id, actor_type "
               "FROM edges WHERE 1=1")
        params = []
        if channel is not None:
            sql += " AND channel=?"
            params.append(channel)
        if rel_type is not None:
            sql += " AND rel_type=?"
            params.append(rel_type)
        if statuses is not None:
            sql += " AND status IN (%s)" % ",".join("?" * len(statuses))
            params.extend(statuses)
        sql += " ORDER BY event_id"
        cols = ("event_id", "subject", "object", "rel_type", "channel", "status", "actor_id", "actor_type")
        return [dict(zip(cols, r)) for r in self.query(sql, params)]

    def columns(self, table):
        return [r[1] for r in self.query(f"PRAGMA table_info({table})")]

    # -- fingerprints ------------------------------------------------------
    def _dump(self, tables, established_only):
        out = {}
        for t in tables:
            n = len(self.columns(t))
            where = " WHERE status='established'" if established_only else ""
            order = ",".join(str(i + 1) for i in range(n))
            out[t] = self.query(f"SELECT * FROM {t}{where} ORDER BY {order}")
        return hashlib.sha256(json.dumps(out, sort_keys=True).encode("utf-8")).hexdigest()

    def fingerprint(self):
        """Hash of the entire derived graph; equal iff the graphs are identical."""
        return self._dump(_TABLES, False)

    def established_fingerprint(self):
        """Hash of the established view only (no provisional or unverified rows)."""
        return self._dump(_ESTABLISHED_TABLES, True)
