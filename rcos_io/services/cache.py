import redis

r = redis.Redis(host="127.0.0.1", port=6379)


def get_cache():
    return r
