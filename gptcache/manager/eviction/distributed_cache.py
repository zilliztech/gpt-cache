# pylint: disable=wrong-import-position
from abc import ABC, abstractmethod
from typing import List

from gptcache.utils import import_redis
from gptcache.manager.eviction.base import EvictionBase

import_redis()
import redis
from redis_om import get_redis_connection


class DistributedEviction(EvictionBase, ABC):
    """
    Base class for Distributed Eviction Strategy.
    """

    @abstractmethod
    def put(self, objs: List[str]):
        pass

    @abstractmethod
    def get(self, obj: str):
        pass

    @property
    @abstractmethod
    def policy(self) -> str:
        pass


class RedisCacheEviction(DistributedEviction, ABC):
    """eviction: Distributed Cache Eviction Strategy using Redis.

    :param host: the host of redis
    :type host: str
    :param port: the port of redis
    :type port: int
    :param policy: eviction strategy policy of redis such as allkeys-lru, volatile-lru, allkeys-random, volatile-random, etc.
    refer https://redis.io/docs/reference/eviction/ for more information.
    :type policy: str
    :param maxsize: the maxsize of cache data
    :type maxsize: int
    :param on_evict: the function for cleaning the data in the store
    :type  on_evict: Callable[[List[Any]], None]
    :param maxmemory: the maxmemory of redis
    :type maxmemory: str
    :param global_key_prefix: the global key prefix
    :type global_key_prefix: str
    :param kwargs: the kwargs
    :type kwargs: Any
    :param ttl: the ttl of the cache data
    :type ttl: int
    """

    def __init__(self,
                 host="localhost",
                 port=6379,
                 maxmemory: str = None,
                 policy: str = None,
                 global_key_prefix="gptcache",
                 ttl: int = None,
                 **kwargs):
        self._redis = get_redis_connection(host=host, port=port, **kwargs)
        if maxmemory:
            self._redis.config_set("maxmemory", maxmemory)
        if policy:
            self._redis.config_set("maxmemory-policy", policy)
            self._policy = policy.lower()
        self._global_key_prefix = global_key_prefix
        self._ttl = ttl

    def _create_key(self, key: str) -> str:
        return f"{self._global_key_prefix}:evict:{key}"

    def put(self, objs: List[str], expire=False):
        ttl = self._ttl if expire else None
        for key in objs:
            self._redis.set(self._create_key(key), "True", ex=ttl)

    def get(self, obj: str):

        try:
            value = self._redis.get(self._create_key(obj))
            # update key expire time when accessed
            if self._ttl:
                self._redis.expire(self._create_key(obj), self._ttl)
            return value
        except redis.RedisError:
            print(f"Error getting key {obj} from cache")
            return None

    @property
    def policy(self) -> str:
        return self._policy


class NoOpEviction(EvictionBase):
    """eviction: No Op Eviction Strategy. This is used when Eviction is managed internally
    by the Databases such as Redis or memcached and no eviction is required to perform.

    """

    @property
    def policy(self) -> str:
        return ""

    def __init__(self, **kwargs):
        pass

    def put(self, objs: List[str]):
        pass

    def get(self, obj: str):
        pass
