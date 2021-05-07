from rest_framework.test import APIClient
from friendships.models import Friendship
from testing.testcases import TestCase

NEWSFEEDS_URL = '/api/newsfeeds/'
POST_TWEETS_URL = '/api/tweets/'
FOLLOW_URL = '/api/friendships/{}/follow/'

class NewsFeedApiTests(TestCase):

    def setUp(self):
        self.rui = self.create_user('rui', 'rui@haha.com')
        self.rui_client = APIClient()
        self.rui_client.force_authenticate(self.rui)

        self.ming = self.create_user('ming', 'ming@haha.com')
        self.ming_client = APIClient()
        self.ming_client.force_authenticate(self.ming)

    def test_list(self):
        # 匿名用户需要登录
        response = self.anonymous_client.get(NEWSFEEDS_URL)
        self.assertEqual(response.status_code, 403)

        # 不能用post
        response = self.ming_client.post(NEWSFEEDS_URL)
        self.assertEqual(response.status_code, 405)

        # 一开始没有任何newsfeeds
        response = self.ming_client.get(NEWSFEEDS_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['newsfeeds']), 0)

        # 自己发的信息可以看到
        tweet = self.ming_client.post(POST_TWEETS_URL, {'content': 'Hello World!'})
        response = self.ming_client.get(NEWSFEEDS_URL)
        self.assertEqual(len(response.data['newsfeeds']), 1)
        self.assertEqual(response.data['newsfeeds'][0]['tweet']['content'], tweet.data['content'])

        # 关注之后可以看到别人发的
        self.ming_client.post(FOLLOW_URL.format(self.rui.id))
        response = self.rui_client.post(POST_TWEETS_URL, {'content': 'Hello Twitter!'})
        posted_tweet_id = response.data['id']
        response = self.ming_client.get(NEWSFEEDS_URL)
        self.assertEqual(len(response.data['newsfeeds']), 2)
        self.assertEqual(response.data['newsfeeds'][0]['tweet']['id'], posted_tweet_id)
