from django.contrib.auth.models import User
from django.db import models
from tweets.models import Tweet


class Comment(models.Model):
    """
    当前版本中，实现了一个简单的评论，
    评论只能评论在某个tweet上，不能评论别人的评论
    """
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    tweet = models.ForeignKey(Tweet, null=True, on_delete=models.SET_NULL)
    content = models.TextField(max_length=140)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # 有在某个tweet下排序所有comments的需求
        index_together = (('tweet', 'created_at'),)

    def __str__(self):
        return '{} - {} says {} at tweet {}'.format(
            self.created_at,
            self.user,
            self.content,
            self.tweet_id,
        )