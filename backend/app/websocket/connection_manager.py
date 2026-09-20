import asyncio
import json
import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set
from fastapi import WebSocket
from backend.app.core.redis import pubsub_manager
from backend.app.websocket.presence import UserPresence, get_user_color

logger = logging.getLogger("codeorbit.websocket")


class ConnectionManager:
    def __init__(self):
        # room_id -> Set[WebSocket]
        self.active_rooms: Dict[str, Set[WebSocket]] = defaultdict(set)
        # ws -> (room_id, user_id)
        self.connection_meta: Dict[WebSocket, Dict[str, Any]] = {}
        # room_id -> user_id -> UserPresence
        self.room_presences: Dict[str, Dict[str, UserPresence]] = defaultdict(dict)

    async def connect(
        self,
        websocket: WebSocket,
        room_id: str,
        user_id: str,
        username: str,
        avatar_url: Optional[str] = None,
    ) -> UserPresence:
        await websocket.accept()
        self.active_rooms[room_id].add(websocket)

        presence = UserPresence(
            user_id=user_id,
            username=username,
            avatar_url=avatar_url,
            color=get_user_color(user_id),
            current_file=None,
            cursor=None,
            selection=None,
            is_online=True,
        )

        self.connection_meta[websocket] = {
            "room_id": room_id,
            "user_id": user_id,
            "username": username,
        }
        self.room_presences[room_id][user_id] = presence

        # Broadcast user joined to room
        await self.broadcast_json(
            room_id,
            {
                "type": "PRESENCE_JOINED",
                "presence": presence.to_dict(),
                "all_presences": [p.to_dict() for p in self.room_presences[room_id].values()],
            },
        )

        return presence

    async def disconnect(self, websocket: WebSocket) -> None:
        meta = self.connection_meta.pop(websocket, None)
        if not meta:
            return

        room_id = meta["room_id"]
        user_id = meta["user_id"]

        if websocket in self.active_rooms[room_id]:
            self.active_rooms[room_id].remove(websocket)
            if not self.active_rooms[room_id]:
                del self.active_rooms[room_id]

        # Check if user has other open tabs in the same room
        still_connected = any(
            m.get("user_id") == user_id and m.get("room_id") == room_id
            for m in self.connection_meta.values()
        )

        if not still_connected and room_id in self.room_presences:
            self.room_presences[room_id].pop(user_id, None)
            await self.broadcast_json(
                room_id,
                {
                    "type": "PRESENCE_LEFT",
                    "user_id": user_id,
                    "all_presences": [p.to_dict() for p in self.room_presences[room_id].values()],
                },
            )

    async def update_presence(
        self,
        room_id: str,
        user_id: str,
        current_file: Optional[str] = None,
        cursor: Optional[Dict] = None,
        selection: Optional[Dict] = None,
    ) -> None:
        if room_id in self.room_presences and user_id in self.room_presences[room_id]:
            presence = self.room_presences[room_id][user_id]
            if current_file is not None:
                presence.current_file = current_file
            if cursor is not None:
                presence.cursor = cursor
            if selection is not None:
                presence.selection = selection

            await self.broadcast_json(
                room_id,
                {
                    "type": "PRESENCE_UPDATE",
                    "presence": presence.to_dict(),
                },
                exclude_user_id=user_id,
            )

    async def broadcast_bytes(self, room_id: str, data: bytes, exclude_ws: Optional[WebSocket] = None) -> None:
        """Broadcast raw binary data (e.g. Yjs CRDT delta) to all connected clients in the room."""
        if room_id not in self.active_rooms:
            return

        to_remove = []
        for connection in list(self.active_rooms[room_id]):
            if connection != exclude_ws:
                try:
                    await connection.send_bytes(data)
                except Exception:
                    to_remove.append(connection)

        for stale in to_remove:
            await self.disconnect(stale)

    async def broadcast_json(
        self,
        room_id: str,
        data: Dict[str, Any],
        exclude_user_id: Optional[str] = None,
        exclude_ws: Optional[WebSocket] = None,
    ) -> None:
        if room_id not in self.active_rooms:
            return

        to_remove = []
        for connection in list(self.active_rooms[room_id]):
            if connection == exclude_ws:
                continue
            meta = self.connection_meta.get(connection)
            if exclude_user_id and meta and meta.get("user_id") == exclude_user_id:
                continue

            try:
                await connection.send_json(data)
            except Exception:
                to_remove.append(connection)

        for stale in to_remove:
            await self.disconnect(stale)


connection_manager = ConnectionManager()
