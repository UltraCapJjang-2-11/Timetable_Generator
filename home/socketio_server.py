import asyncio
import logging
from typing import Dict, Set, DefaultDict
from collections import defaultdict

import socketio

# Async Socket.IO server (ASGI)
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    logger=False,
    engineio_logger=False,
)

# Track user identity per socket id
sid_to_user: Dict[str, Dict] = {}
# Track rooms joined per socket id
sid_to_rooms: DefaultDict[str, Set[str]] = defaultdict(set)
# Track counts per room
room_user_counts: DefaultDict[str, int] = defaultdict(int)


async def _broadcast_user_count(room: str):
    count = room_user_counts.get(room, 0)
    await sio.emit("user_count", {"room": room, "count": count}, room=room)


@sio.event
async def connect(sid, environ, auth):
    # auth may contain user info if provided by client
    user = {}
    if isinstance(auth, dict):
        user = {
            "user_id": auth.get("user_id"),
            "username": auth.get("username") or "익명"
        }
    sid_to_user[sid] = user


@sio.event
async def identify(sid, data):
    # Optional explicit identification after connection
    if not isinstance(data, dict):
        return
    sid_to_user[sid] = {
        "user_id": data.get("user_id"),
        "username": data.get("username") or "익명",
    }


@sio.event
async def join_room(sid, data):
    if not isinstance(data, dict):
        return
    room = data.get("room")
    if not room:
        course_id = data.get("course_id")
        if course_id is None:
            return
        room = f"course_{course_id}"

    if room in sid_to_rooms[sid]:
        # already joined
        return

    await sio.enter_room(sid, room)
    sid_to_rooms[sid].add(room)
    room_user_counts[room] += 1
    await _broadcast_user_count(room)


@sio.event
async def leave_room(sid, data):
    if not isinstance(data, dict):
        return
    room = data.get("room")
    if not room:
        course_id = data.get("course_id")
        if course_id is None:
            return
        room = f"course_{course_id}"

    if room not in sid_to_rooms[sid]:
        return

    await sio.leave_room(sid, room)
    sid_to_rooms[sid].discard(room)
    room_user_counts[room] = max(0, room_user_counts.get(room, 0) - 1)
    await _broadcast_user_count(room)


@sio.event
async def chat_message(sid, data):
    if not isinstance(data, dict):
        return
    message = (data.get("message") or "").strip()
    if not message:
        return

    room = data.get("room")
    course_id = data.get("course_id")
    if not room:
        if course_id is None:
            return
        room = f"course_{course_id}"

    # Ensure the sender is in the room
    if room not in sid_to_rooms[sid]:
        await join_room(sid, {"room": room})

    user = sid_to_user.get(sid) or {}
    payload = {
        "room": room,
        "course_id": course_id,
        "message": message,
        "user_id": user.get("user_id"),
        "username": user.get("username") or "익명",
    }
    # Do not send the message back to the sender; clients render own message locally
    await sio.emit("chat_message", payload, room=room, skip_sid=sid)


@sio.event
async def disconnect(sid):
    # On disconnect, remove from all rooms and update counts
    rooms = list(sid_to_rooms.get(sid, set()))
    for room in rooms:
        try:
            await sio.leave_room(sid, room)
        except Exception:
            pass
        finally:
            room_user_counts[room] = max(0, room_user_counts.get(room, 0) - 1)
            await _broadcast_user_count(room)

    sid_to_rooms.pop(sid, None)
    sid_to_user.pop(sid, None)


# ASGI application to mount in project's ASGI
socketio_asgi_app = socketio.ASGIApp(sio) 