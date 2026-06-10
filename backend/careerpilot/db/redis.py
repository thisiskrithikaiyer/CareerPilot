from functools import lru_cache
import redis
from careerpilot.config import REDIS_URL


@lru_cache(maxsize=1)
def get_redis() -> redis.Redis:
    return redis.from_url(REDIS_URL, decode_responses=True)
