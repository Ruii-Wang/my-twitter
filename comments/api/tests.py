from testing.testcases import TestCase
from rest_framework.test import APIClient

COMMENT_URL = '/api/comments/'

class CommentApiTests(TestCase):

    def setUp(self):
        self.rui = self.create_user('rui')
        self.rui_client = APIClient()
        self.rui_client.force_authenticate(self.rui)

        self.tweet = self.create_tweet(self.rui)

    def test_create(self):
        # 匿名不可以创建
        response = self.anonymous_client.post(COMMENT_URL)
        self.assertEqual(response.status_code, 403)

        # 没有参数不行
        response = self.rui_client.post(COMMENT_URL)
        self.assertEqual(response.status_code, 400)

        # 只带tweet_id不行
        response = self.rui_client.post(COMMENT_URL, {'tweet_id': self.tweet.id})
        self.assertEqual(response.status_code, 400)

        # 只带content不行
        response = self.rui_client.post(COMMENT_URL, {'content': '1'})
        self.assertEqual(response.status_code, 400)

        # content太长不行
        response = self.rui_client.post(COMMENT_URL, {
            'tweet_id': self.tweet.id,
            'content': '1' * 141,
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual('content' in response.data['errors'], True)

        # tweet_id和content都带才行
        response = self.rui_client.post(COMMENT_URL, {
            'tweet_id': self.tweet.id,
            'content': '1',
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['user']['id'], self.rui.id)
        self.assertEqual(response.data['tweet_id'], self.tweet.id)
        self.assertEqual(response.data['content'], '1')