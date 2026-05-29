import json
from bson import ObjectId
from datetime import datetime


class VitalertEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


def serialize_doc(doc):
    if doc is None:
        return None
    doc = dict(doc)
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            doc[k] = str(v)
        elif isinstance(v, list):
            doc[k] = [_serialize_value(i) for i in v]
    if "_id" in doc:
        doc["id"] = str(doc.pop("_id"))
    return doc


def _serialize_value(v):
    if isinstance(v, ObjectId):
        return str(v)
    if isinstance(v, dict):
        return {k: _serialize_value(val) for k, val in v.items()}
    if isinstance(v, list):
        return [_serialize_value(i) for i in v]
    return v
