"""
The attendance module handles the core attendance behavior such as verification,
code generation, and room creation.
"""

import random
import string
import json
import dataclasses
import datetime

from dataclasses import dataclass
from typing import Any, Dict, Optional, cast
from rcos_io.services import cache

ATTENDANCE_CODE_LENGTH = 6
EXPIRATION_MINUTES = 30


@dataclass
class AttendanceSession:
    """
    Represents an attendance session that's stored within the cache; room_code => session
    """

    room_id: str
    meeting_id: str
    small_group_id: str
    verification_percent: float
    opened_at: float


def generate_code(code_length: int = ATTENDANCE_CODE_LENGTH):
    """
    Generates & returns a new attendance code.
    """

    code = ""

    for _ in range(code_length):
        code += random.choice(string.ascii_uppercase)

    return code


def register_room(
    room_id: str, meeting_id: str, small_group_id: str = "default"
) -> str:
    """
    Registers a new attendance room.
    """
    code = generate_code()

    session = AttendanceSession(
        room_id,
        meeting_id,
        small_group_id,
        min(random.random(), 0.3),
        datetime.datetime.now().timestamp(),
    )

    # code => attendance session
    cache.get_cache().set(code, json.dumps(dataclasses.asdict(session)))
    cache.get_cache().expire(code, 60 * EXPIRATION_MINUTES)

    # {meeting_id}:{small_group_id} => code
    key = f"{meeting_id}:{small_group_id}"
    print("creating " + key)
    cache.get_cache().set(key, code)
    cache.get_cache().expire(key, 60 * EXPIRATION_MINUTES)

    return code


def close_room(code: str):
    """
    Closes a room for attendance.
    """
    room = get_room(code)

    # room is already closed, just ignore it
    if room is None:
        return

    cache.get_cache().delete(code)
    cache.get_cache().delete(f"{room['meeting_id']}:{room['small_group_id']}")


def get_room(code: str):
    """
    Fetches a room from the cache.
    """
    room: Optional[bytes] = cache.get_cache().get(code)

    if room is None:
        return None

    return cast(Dict[str, Any], json.loads(room))


def get_code_for_room(meeting_id: str, small_group_id: str):
    """Get the attendance code for a room."""
    code: Optional[bytes] = cache.get_cache().get(f"{meeting_id}:{small_group_id}")
    if code is None:
        return None

    return code.decode("utf-8")


def room_exists(meeting_id: str, small_group_id: str) -> bool:
    """Checks if there is an open attendance session for that meeting & small group room"""
    key = f"{meeting_id}:{small_group_id}"
    print("looking for " + key)
    room: Optional[bytes] = cache.get_cache().get(key)
    print("got ", room)
    return room is not None


def validate_code(code: str, user_id: str):
    """
    Attempt to verify if an attendance code is correct. Randomly selects some
    users to be manually verified based on a per-room percentage.

    Returns a tuple of booleans; the first of which is if the verification was successful,
    while the second is whether or not they were chosen to be manually verified.
    """
    attendance_session: Optional[bytes] = cache.get_cache().get(code)

    if attendance_session is None:
        return False, False

    room = json.loads(attendance_session)

    # invalid code; there does not exist a room with that code
    if room is None:
        return False, False

    # in case the user tries to resubmit, return the same result
    if cache.get_cache().sismember("to_be_verified", user_id):
        return True, True

    # the user has the correct code, however they were selected to be manually verified
    if random.random() <= room["verification_percent"]:
        cache.get_cache().sadd("to_be_verified", user_id)

        return True, True

    return True, False


def verify_user(user_id: str):
    """
    Remove a user from the verification queue. Returns if
    the operation was successful; True indicates the user
    was removed while False indicates that the user did
    not exist.
    """
    if not cache.get_cache().sismember("to_be_verified", user_id):
        return False

    cache.get_cache().srem("to_be_verified", user_id)

    return True
