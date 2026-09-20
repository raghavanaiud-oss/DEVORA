"""
Yjs binary synchronization and awareness protocol definitions.
Compatible with standard y-websocket clients.
"""

MESSAGE_SYNC = 0
MESSAGE_AWARENESS = 1
MESSAGE_AUTH = 2
MESSAGE_QUERY_AWARENESS = 3

MESSAGE_YJS_SYNC_STEP_1 = 0
MESSAGE_YJS_SYNC_STEP_2 = 1
MESSAGE_YJS_UPDATE = 2


def create_sync_message(step: int, payload: bytes) -> bytes:
    """Pack a Yjs sync message."""
    return bytes([MESSAGE_SYNC, step]) + payload


def create_awareness_message(payload: bytes) -> bytes:
    """Pack a Yjs awareness update message."""
    return bytes([MESSAGE_AWARENESS]) + payload
