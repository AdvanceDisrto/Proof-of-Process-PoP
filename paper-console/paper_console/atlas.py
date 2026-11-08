"""Offline atlas ingestion with explicit provenance; never upgrades dataset facts to theorem."""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path
from .codec import Event, canonical


class AtlasDataError(ValueError): pass


def ingest_atlas(path, *, max_entities=50000):
    src=Path(path)
    raw=src.read_bytes()
    if len(raw) > 10*1024*1024:raise AtlasDataError("source dataset too large")
    doc=json.loads(raw)
    if type(doc)!=dict or set(doc)!={"provenance","entities"}:
        raise AtlasDataError("expected provenance and entities")
    provenance=doc["provenance"]
    if type(provenance)!=dict or any(not provenance.get(k) for k in ("url","license","retrieved_at","source_title")):
        raise AtlasDataError("source URL/license/date are required")
    rows=doc["entities"]
    if type(rows)!=list or not 1<=len(rows)<=max_entities:
        raise AtlasDataError("too many or no entities")
    seen=set();out=[]
    for row in rows:
        if type(row)!=dict or set(row)!={"id","kind","name","attributes","as_of"}:
            raise AtlasDataError("invalid entity shape")
        eid=row["id"]
        if type(eid)!=str or not re.fullmatch(r"[A-Z0-9_]{2,60}",eid) or eid in seen:
            raise AtlasDataError("invalid or duplicate entity ID")
        seen.add(eid)
        if row["kind"] not in ("STATE","COUNTRY","CAPITAL","LANGUAGE","STATISTIC","TRANSIT"):
            raise AtlasDataError("unsupported entity kind")
        if type(row["name"])!=str or not 1<=len(row["name"])<=120:
            raise AtlasDataError("invalid name")
        if type(row["attributes"])!=dict or len(canonical(row["attributes"]))>2000:
            raise AtlasDataError("invalid attributes")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(row["as_of"])):
            raise AtlasDataError("as_of date required")
        out.append({**row,"entry_sha256":hashlib.sha256(canonical(row)).hexdigest(),
                    "source_tier":"DATASET_UNVERIFIED"})
    return {"schema":"atlas/ingested-unverified/v1","source_sha256":hashlib.sha256(raw).hexdigest(),
            "provenance":provenance,"count":len(out),"entities":out,
            "what_it_proves":"record hashes and exact downloaded file bytes only",
            "does_not_prove":["source fact accuracy","freshness of offline atlas","real geography","physical routing"]}


def atlas_event(entity,source_sha256,now):
    return Event(event_id="atlas-"+entity["entry_sha256"][:32], occurred_at=now,
        track="atlas",subject=entity["id"]+":"+entity["name"],
        claim_verdict="UNRESOLVED",verification="NOT_CHECKED",
        details={"source_sha256":source_sha256,"kind":entity["kind"],
                 "attributes":entity["attributes"],"data_as_of":entity["as_of"]},
        source_tier="DATASET_UNVERIFIED",source_ref=entity["entry_sha256"])


def cable_transit_observation(*,origin,destination,declared_route=None,measured_latency_ms=None,source_id=None):
    """No submarine cable may be inferred from endpoint location or traceroute."""
    if not (isinstance(origin,str) and isinstance(destination,str) and origin and destination):
        raise AtlasDataError("known origin/destination labels required")
    if measured_latency_ms is not None and (type(measured_latency_ms) not in (int,float) or not 0<=measured_latency_ms<1e7):
        raise AtlasDataError("invalid claimed latency")
    return {"origin":origin,"destination":destination,
            "cable_route_status":"UNOBSERVED" if not source_id else "THIRD_PARTY_CLAIM_UNVERIFIED",
            "declared_cable":declared_route,"latency_ms_operator_supplied":measured_latency_ms,
            "route_evidence_identifier":source_id,
            "does_not_prove":["actual optical path","submarine cable traversal","witness independence"]}
