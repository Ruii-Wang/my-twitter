from newsfeeds.services import NewsFeedService
from testing.testcases import TestCase
from twitter.cache import USER_NEWSFEEDS_PATTERN
from utils.redis_client import RedisClient


class NewsFeedServiceTests(TestCase):

    def setUp(self):
        self.clear_cache()
        self.rui = self.create_user('rui')
        self.ming = self.create_user('ming')

    def test_get_user_newsfeeds(self):
        newsfeeds_ids = []
        for i in range(3):
            tweet = self.create_tweet(self.ming)
            newsfeed = self.create_newsfeed(self.rui, tweet)
            newsfeeds_ids.append(newsfeed.id)
        newsfeed_ids = newsfeeds_ids[::-1]

        # cache miss
        newsfeeds = NewsFeedService.get_cached_newsfeeds(self.rui.id)
        self.assertEqual([f.id for f in newsfeeds], newsfeed_ids)

        # cache hit
        newsfeeds = NewsFeedService.get_cached_newsfeeds(self.rui.id)
        self.assertEqual([f.id for f in newsfeeds], newsfeed_ids)

        # cache updated
        tweet = self.create_tweet(self.rui)
        new_newsfeed = self.create_newsfeed(self.rui, tweet)
        newsfeeds = NewsFeedService.get_cached_newsfeeds(self.rui.id)
        newsfeed_ids.insert(0, new_newsfeed.id)
        self.assertEqual([f.id for f in newsfeeds], newsfeed_ids)

    def test_create_new_newsfeed_before_get_cached_newsfeeds(self):
        feed1 = self.create_newsfeed(self.rui, self.create_tweet(self.rui))

        RedisClient.clear()
        conn = RedisClient.get_connection()

        key = USER_NEWSFEEDS_PATTERN.format(user_id=self.rui.id)
        self.assertEqual(conn.exists(key), False)
        feed2 = self.create_newsfeed(self.rui, self.create_tweet(self.rui))
        self.assertEqual(conn.exists(key), True)

        feeds = NewsFeedService.get_cached_newsfeeds(self.rui.id)
        self.assertEqual([f.id for f in feeds], [feed2.id, feed1.id])