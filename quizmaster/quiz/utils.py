import random, string, datetime
from bson import ObjectId, errors

def oid(s: str) -> ObjectId:
    return ObjectId(s)

def strid(x) -> str:
    return str(x)

def now_utc():
    return datetime.datetime.utcnow()

def gen_join_code(n=6):
    alphabet = string.ascii_uppercase + string.digits
    return "".join(random.choice(alphabet) for _ in range(n))

def strip_correct_answers(quiz_doc):
    """Remove is_correct before sending to players to prevent cheating."""
    q = quiz_doc.copy()
    for ques in q.get("questions", []):
        for opt in ques.get("options", []):
            # Safe removal even if key doesn't exist
            if "is_correct" in opt:
                del opt["is_correct"]
    return q

def is_valid_object_id(oid):
    """Return True if oid is a valid ObjectId string."""
    if not oid:
        return False
    try:
        return ObjectId.is_valid(str(oid))
    except Exception:
        return False