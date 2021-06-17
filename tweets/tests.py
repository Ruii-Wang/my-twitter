from datetime import timedelta
from utils.time_helpers import utc_now
from testing.testcases import TestCase
from tweets.models import TweetPhoto
from tweets.constants import TweetPhotoStatus


class TweetTests(TestCase):

    def setUp(self):
        self.clear_cache()
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