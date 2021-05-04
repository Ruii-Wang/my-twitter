from django.contrib.auth.models import User
from django.db import models
from utils.time_helpers import utc_now


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

    @property
    def hours_to_now(self):
        # self.created_at是带有时区的
        # vagrant的时区是以UTC时区为准的
        # utc_now()是将datetime.now()带上时区信息
        return (utc_now() - self.created_at).seconds // 3600

    def __str__(self):
        # 这里是执行print(tweet instance)的时候会显示的内容
        return f'{self.created_at} {self.user} {self.content}'