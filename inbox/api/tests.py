from notifications.models import Notification
from testing.testcases import TestCase

COMMENT_URL = '/api/comments/'
LIKE_URL = '/api/likes/'

class NotificationTests(TestCase):

    def setUp(self):
        self.rui, self.rui_client = self.create_user_and_client('rui')
        self.ming, self.ming_client = self.create_user_and_client('ming')
        self.ming_tweet = self.create_tweet(self.ming)

    def test_comment_create_api_trigger_notification(self):
        self.assertEqual(Notification.objects.count(), 0)
        self.rui_client.post(COMMENT_URL, {
            'tweet_id': self.ming_tweet.id,
            'content': 'nice tweet',
        })
        self.assertEqual(Notification.objects.count(), 1)

    def test_like_create_api_trigger_notification(self):
        self.assertEqual(Notification.objects.count(), 0)
        self.rui_client.post(LIKE_URL, {
            'content_type': 'tweet',
            'object_id': self.ming_tweet.id,
        })
        self.assertEqual(Notification.objects.count(), 1)