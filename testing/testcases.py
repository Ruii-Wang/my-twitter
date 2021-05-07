from django.test import TestCase as DjangoTestCase
from django.contrib.auth.models import User
from tweets.models import Tweet
from rest_framework.test import APIClient

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

    def create_user(self, username, email, password=None):
        if password is None:
            password = 'genetic password'
        return User.objects.create_user(username, email, password)

    def create_tweet(self, user, content=None):
        if content is None:
            content = 'default tweet content'
        return Tweet.objects.create(user=user, content=content)
