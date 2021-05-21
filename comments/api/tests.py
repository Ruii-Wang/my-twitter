from testing.testcases import TestCase
from rest_framework.test import APIClient
from comments.models import Comment
from django.utils import timezone

COMMENT_URL = '/api/comments/'
COMMENT_DETAIL_URL = '/api/comments/{}/'
TWEET_LIST_API = '/api/tweets/'
TWEET_DETAIL_API = '/api/tweets/{}/'
NEWSFEED_LIST_API = '/api/newsfeeds/'

class CommentApiTests(TestCase):

    def setUp(self):
        self.rui = self.create_user('rui')
        self.rui_client = APIClient()
        self.rui_client.force_authenticate(self.rui)

        self.ming = self.create_user('ming')
        self.ming_client = APIClient()
        self.ming_client.force_authenticate(self.ming)

        self.tweet = self.create_tweet(self.rui)

    def test_list(self):
        # 必须带 tweet_id
        response = self.anonymous_client.get(COMMENT_URL)
        self.assertEqual(response.status_code, 400)

        # 带了tweet_id可以访问
        # 一开始没有评论
        response = self.anonymous_client.get(COMMENT_URL, {
            'tweet_id': self.tweet.id,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['comments']), 0)

        # 评论按照时间顺序打开
        self.create_comment(self.rui, self.tweet, '1')
        self.create_comment(self.ming, self.tweet, '2')
        self.create_comment(self.ming, self.create_tweet(self.ming), '3')
        response = self.anonymous_client.get(COMMENT_URL, {
            'tweet_id': self.tweet.id,
        })
        self.assertEqual(len(response.data['comments']), 2)
        self.assertEqual(response.data['comments'][0]['content'], '1')
        self.assertEqual(response.data['comments'][1]['content'], '2')

        # 同时提供user_id和tweet_id只有tweet_id会在filter中生效
        response = self.anonymous_client.get(COMMENT_URL, {
            'tweet_id': self.tweet.id,
            'user_id': self.rui.id,
        })
        self.assertEqual(len(response.data['comments']), 2)

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

    def test_update(self):
        comment = self.create_comment(self.rui, self.tweet, 'original')
        another_tweet = self.create_tweet(self.ming)
        url = '{}{}/'.format(COMMENT_URL, comment.id)

        # 使用put的情况下
        # 匿名不可以更新
        response = self.anonymous_client.put(url, {'content': 'new'})
        self.assertEqual(response.status_code, 403)

        # 非本人不能更新
        response = self.ming_client.put(url, {'content': 'new'})
        self.assertEqual(response.status_code, 403)
        comment.refresh_from_db()
        self.assertNotEqual(comment.content, 'new')

        # 不能更新除content意外的内容，静默处理，只更新内容
        before_updated_at = comment.updated_at
        before_created_at = comment.created_at
        now = timezone.now()
        response = self.rui_client.put(url, {
            'content': 'new',
            'user_id': self.ming.id,
            'tweet_id': another_tweet.id,
            'created_at': now,
        })
        self.assertEqual(response.status_code, 200)
        comment.refresh_from_db()
        self.assertEqual(comment.content, 'new')
        self.assertEqual(comment.user, self.rui)
        self.assertEqual(comment.tweet, self.tweet)
        self.assertEqual(comment.created_at, before_created_at)
        self.assertNotEqual(comment.created_at, now)
        self.assertNotEqual(comment.updated_at, before_updated_at)

    def test_destroy(self):
        comment = self.create_comment(self.rui, self.tweet)
        url = '{}{}/'.format(COMMENT_URL, comment.id)

        # 匿名不可以删除
        response = self.anonymous_client.delete(url)
        self.assertEqual(response.status_code, 403)

        # 非本人不能删除
        response = self.ming_client.delete(url)
        self.assertEqual(response.status_code, 403)

        # 本人可以删除
        count = Comment.objects.count()
        response = self.rui_client.delete(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Comment.objects.count(), count-1)

    def test_comments_count(self):
        # test tweet detail api
        tweet = self.create_tweet(self.rui)
        url = TWEET_DETAIL_API.format(tweet.id)
        response = self.ming_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['comments_count'], 0)

        # test tweet list api
        self.create_comment(self.rui, tweet)
        response = self.ming_client.get(TWEET_LIST_API, {'user_id': self.rui.id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['tweets'][0]['comments_count'], 1)

        # test newsfeeds list api
        self.create_comment(self.ming, tweet)
        self.create_newsfeed(self.ming, tweet)
        response = self.ming_client.get(NEWSFEED_LIST_API)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['newsfeeds'][0]['tweet']['comments_count'], 2)