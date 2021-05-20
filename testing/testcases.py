from django.test import TestCase as DjangoTestCase
from django.contrib.auth.models import User
from tweets.models import Tweet
from rest_framework.test import APIClient
from comments.models import Comment
from likes.models import Like
from django.contrib.contenttypes.models import ContentType

class TestCase(DjangoTestCase):

    @property
    def anonymous_client(self):
        # 不能直接写成
        # return APIClient()
        # 因为每次调用这个函数的时候就会创新新的instance
        # 只需要第一访问的时候创建new instance就好了

        # instance内部的cache
        if hasattr(self, '_anonymous_client'):
            return self._anonymous_client
        self._anonymous_client = APIClient()
        return self._anonymous_client

    def create_user(self, username, email=None, password=None):
        if password is None:
            password = 'genetic password'
        if email is None:
            email = f'{username}@haha.com'
        # 不能写成User.objects.create()
        # 因为password需要被加密，username和email需要进行一些normalize处理
        return User.objects.create_user(username, email, password)

    def create_tweet(self, user, content=None):
        if content is None:
            content = 'default tweet content'
        return Tweet.objects.create(user=user, content=content)

    def create_comment(self, user, tweet, content=None):
        if content is None:
            content = 'default comment content'
        return Comment.objects.create(user=user, tweet=tweet, content=content)

    def create_like(self, user, target):
        # target is tweet or comment
        instance, _ = Like.objects.get_or_create(
            content_type = ContentType.objects.get_for_model(target.__class__),
            object_id = target.id,
            user = user,
        )
        return instance

    def create_user_and_client(self, *args, **kwargs):
        user = self.create_user(*args, **kwargs)
        client = APIClient()
        client.force_authenticate(user)
        return user, client

