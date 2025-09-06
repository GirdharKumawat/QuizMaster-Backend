import random, string, datetime
from bson import ObjectId

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
    # Remove is_correct before sending to players
    q = quiz_doc.copy()
    for ques in q.get("questions", []):
        for opt in ques.get("options", []):
            opt.pop("is_correct", None)
    return q


