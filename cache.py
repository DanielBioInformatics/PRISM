import hashlib
import json
import logging
from functools import wraps

import redis

from config import Config

r = redis.Redis.from_url(Config.REDIS_URL, decode_responses=True)


def cached_analysis(ttl=86400):
    def decorator(func):
        @wraps(func)
        def wrapper(sequence, pdb_id="", *args, **kwargs):
            raw = f"{sequence}::{pdb_id}"
            key = f"analysis:{hashlib.sha256(raw.encode()).hexdigest()}"
            try:
                cached = r.get(key)
                if cached is not None:
                    return json.loads(cached)
            except redis.RedisError as e:
                logging.warning("Redis unavailable, falling through: %s", e)

            result = func(sequence, *args, **kwargs)

            if "error" not in result:
                try:
                    r.setex(key, ttl, json.dumps(result))
                except redis.RedisError as e:
                    logging.warning("Redis write failed: %s", e)

            return result
        return wrapper
    return decorator
