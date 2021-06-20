from rest_framework.test import APIClient
from friendships.models import Friendship
from testing.testcases import TestCase
from utils.paginations import EndlessPagination

NEWSFEEDS_URL = '/api/newsfeeds/'
POST_TWEETS_URL = '/api/tweets/'
FOLLOW_URL = '/api/friendships/{}/follow/'

class NewsFeedApiTests(TestCase):

    def setUp(self):
        self.clear_cache()
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
        self.assertEqual(len(response.data['results']), 0)

        # 自己发的信息可以看到
        tweet = self.ming_client.post(POST_TWEETS_URL, {'content': 'Hello World!'})
        response = self.ming_client.get(NEWSFEEDS_URL)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['tweet']['content'], tweet.data['content'])

        # 关注之后可以看到别人发的
        self.ming_client.post(FOLLOW_URL.format(self.rui.id))
        response = self.rui_client.post(POST_TWEETS_URL, {'content': 'Hello Twitter!'})
        posted_tweet_id = response.data['id']
        response = self.ming_client.get(NEWSFEEDS_URL)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['results'][0]['tweet']['id'], posted_tweet_id)

    def test_pagination(self):
        page_size = EndlessPagination.page_size
        followed_user = self.create_user('followed')
        newsfeeds = []
        for i in range(page_size * 2):
            tweet = self.create_tweet(followed_user)
            newsfeed = self.create_newsfeed(user = self.rui, tweet = tweet)
            newsfeeds.append(newsfeed)
        newsfeeds = newsfeeds[::-1]

        # pull the first page
        response = self.rui_client.get(NEWSFEEDS_URL)
        self.assertEqual(response.data['has_next_page'], True)
        self.assertEqual(len(response.data['results']), page_size)
        self.assertEqual(response.data['results'][0]['id'], newsfeeds[0].id)
        self.assertEqual(response.data['results'][1]['id'], newsfeeds[1].id)
        self.assertEqual(
            response.data['results'][page_size - 1]['id'],
            newsfeeds[page_size - 1].id,
        )

        # pull the second page
        response = self.rui_client.get(
            NEWSFEEDS_URL,
            {'created_at__lt': newsfeeds[page_size - 1].created_at},
        )
        self.assertEqual(response.data['has_next_page'], False)
        results = response.data['results']
        self.assertEqual(len(results), page_size)
        self.assertEqual(results[0]['id'], newsfeeds[page_size].id)
        self.assertEqual(results[1]['id'], newsfeeds[page_size + 1].id)
        self.assertEqual(
            results[page_size - 1]['id'],
            newsfeeds[2 * page_size - 1].id,
        )

        # pull latest newsfeeds
        response = self.rui_client.get(
            NEWSFEEDS_URL,
            {'created_at__gt': newsfeeds[0].created_at},
        )
        self.assertEqual(response.data['has_next_page'], False)
        self.assertEqual(len(response.data['results']), 0)

        tweet = self.create_tweet(followed_user)
        new_newsfeed = self.create_newsfeed(user=self.rui, tweet=tweet)

        response = self.rui_client.get(
            NEWSFEEDS_URL,
            {'created_at__gt': newsfeeds[0].created_at},
        )
        self.assertEqual(response.data['has_next_page'], False)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], new_newsfeed.id)

    def test_user_cache(self):
        profile = self.ming.profile
        profile.nickname = 'jelly'
        profile.save()

        self.assertEqual(self.rui.username, 'rui')
        self.create_newsfeed(self.ming, self.create_tweet(self.rui))
        self.create_newsfeed(self.ming, self.create_tweet(self.ming))

        response = self.ming_client.get(NEWSFEEDS_URL)
        results = response.data['results']
        self.assertEqual(results[0]['tweet']['user']['username'], 'ming')
        self.assertEqual(results[0]['tweet']['user']['nickname'], 'jelly')
        self.assertEqual(results[1]['tweet']['user']['username'], 'rui')

        self.rui.username = 'michael'
        self.rui.save()
        profile.nickname = 'jelly_away'
        profile.save()

        response = self.ming_client.get(NEWSFEEDS_URL)
        results = response.data['results']
        self.assertEqual(results[0]['tweet']['user']['username'], 'ming')
        self.assertEqual(results[0]['tweet']['user']['nickname'], 'jelly_away')
        self.assertEqual(results[1]['tweet']['user']['username'], 'michael')

    def test_tweet_cache(self):
        tweet = self.create_tweet(self.rui, 'content1')
        self.create_newsfeed(self.ming, tweet)
        response = self.ming_client.get(NEWSFEEDS_URL)
        results = response.data['results']
        self.assertEqual(results[0]['tweet']['user']['username'], 'rui')
        self.assertEqual(results[0]['tweet']['content'], 'content1')

        # update username
        self.rui.username = 'michael'
        self.rui.save()
        response = self.ming_client.get(NEWSFEEDS_URL)
        results = response.data['results']
        self.assertEqual(results[0]['tweet']['user']['username'], 'michael')

        # update content
        tweet.content = 'content2'
        tweet.save()
        response = self.ming_client.get(NEWSFEEDS_URL)
        results = response.data['results']
        self.assertEqual(results[0]['tweet']['content'], 'content2')