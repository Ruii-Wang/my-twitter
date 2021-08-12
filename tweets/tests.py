from datetime import timedelta
from utils.time_helpers import utc_now
from testing.testcases import TestCase
from tweets.models import TweetPhoto
from tweets.constants import TweetPhotoStatus
from utils.redis_client import RedisClient
from utils.redis_serializers import DjangoModelSerializer
from tweets.services import TweetService
from twitter.cache import USER_TWEETS_PATTERN


class TweetTests(TestCase):

    def setUp(self):
        super(TweetTests, self).setUp()
        self.rui = self.create_user('rui')
        self.tweet = self.create_tweet(self.rui, content= "Don't give up")

    def test_hours_to_now(self):
        self.tweet.created_at = utc_now() - timedelta(hours=10)
        self.tweet.save()
        self.assertEqual(self.tweet.hours_to_now, 10)

    def test_like_set(self):
        self.create_like(self.rui, self.tweet)
        self.assertEqual(self.tweet.like_set.count(), 1)

        self.create_like(self.rui, self.tweet)
        self.assertEqual(self.tweet.like_set.count(), 1)

        ming = self.create_user('ming')
        self.create_like(ming, self.tweet)
        self.assertEqual(self.tweet.like_set.count(), 2)

    def test_create_photo(self):
        photo = TweetPhoto.objects.create(
            tweet = self.tweet,
            user = self.rui,
        )
        self.assertEqual(photo.user, self.rui)
        self.assertEqual(photo.status, TweetPhotoStatus.PENDING)
        self.assertEqual(self.tweet.tweetphoto_set.count(), 1)

    def test_cache_tweet_in_redis(self):
        tweet = self.create_tweet(self.rui)
        conn = RedisClient.get_connection()
        serialized_data = DjangoModelSerializer.serialize(tweet)
        conn.set(f'tweet:{tweet.id}', serialized_data)
        data = conn.get(f'tweet:not_exists')
        self.assertEqual(data, None)

        data = conn.get(f'tweet:{tweet.id}')
        cached_tweet = DjangoModelSerializer.deserialize(data)
        self.assertEqual(tweet, cached_tweet)


class TweetServiceTests(TestCase):

    def setUp(self):
        super(TweetServiceTests, self).setUp()
        self.rui = self.create_user('rui')

    def test_get_user_tweets(self):
        tweet_ids = []
        for i in range(3):
            tweet = self.create_tweet(self.rui, 'tweet {}'.format(i))
            tweet_ids.append(tweet.id)
        tweet_ids = tweet_ids[::-1]

        RedisClient.clear()
        conn = RedisClient.get_connection()

        # cache miss
        tweets = TweetService.get_cached_tweets(self.rui.id)
        self.assertEqual([t.id for t in tweets], tweet_ids)

        # cache hit
        tweets = TweetService.get_cached_tweets(self.rui.id)
        self.assertEqual([t.id for t in tweets], tweet_ids)

        # cache updated
        new_tweet = self.create_tweet(self.rui, 'new tweet')
        tweets = TweetService.get_cached_tweets(self.rui.id)
        tweet_ids.insert(0, new_tweet.id)
        self.assertEqual([t.id for t in tweets], tweet_ids)

    def test_create_new_tweet_before_get_cached_tweets(self):
        tweet1 = self.create_tweet(self.rui, 'tweet1')

        RedisClient.clear()
        conn = RedisClient.get_connection()

        key = USER_TWEETS_PATTERN.format(user_id=self.rui.id)
        self.assertEqual(conn.exists(key), False)
        tweet2 = self.create_tweet(self.rui, 'tweet2')
        self.assertEqual(conn.exists(key), True)

        tweets = TweetService.get_cached_tweets(self.rui.id)
        self.assertEqual([t.id for t in tweets], [tweet2.id, tweet1.id])