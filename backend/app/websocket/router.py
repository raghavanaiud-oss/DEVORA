import json
import logging
import uuid
from typing import Optional
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from backend.app.core.security import decode_token
from backend.app.websocket.connection_manager import connection_manager

logger = logging.getLogger("codeorbit.websocket")

router = APIRouter()


@router.websocket("/ws/projects/{project_id}")
async def project_collaboration_websocket(
    websocket: WebSocket,
    project_id: uuid.UUID,
    token: Optional[str] = Query(None),
    username: Optional[str] = Query(None),
):
    """
    WebSocket endpoint for real-time collaborative editing and developer presence.
    Supports:
    - Cursor and selection tracking
    - Live active user presences and color assignments
    - Binary Yjs CRDT delta synchronization
    - Real-time project chat and activity broadcasting
    """
    user_id = str(uuid.uuid4())
    display_name = username or f"Developer-{user_id[:4]}"
    avatar_url = None

    if token:
        payload = decode_token(token)
        if payload and payload.get("type") == "access":
            user_id = payload.get("sub", user_id)
            if not username:
                display_name = payload.get("username", display_name)

    room_id = str(project_id)

    # Establish connection and broadcast presence
    await connection_manager.connect(
        websocket=websocket,
        room_id=room_id,
        user_id=user_id,
        username=display_name,
        avatar_url=avatar_url,
    )

    try:
        while True:
            # Handle both text (JSON presence/events) and binary (Yjs CRDT deltas)
            message = await websocket.receive()

            if "bytes" in message and message["bytes"] is not None:
                # Raw binary Yjs CRDT update
                raw_bytes = message["bytes"]
                await connection_manager.broadcast_bytes(
                    room_id=room_id,
                    data=raw_bytes,
                    exclude_ws=websocket,
                )
            elif "text" in message and message["text"] is not None:
                text_data = message["text"]
                try:
                    data = json.loads(text_data)
                    msg_type = data.get("type")

                    if msg_type == "CURSOR_MOVE":
                        await connection_manager.update_presence(
                            room_id=room_id,
                            user_id=user_id,
                            cursor=data.get("cursor"),
                            current_file=data.get("current_file"),
                        )
                    elif msg_type == "SELECTION_CHANGE":
                        await connection_manager.update_presence(
                            room_id=room_id,
                            user_id=user_id,
                            selection=data.get("selection"),
                        )
                    elif msg_type == "FILE_OPEN":
                        await connection_manager.update_presence(
                            room_id=room_id,
                            user_id=user_id,
                            current_file=data.get("current_file"),
                        )
                    elif msg_type == "CHAT_MESSAGE":
                        data["sender_id"] = user_id
                        data["sender_name"] = display_name
                        await connection_manager.broadcast_json(
                            room_id=room_id,
                            data=data,
                        )
                    else:
                        # Forward general broadcast event
                        await connection_manager.broadcast_json(
                            room_id=room_id,
                            data=data,
                            exclude_ws=websocket,
                        )
                except json.JSONDecodeError:
                    logger.warning("Received non-JSON text message on WebSocket: %s", text_data)
    except WebSocketDisconnect:
        await connection_manager.disconnect(websocket)
    except Exception as exc:
        logger.exception("Unexpected error in WebSocket connection: %s", exc)
        await connection_manager.disconnect(websocket)
