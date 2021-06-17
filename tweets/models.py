from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db import models
from likes.models import Like
from utils.time_helpers import utc_now
from tweets.constants import TweetPhotoStatus, TWEET_PHOTO_STATUS_CHOICES
from accounts.services import UserService


class Tweet(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        help_text='who posts this tweet',
    )
    content = models.CharField(max_length=255)
    # auto_mow_add是当创建的时候自动计算创建的时间
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # 生成索引表单[user, created_at, id]
        index_together = (('user', 'created_at'),)
        ordering = ('user', '-created_at')

    @property
    def hours_to_now(self):
        # self.created_at是带有时区的
        # vagrant的时区是以UTC时区为准的
        # utc_now()是将datetime.now()带上时区信息
        return (utc_now() - self.created_at).seconds // 3600

    @property
    def like_set(self):
        return Like.objects.filter(
            content_type = ContentType.objects.get_for_model(Tweet),
            object_id = self.id,
        ).order_by('-created_at')

    def __str__(self):
        # 这里是执行print(tweet instance)的时候会显示的内容
        return f'{self.created_at} {self.user} {self.content}'

    @property
    def cached_user(self):
        return UserService.get_user_through_cache(self.user_id)


class TweetPhoto(models.Model):
    # 图片位于哪个tweet下面
    tweet = models.ForeignKey(Tweet, on_delete=models.SET_NULL, null=True)

    # 谁上传了这个图片，这个信息虽然可以在tweet中获得，但是重复的记录在image里可以
    # 在使用上带来便利，比如某个人经常上传一些不合法的照片，那么这个人新上传的照片可以
    # 被标记为重点审查对象。或者我们需要封禁某个用户上传的所有照片的时候，就可以通过这
    # 个model快速进行筛选。
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    # 图片文件
    file = models.FileField()
    order = models.IntegerField(default=0)

    # 图片状态，用于审核
    status = models.IntegerField(
        default=TweetPhotoStatus.PENDING,
        choices=TWEET_PHOTO_STATUS_CHOICES,
    )

    # 软删除标记，当一张照片被删除的时候，会先被标记为已经被删除，在一定时间后
    # 才会被真正的删除。这样做的目的是，如果在tweet被删除的时候马上执行真删除
    # 的通常会花费一定的时间，影响效率。可以使用异步任务在后台慢慢做真删除
    has_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        index_together = (
            ('user', 'created_at'),
            ('has_deleted', 'created_at'),
            ('status', 'created_at'),
            ('tweet', 'order'),
        )

    def __str__(self):
        return f'{self.tweet_id}: {self.file}'