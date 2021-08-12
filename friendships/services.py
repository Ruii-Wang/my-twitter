from friendships.models import Friendship
from django.conf import settings
from django.core.cache import caches
from twitter.cache import FOLLOWINGS_PATTERN
from gatekeeper.models import GateKeeper
from friendships.hbase_models import HBaseFollowing, HBaseFollower

import time

cache = caches['testing'] if settings.TESTING else caches['default']

class FriendshipService(object):

    @classmethod
    def get_followers(cls, user):
        # 错误的写法一
        # 这种写法会导致 N+1 Queries 的问题
        # 即：filter 出所有的 friendships 耗费一次 Query
        # 而 for 循环每个 friendship 取 from_user 又耗费了 N 次 Queries
        # friendships = Friendship.objects.filter(to_user=user)
        # return [friendship.from_user for friendship in friendships]

        # 错误的写法二
        # 这种写法使用了 JOIN 操作，让friendship table和user table在from_user
        # 这个属性上join起来，join操作在大规模用户的web场景下是禁用的，因为非常慢
        # friendships = Friendship.objects.filter(to_user=user).select_related('from_user')
        # return [friendship.from_user for friendship in friendships]

        # 正确的写法一，自己手动 filter id，使用IN Query查询
        # friendships = Friendship.objects.filter(to_user=user)
        # follower_ids = [friendship.from_user_id for friendship in friendships]
        # followers = User.objects.filter(id__in=follower_ids)

        # 正确的写法二，使用prefetch_related，会自动执行成两条语句，用IN Query查询
        # 实际执行的SQL查询和上面的一样，一共两条SQL Queries
        friendships = Friendship.objects.filter(
            to_user=user,
        ).prefetch_related('from_user')
        return [friendship.from_user for friendship in friendships]

    @classmethod
    def get_follower_ids(cls, to_user_id):
        friendships = Friendship.objects.filter(to_user_id = to_user_id)
        return [friendship.from_user_id for friendship in friendships]

    @classmethod
    def get_following_user_id_set(cls, from_user_id):
        if not GateKeeper.is_switch_on('switch_friendship_to_hbase'):
            friendships = Friendship.objects.filter(from_user_id = from_user_id)
        else:
            friendships = HBaseFollowing.filter(prefix = (from_user_id,))
        user_id_set = set([fs.to_user_id for fs in friendships])
        return user_id_set

    @classmethod
    def invalidate_following_cache(cls, from_user_id):
        key = FOLLOWINGS_PATTERN.format(user_id = from_user_id)
        cache.delete(key)

    @classmethod
    def follow(cls, from_user_id, to_user_id):
        if from_user_id == to_user_id:
            return None
        if not GateKeeper.is_switch_on('switch_friendship_to_hbase'):
            # create data in mysql
            return Friendship.objects.create(
                from_user_id = from_user_id,
                to_user_id = to_user_id,
            )

        # create data in hbase
        now = int(time.time() * 1000000)
        HBaseFollower.create(
            from_user_id = from_user_id,
            to_user_id = to_user_id,
            created_at = now,
        )
        return HBaseFollowing.create(
            from_user_id = from_user_id,
            to_user_id = to_user_id,
            created_at = now,
        )

    @classmethod
    def unfollow(cls, from_user_id, to_user_id):
        if from_user_id == to_user_id:
            return 0
        # Queryset 的 delete 操作返回两个值，一个是删了多少数据，一个是具体每种类型删了多少
        # 为什么会出现多种类型数据的删掉？因为可能因为 foreign key 设置了 cascade 出现级联
        # 删除，也就是比如 A model 的某个属性是 B model 的 foreign key，并且设置了
        # on_delete = models.CASCADE，那么当 B 的某个数据被删除的时候，A 中的关联也会被删除。
        # 所以 CASCADE 是很危险的，一般最好不要用，而是用 on_delete = models.SET_NULL
        # 取而代之，这样至少可以避免误删除操作带来的多米诺效应
        if not GateKeeper.is_switch_on('switch_friendship_to_hbase'):
            deleted, _ = Friendship.objects.filter(
                from_user_id = from_user_id,
                to_user_id = to_user_id,
            ).delete()
            return deleted

        instance = cls.get_follow_instance(from_user_id, to_user_id)
        if instance is None:
            return 0

        HBaseFollowing.delete(from_user_id = from_user_id, created_at = instance.created_at)
        HBaseFollower.delete(to_user_id = to_user_id, created_at = instance.created_at)
        return 1


    @classmethod
    def has_followed(cls, from_user_id, to_user_id):
        if from_user_id == to_user_id:
            return True
        if not GateKeeper.is_switch_on('switch_friendship_to_hbase'):
            return Friendship.objects.filter(
                from_user_id = from_user_id,
                to_user_id = to_user_id,
            ).exists()
        instance = cls.get_follow_instance(from_user_id, to_user_id)
        return instance is not None

    @classmethod
    def get_follow_instance(cls, from_user_id, to_user_id):
        followings = HBaseFollowing.filter(prefix = (from_user_id,))
        for follow in followings:
            if follow.to_user_id == to_user_id:
                return follow
        return None

    @classmethod
    def get_following_count(cls, from_user_id):
        if not GateKeeper.is_switch_on('switch_friendship_to_hbase'):
            return Friendship.objects.filter(from_user_id = from_user_id).count()
        followings = HBaseFollowing.filter(prefix = (from_user_id,))
        return len(followings)