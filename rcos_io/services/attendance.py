import datetime
import random
import string
from types import Tuple
from dataclasses import dataclass

ATTENDANCE_CODE_LENGTH = 6

#
#   TODO: replace this with something good and thread-safe
#
rooms = {}
to_be_verified = set()


@dataclass
class AttendanceSession:
    room: str
    verification_percent: float
    opened_at: datetime.datetime


def generate_code(code_length: int = ATTENDANCE_CODE_LENGTH):
    code = ""

    for _ in range(code_length):
        code += random.choice(string.ascii_uppercase)

    return code


def register_room() -> str:
    """
    Registers a new attendance room.
    """
    code = generate_code()
    rooms[code] = AttendanceSession("null", 0.2, datetime.datetime.now())

    print(rooms)

    return code


def close_room(id):
    """
    Closes a room for attendance.
    """
    rooms.pop(id)


def validate_code(code, id) -> Tuple[bool, bool]:
    """
    Attempt to verify if an attendance code is correct. Randomly selects some
    users to be manually verified based on a per-room percentage.

    Returns a tuple of booleans; the first of which is if the verification was successful,
    while the second is whether or not they were chosen to be manually verified.
    """
    room = rooms.get(code)

    # invalid code; there does not exist a room with that code
    if room == None:
        return (False, False)

    # in case the user tries to resubmit, return the same result
    if id in to_be_verified:
        return (True, True)

    # the user has the correct code, however they were selected to be manually verified
    if random.random() <= room.verification_percent:
        to_be_verified.add(id)

        return (True, True)

    # TODO: add attendane to database

    return (True, False)


def verify_user(id):
    """
    Remvoe a user from the verification queue.
    """
    to_be_verified.discard(id)
