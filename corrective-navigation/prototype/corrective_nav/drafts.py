"""Convenience constructors for draft events. They only build dictionaries;
validation and hashing happen in the ledger."""


def actor(ident, type_="human"):
    return {"id": ident, "type": type_}


def evidence(text):
    return {"evidence": text}


def event_ref(event_id):
    return {"event": event_id}


def external(citation, verified=False):
    return {"external": {"citation": citation, "verified": verified}}


def model(model_id, version):
    return {"model": {"id": model_id, "version": version}}


def _draft(kind, t, who, subject, status, basis=None, **extra):
    d = {"t": t, "actor": who, "kind": kind, "subject": subject,
         "status": status, "basis": list(basis or [])}
    d.update(extra)
    return d


def assertion(subject, who, t, status="established", basis=None, git_ref=None):
    return _draft("assert", t, who, subject, status, basis, git_ref=git_ref)


def relation(subject, object_, rel_type, channel, who, t, basis,
             status="established", caused_by=None, supersedes=None):
    return _draft("relate", t, who, subject, status, basis, object=object_,
                  rel_type=rel_type, channel=channel, caused_by=caused_by,
                  supersedes=supersedes)


def unrelation(relation_event, who, t, basis, status="established"):
    """Withdraw a relation by superseding it."""
    return _draft("unrelate", t, who, relation_event["subject"], status, basis,
                  supersedes=relation_event["id"])


def support(claim, who, t, basis, status="established"):
    return _draft("support", t, who, claim, status, basis)


def defeat(claim, who, t, basis, target_event=None, status="established"):
    payload = {"target_event": target_event} if target_event else {}
    return _draft("defeat", t, who, claim, status, basis, payload=payload)


def admit(continuation, requires, who, t, basis, status="established"):
    return _draft("admit", t, who, continuation, status, basis,
                  payload={"requires": list(requires)})


def nomination(subject, object_, rel_type, channel, retriever, model_id, model_version, t):
    """A retriever nominating a candidate relation: always provisional."""
    return relation(subject, object_, rel_type, channel, retriever, t,
                    basis=[model(model_id, model_version)], status="provisional")


def _constrain(subject, who, t, basis, payload, status="established", supersedes=None):
    return _draft("constrain", t, who, subject, status, basis, payload=payload,
                  supersedes=supersedes)


def pin(node, position, who, t, basis):
    return _constrain(node, who, t, basis, {"constraint": "pin", "position": list(position)})


def group(members, who, t, basis):
    return _constrain(members[0], who, t, basis, {"constraint": "group", "members": list(members)})


def separate(members, who, t, basis):
    return _constrain(members[0], who, t, basis,
                      {"constraint": "separate", "members": list(members)})


def release(constraint_event, who, t, basis):
    """Remove a constraint by superseding it."""
    return _constrain(constraint_event["subject"], who, t, basis, {"constraint": "release"},
                      supersedes=constraint_event["id"])
