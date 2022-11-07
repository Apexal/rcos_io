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


def register_room(room_id: str, meeting_id: str) -> str:
    """
    Registers a new attendance room.
    """
    code = generate_code()

    session = AttendanceSession(
        room_id,
        meeting_id,
        min(random.random(), 0.2),
        datetime.datetime.now().timestamp(),
    )

    cache.get_cache().set(code, json.dumps(dataclasses.asdict(session)))
    cache.get_cache().expire(code, 60 * EXPIRATION_MINUTES)

    return code


def close_room(code: str):
    """
    Closes a room for attendance.
    """
    cache.get_cache().delete(code)


def get_room(code: str):
    """
    Fetches a room from the cache.
    """
    room = cache.get_cache().get(code)

    if room is None:
        return None

    return json.loads(room)


def validate_code(code: str, user_id: str):
    """
    Attempt to verify if an attendance code is correct. Randomly selects some
    users to be manually verified based on a per-room percentage.

    Returns a tuple of booleans; the first of which is if the verification was successful,
    while the second is whether or not they were chosen to be manually verified.
    """
    attendance_session = cache.get_cache().get(code)

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
