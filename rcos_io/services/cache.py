"""Handles connecting to the Redis cache."""
import redis

from rcos_io.settings import REDISHOST, REDISPORT, REDISPASSWORD

CLIENT = None
if REDISPASSWORD == "default":
    CLIENT = redis.Redis(host=REDISHOST, port=REDISPORT, db=0)
else:
    CLIENT = redis.StrictRedis(
        host=REDISHOST, port=REDISPORT, db=0, password=REDISPASSWORD
    )


def get_cache():
    """Returns an instance of the Redis client."""
    return CLIENT
