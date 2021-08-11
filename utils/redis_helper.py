from utils.redis_client import RedisClient
from utils.redis_serializers import DjangoModelSerializer
from django.conf import settings

class RedisHelper:

    @classmethod
    def _load_objects_to_cache(cls, key, objects):
        conn = RedisClient.get_connection()
        serialized_list = []

        for obj in objects:
            serialized_data = DjangoModelSerializer.serialize(obj)
            serialized_list.append(serialized_data)
        if serialized_list:
            conn.rpush(key, *serialized_list)
            conn.expire(key, settings.REDIS_KEY_EXPIRE_TIME)

    @classmethod
    def load_objects(cls, key, queryset):
        # 最多只 cache REDIS_LIST_LENGTH_LIMIT 个 objects
        # 超过这个限制的 objects 就去数据库里面读取。一般这个限制会比较大，比如200
        # 因此翻页翻到 200 的用户访问量会比较少，从数据库读取也不是大问题
        queryset = queryset[:settings.REDIS_LIST_LENGTH_LIMIT]
        conn = RedisClient.get_connection()

        # 如果在cache里存在，则直接拿出来，然后返回
        if conn.exists(key):
            # cache hit
            serialized_list = conn.lrange(key, 0, -1)
            objects = []
            for serialized_data in serialized_list:
                deserialized_object = DjangoModelSerializer.deserialize(serialized_data)
                objects.append(deserialized_object)
            return objects

        # cache miss
        cls._load_objects_to_cache(key, queryset)

        # 转换为list的原因是保持返回类型的统一，因为存在redis里的数据是list的形式
        return list(queryset)

    @classmethod
    def push_object(cls, key, obj, queryset):
        queryset = queryset[:settings.REDIS_LIST_LENGTH_LIMIT]
        conn = RedisClient.get_connection()
        if not conn.exists(key):
            # 如果key不存在，直接从数据库里面load
            # 就不走单个push的方式加到cache里面了
            cls._load_objects_to_cache(key, queryset)
            return
        serialized_data = DjangoModelSerializer.serialize(obj)
        conn.lpush(key, serialized_data)
        conn.ltrim(key, 0, settings.REDIS_LIST_LENGTH_LIMIT - 1)

    @classmethod
    def get_count_key(cls, obj, attr):
        return '{}.{}:{}'.format(obj.__class__.__name__, attr, obj.id)

    @classmethod
    def incr_count(cls, obj, attr):
        conn = RedisClient.get_connection()
        key = cls.get_count_key(obj, attr)
        # return conn.incr(key)
        if conn.exists(key):
            return conn.incr(key)
        # back fill cache from db
        # 不执行+1操作，因为必须保证调用incr_count之前obj.attr已经+1过了
        obj.refresh_from_db()
        conn.set(key, getattr(obj, attr))
        conn.expire(key, settings.REDIS_KEY_EXPIRE_TIME)
        return getattr(obj, attr)


    @classmethod
    def decr_count(cls, obj, attr):
        conn = RedisClient.get_connection()
        key = cls.get_count_key(obj, attr)
        # return conn.decr(key)
        if conn.exists(key):
            return conn.decr(key)
        # back fill cache from db
        # 不执行-1操作，因为必须保证调用decr_count之前obj.attr已经-1过了
        obj.refresh_from_db()
        conn.set(key, getattr(obj, attr))
        conn.expire(key, settings.REDIS_KEY_EXPIRE_TIME)
        return getattr(obj, attr)

    @classmethod
    def get_count(cls, obj, attr):
        conn = RedisClient.get_connection()
        key = cls.get_count_key(obj, attr)
        count = conn.get(key)
        if count is not None:
            return int(count)
        obj.refresh_from_db()
        count = getattr(obj, attr)
        conn.set(key, count)
        return count