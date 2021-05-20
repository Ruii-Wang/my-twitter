from datetime import timedelta
from django.contrib.auth.models import User
from django.test import TestCase
from tweets.models import Tweet
from utils.time_helpers import utc_now
from testing.testcases import TestCase


class TweetTests(TestCase):

    def setUp(self):
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