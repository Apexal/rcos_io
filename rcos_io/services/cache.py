import redis

from rcos_io.settings import REDISHOST, REDISPORT, REDISPASSWORD

r = None
if REDISPASSWORD == "default":
    r = redis.Redis(host=REDISHOST, port=REDISPORT, db=0)
else:
    r = redis.StrictRedis(host=REDISHOST, port=REDISPORT, db=0, password=REDISPASSWORD)


def get_cache():
    return r
