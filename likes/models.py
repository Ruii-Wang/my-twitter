from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from utils.memcached_helper import MemcachedHelper
from django.db.models.signals import pre_delete, post_save
from likes.listeners import incr_likes_count, decr_likes_count

class Like(models.Model):
    # user liked content_object at created_at
    content_object = GenericForeignKey('content_type', 'object_id')
    object_id = models.PositiveIntegerField() # comment id or tweet id
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
    )
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # 这里的unique_together会建一个<user, content_type, object_id>的索引
        # 这个索引同时具备查询某个user like 了哪些不同的 objects 的功能
        # 因此如果unique_together改成<content_type, object_id, user>则没有这样的效果
        unique_together = (('user', 'content_type', 'object_id'),)
        index_together = (
            # 可以按时间排序某个被like的content_object的所有likes
            ('content_type', 'object_id', 'created_at'),

            # 可以按照时间排序某个user的like记录
            ('user', 'content_type', 'created_at'),
        )

    def __str__(self):
        return '{} - {} liked {} {}'.format(
            self.created_at,
            self.user,
            self.content_type,
            self.object_id,
        )

    @property
    def cached_user(self):
        return MemcachedHelper.get_object_through_cache(User, self.user_id)

pre_delete.connect(decr_likes_count, sender=Like)
post_save.connect(incr_likes_count, sender=Like)