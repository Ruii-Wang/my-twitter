from notifications.models import Notification
from testing.testcases import TestCase

COMMENT_URL = '/api/comments/'
LIKE_URL = '/api/likes/'
NOTIFICATION_URL = '/api/notifications/'

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


class NotificationApiTests(TestCase):

    def setUp(self):
        self.rui, self.rui_client = self.create_user_and_client('rui')
        self.ming, self.ming_client = self.create_user_and_client('ming')
        self.rui_tweet = self.create_tweet(self.rui)

    def test_unread_count(self):
        self.ming_client.post(LIKE_URL, {
            'content_type': 'tweet',
            'object_id': self.rui_tweet.id,
        })
        url = '/api/notifications/unread-count/'
        response = self.rui_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['unread_count'], 1)

        comment = self.create_comment(self.rui, self.rui_tweet)
        self.ming_client.post(LIKE_URL, {
            'content_type': 'comment',
            'object_id': comment.id,
        })
        response = self.rui_client.get(url)
        self.assertEqual(response.data['unread_count'], 2)

    def test_mark_all_as_read(self):
        self.ming_client.post(LIKE_URL, {
            'content_type': 'tweet',
            'object_id': self.rui_tweet.id,
        })
        comment = self.create_comment(self.rui, self.rui_tweet)
        self.ming_client.post(LIKE_URL, {
            'content_type': 'comment',
            'object_id': comment.id,
        })

        unread_url = '/api/notifications/unread-count/'
        response = self.rui_client.get(unread_url)
        self.assertEqual(response.data['unread_count'], 2)

        mark_url = '/api/notifications/mark-all-as-read/'
        response = self.rui_client.get(mark_url)
        self.assertEqual(response.status_code, 405)
        response = self.rui_client.post(mark_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['marked_count'], 2)
        response = self.rui_client.get(unread_url)
        self.assertEqual(response.data['unread_count'], 0)

    def test_list(self):
        self.ming_client.post(LIKE_URL, {
            'content_type': 'tweet',
            'object_id': self.rui_tweet.id,
        })
        comment = self.create_comment(self.rui, self.rui_tweet)
        self.ming_client.post(LIKE_URL, {
            'content_type': 'comment',
            'object_id': comment.id,
        })

        # 匿名用户无法查看
        response = self.anonymous_client.get(NOTIFICATION_URL)
        self.assertEqual(response.status_code, 403)

        # ming看不到任何通知
        response = self.ming_client.get(NOTIFICATION_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)

        # rui看到两个通知
        response = self.rui_client.get(NOTIFICATION_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)

        # 标记之后看到一个未读
        notification = self.rui.notifications.first()
        notification.unread = False
        notification.save()
        response = self.rui_client.get(NOTIFICATION_URL)
        self.assertEqual(response.data['count'], 2)
        response = self.rui_client.get(NOTIFICATION_URL, {'unread': True})
        self.assertEqual(response.data['count'], 1)
        response = self.rui_client.get(NOTIFICATION_URL, {'unread': False})
        self.assertEqual(response.data['count'], 1)