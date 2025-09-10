import asyncio
import logging
from typing import Dict, Set, DefaultDict
from collections import defaultdict

import socketio
from asgiref.sync import sync_to_async

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


async def _persist_chat_message(room: str, course_id, user_id, username: str, message: str):
    """메시지를 DB에 저장합니다. Django ORM은 동기이므로 sync_to_async로 래핑합니다."""
    try:
        # 지연 import (ASGI 초기화 순서 안전)
        from home.models import ChatMessage

        def _create():
            return ChatMessage.objects.create(
                room=room,
                course_id=course_id,
                user_id=user_id,
                username=username or '익명',
                message=message,
            )

        await sync_to_async(_create, thread_sensitive=True)()
    except Exception:
        logging.getLogger(__name__).exception("Failed to persist chat message")


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
    
    # Django User 모델에서 first_name, last_name 가져오기
    first_name = ''
    last_name = ''
    user_id = user.get("user_id")
    if user_id:
        from django.contrib.auth.models import User
        try:
            django_user = await sync_to_async(User.objects.get)(id=user_id)
            first_name = await sync_to_async(lambda: django_user.first_name)()
            last_name = await sync_to_async(lambda: django_user.last_name)()
        except User.DoesNotExist:
            pass
    
    payload = {
        "room": room,
        "course_id": course_id,
        "message": message,
        "user_id": user_id,
        "username": user.get("username") or "익명",
        "first_name": first_name,
        "last_name": last_name,
    }

    # 메시지 영속화 (course_id 미제공 시 room에서 파생)
    cid = course_id
    if cid is None and isinstance(room, str) and room.startswith("course_"):
        try:
            cid = int(room.split("_", 1)[1])
        except Exception:
            cid = None
    await _persist_chat_message(
        room=room,
        course_id=cid,
        user_id=user.get("user_id"),
        username=user.get("username") or "익명",
        message=message,
    )

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