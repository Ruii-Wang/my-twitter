from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save, pre_delete
from friendships.listeners import invalidate_following_cache

# Create your models here.
class Friendship(models.Model):
    from_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='following_friendship_set',
    )
    to_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='follower_friendship_set',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        index_together = (
            # 获得我关注的所有人，按照时间排序
            ('from_user_id', 'created_at'),
            # 获得关注我的所有人，按照时间排序
            ('to_user_id', 'created_at'),
        )
        # 为了避免重复创建相同的好友关系，在数据库层面能够严格避免重复关注的好友关系
        unique_together = (('from_user_id', 'to_user_id'),)

    def __str__(self):
        return f'{self.from_user_id} followed {self.to_user_id}'

# hook up with listeners to invalidate cache
pre_delete.connect(invalidate_following_cache, sender = Friendship)
post_save.connect(invalidate_following_cache, sender = Friendship)