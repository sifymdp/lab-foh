"""
Central ID generation.
All models use uuid4 strings — never millisecond timestamps,
which collide under concurrent load.
"""
import uuid


def new_id() -> str:
    return str(uuid.uuid4())
