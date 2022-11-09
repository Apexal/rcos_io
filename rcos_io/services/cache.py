"""
This modules initializes the connection to the Redis server
and exposes it through `get_cache()`.
"""
import redis

from rcos_io.services import settings

CLIENT = None
if settings.REDISPASSWORD == "default":
    CLIENT = redis.Redis(host=settings.REDISHOST, port=settings.REDISPORT, db=0)
else:
    CLIENT = redis.StrictRedis(
        host=settings.REDISHOST,
        port=settings.REDISPORT,
        db=0,
        password=settings.REDISPASSWORD,
    )


def get_cache():
    """Returns an instance of the Redis client."""
    return CLIENT
