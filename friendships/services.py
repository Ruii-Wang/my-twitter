from friendships.models import Friendship

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
