from utils.redis_client import RedisClient
from utils.redis_serializers import DjangoModelSerializer
from twitter import settings

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
        conn = RedisClient.get_connection()
        if not conn.exists(key):
            # 如果key不存在，直接从数据库里面load
            # 就不走单个push的方式加到cache里面了
            cls._load_objects_to_cache(key, queryset)
            return
        serialized_data = DjangoModelSerializer.serialize(obj)
        conn.lpush(key, serialized_data)