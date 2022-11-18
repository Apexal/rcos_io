"""
This modules initializes the connection to the Redis server
and exposes it through `get_cache()`.
"""
import redis

from rcos_io.services import settings

if settings.REDISPASSWORD == "default":
    redisdb = redis.Redis(host=settings.REDISHOST, port=int(settings.REDISPORT), db=0)
else:
    redisdb = redis.StrictRedis(
        host=settings.REDISHOST,
        port=int(settings.REDISPORT),
        db=0,
        password=settings.REDISPASSWORD,
    )


def get_cache():
    """Returns an instance of the Redis client."""
    return redisdb
